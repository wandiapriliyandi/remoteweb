"""WebSocket Server Engine untuk PC Server Admin."""
import asyncio
import json
import socket
import threading
import time
from typing import Callable, Dict, List, Optional
import websockets
from websockets.server import WebSocketServerProtocol

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

class ClientSession:
    """Menyimpan data sesi dan aktivitas live dari PC Client."""
    def __init__(self, websocket: WebSocketServerProtocol, client_id: str, hostname: str, ip: str):
        self.websocket = websocket
        self.client_id = client_id
        self.hostname = hostname
        self.ip = ip
        self.connected_at = time.strftime("%H:%M:%S")
        self.last_seen = time.time()
        self.current_browser = "Tidak aktif"
        self.current_title = "Belum ada aktivitas"
        self.current_url = ""
        self.is_last_blocked = False
        self.last_matched_rule = ""
        self.violation_count = 0

class RemoteServerEngine:
    def __init__(self, port: int = 8765):
        self.port = port
        self.clients: Dict[str, ClientSession] = {}
        self.ws_to_id: Dict[WebSocketServerProtocol, str] = {}
        self.is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._server = None

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
        self._thread = threading.Thread(target=self._run_event_loop, args=(host,), daemon=True)
        self._thread.start()

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
                    client_session = ClientSession(websocket, client_id, hostname, remote_ip)
                    
                    self.clients[client_id] = client_session
                    self.ws_to_id[websocket] = client_id
                    self.log(f"PC Client Terhubung: {hostname} ({remote_ip})")

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
                            self.log(f"⚠️ [PELANGGARAN] {client_session.hostname} mencoba membuka: '{client_session.current_title[:40]}' -> TAB DITUTUP OTOMATIS!")

                        if self.on_clients_changed:
                            self.on_clients_changed()

                elif mtype == TYPE_PING:
                    await websocket.send(create_message(TYPE_PONG))

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            self.log(f"Error client: {e}")
        finally:
            if websocket in self.ws_to_id:
                cid = self.ws_to_id.pop(websocket)
                if cid in self.clients:
                    hname = self.clients[cid].hostname
                    del self.clients[cid]
                    self.log(f"PC Client terputus: {hname} ({remote_ip})")
                    if self.on_clients_changed:
                        self.on_clients_changed()

    def broadcast_rules(self, rules: List[str]):
        """Kirim daftar aturan kata kunci/domain terbaru ke SEMUA client."""
        self.active_rules = rules
        msg = create_message(TYPE_UPDATE_RULES, {"rules": rules})
        self._broadcast(msg)
        self.log(f"Mengirim aturan pemblokiran ({len(rules)} kata kunci) ke {len(self.clients)} client.")

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
        if self._server and self._loop:
            self._loop.call_soon_threadsafe(self._server.close)
