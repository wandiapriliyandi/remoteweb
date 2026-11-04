"""Engine WebSocket Client & integrasi pemantau browser dengan Auto-Updater."""
import asyncio
import json
import os
import socket
import threading
import time
from typing import Callable, Optional
import websockets

from shared.protocol import (
    APP_VERSION,
    TYPE_REGISTER,
    TYPE_URL_ACTIVITY,
    TYPE_UPDATE_RULES,
    TYPE_FORCE_CLOSE,
    TYPE_PING,
    TYPE_PONG,
    TYPE_UPDATE_AVAILABLE,
    TYPE_UPDATE_PROGRESS,
    create_message,
    parse_message,
    is_newer_version
)
from client.browser_watcher import (
    BrowserWatcher,
    close_active_tab,
    close_entire_window,
    find_top_browser_window
)
from client.config import load_client_config, save_client_config
from client.updater import perform_auto_update

class ClientEngine:
    def __init__(self):
        self.config = load_client_config()
        self.client_id = self.config.get("client_id")
        self.server_ip = self.config.get("server_ip", "127.0.0.1")
        self.server_port = self.config.get("server_port", 8765)
        self.hostname = socket.gethostname()

        self.watcher = BrowserWatcher(check_interval=0.4)
        self.watcher.update_rules(self.config.get("cached_rules", []))

        self.is_connected = False
        self.is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws = None
        self._has_logged_connect = False
        self._is_updating = False

        # Callbacks untuk GUI
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_connection_status: Optional[Callable[[bool], None]] = None
        self.on_activity_detected: Optional[Callable[[str, str, bool], None]] = None

    def log(self, message: str):
        if self.on_log:
            self.on_log(message)
        else:
            print(f"[CLIENT] {message}")

    def update_server_target(self, ip: str, port: int = 8765):
        """Memperbarui alamat IP dan Port target server."""
        self.server_ip = ip.strip()
        self.server_port = int(port)
        self.config["server_ip"] = self.server_ip
        self.config["server_port"] = self.server_port
        save_client_config(self.config)
        self._has_logged_connect = False
        self.log(f"Alamat server diatur ke ws://{self.server_ip}:{self.server_port}")

    def start(self):
        if self.is_running:
            return
        self.is_running = True

        watcher_thread = threading.Thread(target=self._run_browser_watcher, daemon=True)
        watcher_thread.start()

        net_thread = threading.Thread(target=self._run_network_loop, daemon=True)
        net_thread.start()

    def _run_browser_watcher(self):
        """Loop pemantau jendela browser di PC client."""
        last_reported_title = ""
        while self.is_running:
            try:
                res = self.watcher.inspect_once()
                if res:
                    browser_name, title, detected_info, is_blocked, matched_rule = res

                    # Hanya log ke tampilan lokal jika terjadi PEMBLOKIRAN
                    if is_blocked:
                        self.log(f"🚨 Situs terlarang ('{matched_rule}') terdeteksi pada {browser_name} -> TAB DITUTUP!")

                    if self.on_activity_detected:
                        self.on_activity_detected(browser_name, title, is_blocked)

                    # Kirim laporan ke server hanya jika judul berubah atau terblokir
                    if title != last_reported_title or is_blocked:
                        last_reported_title = title
                        if self.is_connected and self._ws and self._loop:
                            payload = {
                                "browser": browser_name,
                                "title": title,
                                "url_snippet": detected_info,
                                "is_blocked": is_blocked,
                                "matched_rule": matched_rule,
                                "timestamp": time.strftime("%H:%M:%S")
                            }
                            msg = create_message(TYPE_URL_ACTIVITY, payload)
                            asyncio.run_coroutine_threadsafe(self._ws.send(msg), self._loop)
            except Exception:
                pass
            time.sleep(self.watcher.check_interval)

    def _run_network_loop(self):
        """Event loop asyncio untuk koneksi WebSocket ke server."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_loop())

    async def _connect_loop(self):
        was_connected = False
        while self.is_running:
            uri = f"ws://{self.server_ip}:{self.server_port}"
            try:
                async with websockets.connect(uri, ping_interval=20, ping_timeout=15) as ws:
                    self._ws = ws
                    self.is_connected = True
                    was_connected = True

                    # Hanya log sekali saat status berubah menjadi terhubung
                    if not self._has_logged_connect:
                        self.log("✅ Berhasil terhubung ke PC Server Admin.")
                        self._has_logged_connect = True

                    if self.on_connection_status:
                        self.on_connection_status(True)

                    # Registrasi ke server dengan menyertakan versi
                    reg_msg = create_message(TYPE_REGISTER, {
                        "client_id": self.client_id,
                        "hostname": self.hostname,
                        "rules_count": len(self.watcher.blocked_keywords),
                        "version": APP_VERSION
                    })
                    await ws.send(reg_msg)

                    # Dengarkan pesan dari server
                    async for raw_msg in ws:
                        msg = parse_message(raw_msg)
                        mtype = msg.get("type")
                        payload = msg.get("payload", {})

                        if mtype == TYPE_UPDATE_RULES:
                            new_rules = payload.get("rules", [])
                            self.watcher.update_rules(new_rules)
                            self.config["cached_rules"] = new_rules
                            save_client_config(self.config)
                            self.log(f"📥 Aturan diperbarui oleh Admin ({len(new_rules)} situs/kata kunci).")

                        elif mtype == TYPE_FORCE_CLOSE:
                            mode = payload.get("mode", "tab")
                            hwnd, btitle, bname = find_top_browser_window()
                            if hwnd:
                                if mode == "window":
                                    close_entire_window(hwnd)
                                    self.log(f"🛑 Menutup jendela browser {bname} atas perintah Admin.")
                                else:
                                    close_active_tab(hwnd)
                                    self.log(f"🛑 Menutup tab browser {bname} atas perintah Admin.")

                        elif mtype == TYPE_UPDATE_AVAILABLE:
                            target_ver = payload.get("version", "")
                            download_url = payload.get("download_url", "")
                            changelog = payload.get("changelog", "")
                            self.log(f"🔔 Server menawarkan update versi v{target_ver}: {changelog}")

                            if not self._is_updating and is_newer_version(target_ver, APP_VERSION):
                                self._is_updating = True
                                self.log(f"🚀 Memulai unduhan otomatis v{target_ver} dari Server...")
                                threading.Thread(
                                    target=self._execute_auto_update,
                                    args=(download_url, target_ver),
                                    daemon=True
                                ).start()
                            else:
                                self.log(f"Aplikasi sudah pada versi terbaru (v{APP_VERSION}).")

                        elif mtype == TYPE_PING:
                            await ws.send(create_message(TYPE_PONG))

            except (websockets.exceptions.ConnectionClosed, OSError, Exception):
                self.is_connected = False
                self._ws = None

                # Catat putus koneksi HANYA jika sebelumnya pernah terhubung
                if was_connected:
                    self.log("⚠️ Koneksi ke server terputus. Mencoba menghubungkan kembali...")
                    was_connected = False
                    self._has_logged_connect = False

                if self.on_connection_status:
                    self.on_connection_status(False)

            # Jeda sebelum mencoba reconnect
            time.sleep(3)

    def _execute_auto_update(self, download_url: str, target_ver: str):
        """Menjalankan proses auto-update di thread terpisah dan melaporkan progres ke Server."""
        def _on_status(status: str, percent: int):
            if status == "downloading":
                self.log(f"📥 Mengunduh update: {percent}%")
            elif status == "installing":
                self.log("⚙️ Mengganti file program dan merestart client...")
            elif status == "failed":
                self.log("❌ Gagal memperbarui aplikasi dari server.")
                self._is_updating = False

            # Laporkan ke Server Admin via WebSocket jika koneksi aktif
            if self.is_connected and self._ws and self._loop:
                msg = create_message(TYPE_UPDATE_PROGRESS, {
                    "client_id": self.client_id,
                    "status": status,
                    "percent": percent,
                    "version": target_ver
                })
                asyncio.run_coroutine_threadsafe(self._ws.send(msg), self._loop)

        perform_auto_update(download_url, _on_status)

    def stop(self):
        self.is_running = False
