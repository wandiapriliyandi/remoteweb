"""Penyimpanan konfigurasi lokal untuk PC Client yang persisten."""
import json
import os
import sys
import uuid

def get_config_file() -> str:
    """Mendapatkan path penyimpanan file konfigurasi client di AppData Local."""
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    app_dir = os.path.join(local_app_data, "RemotePCWebMonitor")
    try:
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, "client_config.json")
    except Exception:
        base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "client_config.json")

def load_client_config() -> dict:
    """Memuat konfigurasi client."""
    cfg_file = get_config_file()
    default_cfg = {
        "client_id": str(uuid.uuid4())[:12],
        "server_ip": "127.0.0.1",
        "server_port": 8765,
        "auto_minimize": True,
        "cached_rules": [
            "youtube",
            "facebook",
            "instagram",
            "tiktok",
            "twitter",
            "roblox",
            "judi",
            "slot"
        ]
    }
    if not os.path.exists(cfg_file):
        save_client_config(default_cfg)
        return default_cfg

    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in default_cfg.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default_cfg

def save_client_config(cfg: dict) -> bool:
    """Menyimpan konfigurasi client."""
    try:
        cfg_file = get_config_file()
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False
