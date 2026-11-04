"""Modul protokol komunikasi real-time antara Server Monitor dan PC Client."""
import json
import uuid
from typing import Any, Dict, List

# Versi Aplikasi Saat Ini
APP_VERSION = "1.3.0"

# Tipe Pesan Protokol
TYPE_REGISTER = "REGISTER"                    # Client mendaftar dengan info hostname, IP, dan OS
TYPE_URL_ACTIVITY = "URL_ACTIVITY"            # Client melaporkan judul & URL browser yang sedang aktif
TYPE_UPDATE_RULES = "UPDATE_RULES"            # Server memperbarui daftar kata kunci/domain terlarang
TYPE_FORCE_CLOSE = "FORCE_CLOSE"              # Perintah manual dari server untuk menutup tab yang aktif
TYPE_PING = "PING"                            # Pengecekan koneksi berkala
TYPE_PONG = "PONG"                            # Respon balasan koneksi
TYPE_UPDATE_AVAILABLE = "UPDATE_AVAILABLE"    # Server mengabarkan file pembaruan baru siap diunduh
TYPE_UPDATE_PROGRESS = "UPDATE_PROGRESS"      # Client melaporkan progres pengunduhan/instalasi update

def create_message(msg_type: str, payload: Dict[str, Any] = None) -> str:
    """Membuat format pesan JSON standar."""
    data = {
        "id": str(uuid.uuid4()),
        "type": msg_type,
        "payload": payload or {}
    }
    return json.dumps(data)

def parse_message(raw_text: str) -> Dict[str, Any]:
    """Membaca format pesan JSON."""
    try:
        return json.loads(raw_text)
    except Exception:
        return {"id": "", "type": "UNKNOWN", "payload": {}}

def is_newer_version(new_ver: str, current_ver: str) -> bool:
    """Membandingkan string versi semantic (misal '1.1.0' vs '1.0.0')."""
    try:
        def parse_v(v: str):
            return [int(x) for x in v.strip().lstrip("v").split(".") if x.isdigit()]
        return parse_v(new_ver) > parse_v(current_ver)
    except Exception:
        return new_ver != current_ver
