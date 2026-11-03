"""Penyimpanan konfigurasi lokal untuk PC Client."""
import json
import os
import uuid

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "client_config.json")

def load_client_config() -> dict:
    """Memuat konfigurasi client."""
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
            "x.com",
            "roblox",
            "judi"
        ]
    }
    if not os.path.exists(CONFIG_FILE):
        save_client_config(default_cfg)
        return default_cfg

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Pastikan field default ada
            for k, v in default_cfg.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default_cfg

def save_client_config(cfg: dict) -> bool:
    """Menyimpan konfigurasi client."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

