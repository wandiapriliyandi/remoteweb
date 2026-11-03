"""Engine WebSocket Client & integrasi pemantau browser."""
import asyncio
import json
import os
import socket
import threading
import time
from typing import Callable, Optional
import websockets

from shared.protocol import (
    TYPE_REGISTER,
    TYPE_URL_ACTIVITY,
    TYPE_UPDATE_RULES,
    TYPE_FORCE_CLOSE,
    TYPE_PING,
    TYPE_PONG,
    create_message,
    parse_message
)
from client.browser_watcher import (
    BrowserWatcher,
    close_active_tab,
    close_entire_window,
    find_top_browser_window
)
from client.config import load_client_config, save_client_config

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
        self.log(f"Alamat server diperbarui ke ws://{self.server_ip}:{self.server_port}")

    def start(self):
        """Menjalankan engine client dan watcher."""
        if self.is_running:
            return
        self.is_running = True

        watcher_thread = threading.Thread(target=self._run_browser_watcher, daemon=True)
        watcher_thread.start()

        net_thread = threading.Thread(target=self._run_network_loop, daemon=True)
        net_thread.start()

    def _run_browser_watcher(self):
        """Loop pemantau jendela browser di PC client."""
        last_title = ""
        while self.is_running:
            try:
                res = self.watcher.inspect_once()
                if res:
                    browser_name, title, detected_info, is_blocked, matched_rule = res
                    if title != last_title or is_blocked:
                        last_title = title
                        status_str = f"BLOKIR [{matched_rule}]" if is_blocked else "Normal"
                        self.log(f"Browser: {browser_name} | {title[:50]}... [{status_str}]")

                        if self.on_activity_detected:
                            self.on_activity_detected(browser_name, title, is_blocked)

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
        while self.is_running:
            uri = f"ws://{self.server_ip}:{self.server_port}"
            try:
                self.log(f"Menghubungkan ke server {uri}...")
                async with websockets.connect(uri, ping_interval=15, ping_timeout=10) as ws:
                    self._ws = ws
                    self.is_connected = True
                    self.log("✅ Berhasil terhubung ke PC Server!")
                    if self.on_connection_status:
                        self.on_connection_status(True)

                    reg_msg = create_message(TYPE_REGISTER, {
                        "client_id": self.client_id,
                        "hostname": self.hostname,
                        "rules_count": len(self.watcher.blocked_rules)
                    })
                    await ws.send(reg_msg)

                    async for raw_msg in ws:
                        msg = parse_message(raw_msg)
                        mtype = msg.get("type")
                        payload = msg.get("payload", {})

                        if mtype == TYPE_UPDATE_RULES:
                            new_rules = payload.get("rules", [])
                            self.watcher.update_rules(new_rules)
                            self.config["cached_rules"] = new_rules
                            save_client_config(self.config)
                            self.log(f"Menerima pembaruan aturan ({len(new_rules)} kata kunci/domain).")

                        elif mtype == TYPE_FORCE_CLOSE:
                            mode = payload.get("mode", "tab")
                            hwnd, btitle, bname = find_top_browser_window()
                            if hwnd:
                                if mode == "window":
                                    close_entire_window(hwnd)
                                    self.log(f"🚨 Menutup seluruh jendela browser {bname} ('{btitle[:30]}...')")
                                else:
                                    close_active_tab(hwnd)
                                    self.log(f"🚨 Menutup tab aktif browser {bname} ('{btitle[:30]}...')")
                            else:
                                self.log("Perintah tutup tab diterima, tetapi tidak ada jendela browser aktif yang ditemukan.")

                        elif mtype == TYPE_PING:
                            await ws.send(create_message(TYPE_PONG))

            except (websockets.exceptions.ConnectionClosed, OSError, Exception):
                self.is_connected = False
                self._ws = None
                if self.on_connection_status:
                    self.on_connection_status(False)
                await asyncio.sleep(4)

    def stop(self):
        self.is_running = False
