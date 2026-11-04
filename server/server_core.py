"""WebSocket Server Engine untuk PC Server Admin dengan Layanan Auto-Update Lokal."""
import asyncio
import http.server
import json
import os
import socket
import sys
import threading
import time
from typing import Callable, Dict, List, Optional
import websockets
from websockets.server import WebSocketServerProtocol

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
    parse_message
)

class ClientSession:
    """Menyimpan data sesi dan aktivitas live dari PC Client."""
    def __init__(self, websocket: WebSocketServerProtocol, client_id: str, hostname: str, ip: str, version: str = "1.0.0"):
        self.websocket = websocket
        self.client_id = client_id
        self.hostname = hostname
        self.ip = ip
        self.version = version
        self.update_status = ""
        self.connected_at = time.strftime("%H:%M:%S")
        self.last_seen = time.time()
        self.current_browser = "Tidak aktif"
        self.current_title = "Belum ada aktivitas"
        self.current_url = ""
        self.is_last_blocked = False
        self.last_matched_rule = ""
        self.violation_count = 0

class UpdateHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Handler HTTP sederhana untuk melayani download ClientAgent.exe ke client."""
    def do_GET(self):
        exe_path = RemoteServerEngine.find_client_exe_path()
        if not exe_path or not os.path.exists(exe_path):
            self.send_error(404, "File ClientAgent.exe tidak ditemukan di server.")
            return

        try:
            file_size = os.path.getsize(exe_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", 'attachment; filename="ClientAgent.exe"')
            self.send_header("Content-Length", str(file_size))
            self.end_headers()

            with open(exe_path, "rb") as f:
                while True:
                    chunk = f.read(64 * 1024)
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        break
        except Exception as e:
            try:
                self.send_error(500, f"Error: {e}")
            except Exception:
                pass

    def log_message(self, format, *args):
        # Mute logging console HTTP request bawaan
        pass

class RemoteServerEngine:
    def __init__(self, port: int = 8765):
        self.port = port
        self.http_port = port + 1
        self.clients: Dict[str, ClientSession] = {}
        self.ws_to_id: Dict[WebSocketServerProtocol, str] = {}
        self.is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._server = None
        self._httpd: Optional[http.server.ThreadingHTTPServer] = None

        self.active_rules: List[str] = []

        # Callbacks untuk GUI
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_clients_changed: Optional[Callable[[], None]] = None
        self.on_activity_received: Optional[Callable[[str, dict], None]] = None

    def log(self, message: str):
        if self.on_log:
            self.on_log(message)
        else:
            print(f"[SERVER] {message}")

    @staticmethod
    def find_client_exe_path() -> Optional[str]:
        """Menemukan lokasi file ClientAgent.exe di server."""
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(base_dir, "dist", "ClientAgent.exe"),
            os.path.join(base_dir, "ClientAgent.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "RemotePCWebMonitor", "ClientAgent.exe")
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    @staticmethod
    def get_local_ip() -> str:
        """Mendapatkan alamat IP lokal PC Server dalam jaringan WiFi/LAN."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def start(self, host: str = "0.0.0.0"):
        if self.is_running:
            return
        self.is_running = True
        
        # 1. Jalankan WebSocket server
        self._thread = threading.Thread(target=self._run_event_loop, args=(host,), daemon=True)
        self._thread.start()

        # 2. Jalankan HTTP Update Server di port port + 1 (misal: 8766)
        self._start_http_update_server(host)

    def _start_http_update_server(self, host: str):
        """Memulai layanan file HTTP lokal untuk mendistribusikan file update ClientAgent.exe."""
        try:
            self._httpd = http.server.ThreadingHTTPServer((host, self.http_port), UpdateHTTPHandler)
            threading.Thread(target=self._httpd.serve_forever, daemon=True).start()
            local_ip = self.get_local_ip()
            self.log(f"Layanan Update Client aktif di http://{local_ip}:{self.http_port}/ClientAgent.exe")
        except Exception as e:
            self.log(f"Peringatan: Gagal menjalankan HTTP update server di port {self.http_port}: {e}")

    def _run_event_loop(self, host: str):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_server(host))
        self._loop.run_forever()

    async def _start_server(self, host: str):
        try:
            self._server = await websockets.serve(self._handle_client, host, self.port)
            local_ip = self.get_local_ip()
            self.log(f"Server Admin aktif di ws://{local_ip}:{self.port} (Siap menerima client)")
        except Exception as e:
            self.log(f"Gagal menjalankan server: {e}")
            self.is_running = False

    async def _handle_client(self, websocket: WebSocketServerProtocol):
        remote_ip = websocket.remote_address[0]
        temp_id = f"{remote_ip}:{websocket.remote_address[1]}"
        client_session: Optional[ClientSession] = None

        try:
            async for raw_msg in websocket:
                msg = parse_message(raw_msg)
                mtype = msg.get("type")
                payload = msg.get("payload", {})

                if mtype == TYPE_REGISTER:
                    client_id = payload.get("client_id", temp_id)
                    hostname = payload.get("hostname", "Unknown-PC")
                    client_version = payload.get("version", "1.0.0")
                    client_session = ClientSession(websocket, client_id, hostname, remote_ip, version=client_version)
                    
                    self.clients[client_id] = client_session
                    self.ws_to_id[websocket] = client_id
                    self.log(f"🟢 PC Client Terhubung: {hostname} ({remote_ip}) [Versi: v{client_version}]")

                    if self.active_rules:
                        sync_msg = create_message(TYPE_UPDATE_RULES, {"rules": self.active_rules})
                        await websocket.send(sync_msg)

                    if self.on_clients_changed:
                        self.on_clients_changed()

                elif mtype == TYPE_URL_ACTIVITY:
                    if client_session:
                        client_session.last_seen = time.time()
                        client_session.current_browser = payload.get("browser", "Browser")
                        client_session.current_title = payload.get("title", "")
                        client_session.current_url = payload.get("url_snippet", "")
                        is_blocked = payload.get("is_blocked", False)
                        client_session.is_last_blocked = is_blocked
                        client_session.last_matched_rule = payload.get("matched_rule", "")

                        if is_blocked:
                            client_session.violation_count += 1
                            self.log(f"🚨 [BLOKIR] {client_session.hostname} mencoba membuka: '{client_session.current_title[:40]}' -> TAB DITUTUP OTOMATIS!")

                        if self.on_clients_changed:
                            self.on_clients_changed()

                elif mtype == TYPE_UPDATE_PROGRESS:
                    if client_session:
                        status = payload.get("status", "")
                        percent = payload.get("percent", 0)
                        client_session.update_status = f"{status} ({percent}%)"
                        if status == "downloading":
                            self.log(f"📥 [UPDATE] {client_session.hostname} sedang mengunduh: {percent}%")
                        elif status == "installing":
                            self.log(f"⚙️ [UPDATE] {client_session.hostname} sedang memasang file baru...")
                        elif status == "failed":
                            self.log(f"❌ [UPDATE] {client_session.hostname} gagal mengunduh update.")
                        
                        if self.on_clients_changed:
                            self.on_clients_changed()

                elif mtype == TYPE_PING:
                    await websocket.send(create_message(TYPE_PONG))

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception:
            pass
        finally:
            if websocket in self.ws_to_id:
                cid = self.ws_to_id.pop(websocket)
                if cid in self.clients:
                    hname = self.clients[cid].hostname
                    del self.clients[cid]
                    self.log(f"🔴 PC Client Terputus: {hname} ({remote_ip})")
                    if self.on_clients_changed:
                        self.on_clients_changed()

    def broadcast_rules(self, rules: List[str]):
        """Kirim daftar aturan kata kunci/domain terbaru ke SEMUA client."""
        self.active_rules = rules
        msg = create_message(TYPE_UPDATE_RULES, {"rules": rules})
        self._broadcast(msg)
        self.log(f"Mengirim aturan pemblokiran ({len(rules)} kata kunci) ke {len(self.clients)} client.")

    def broadcast_update(self, version: str = APP_VERSION, changelog: str = "") -> int:
        """Kirim perintah pembaruan versi ke SEMUA client yang online."""
        local_ip = self.get_local_ip()
        download_url = f"http://{local_ip}:{self.http_port}/ClientAgent.exe"
        
        payload = {
            "version": version,
            "download_url": download_url,
            "changelog": changelog or f"Pembaruan fitur versi {version}"
        }
        msg = create_message(TYPE_UPDATE_AVAILABLE, payload)
        self._broadcast(msg)
        count = len(self.clients)
        self.log(f"🚀 Menyiarkan instruksi update v{version} ke {count} PC Client.")
        return count

    def update_single_client(self, client_id: str, version: str = APP_VERSION, changelog: str = "") -> bool:
        """Kirim perintah pembaruan versi ke SATU client tertentu."""
        session = self.clients.get(client_id)
        if not session:
            return False

        local_ip = self.get_local_ip()
        download_url = f"http://{local_ip}:{self.http_port}/ClientAgent.exe"
        payload = {
            "version": version,
            "download_url": download_url,
            "changelog": changelog or f"Pembaruan fitur versi {version}"
        }
        msg = create_message(TYPE_UPDATE_AVAILABLE, payload)
        self._send_to_ws(session.websocket, msg)
        self.log(f"🚀 Mengirim instruksi update v{version} ke {session.hostname}.")
        return True

    def send_force_close_to_client(self, client_id: str, mode: str = "tab"):
        """Kirim perintah paksa tutup tab atau jendela browser ke SATU client."""
        session = self.clients.get(client_id)
        if session:
            msg = create_message(TYPE_FORCE_CLOSE, {"mode": mode})
            self._send_to_ws(session.websocket, msg)
            action_desc = "TUTUP SELURUH JENDELA" if mode == "window" else "TUTUP TAB"
            self.log(f"Mengirim perintah {action_desc} ke client {session.hostname}.")

    def _broadcast(self, msg: str):
        if not self._loop or not self.is_running:
            return
        for session in list(self.clients.values()):
            asyncio.run_coroutine_threadsafe(session.websocket.send(msg), self._loop)

    def _send_to_ws(self, ws: WebSocketServerProtocol, msg: str):
        if not self._loop or not self.is_running:
            return
        asyncio.run_coroutine_threadsafe(ws.send(msg), self._loop)

    def stop(self):
        self.is_running = False
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
        if self._server and self._loop:
            self._loop.call_soon_threadsafe(self._server.close)
