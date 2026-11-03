"""Penyimpanan lokal untuk daftar domain yang diblokir."""
import json
import os
from typing import List

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "blocked_sites.json")

DEFAULT_DOMAINS = [
    "youtube.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "roblox.com"
]

def load_blocked_domains() -> List[str]:
    """Memuat daftar domain yang diblokir dari file JSON."""
    if not os.path.exists(CONFIG_FILE):
        save_blocked_domains(DEFAULT_DOMAINS)
        return DEFAULT_DOMAINS.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return DEFAULT_DOMAINS.copy()
    except Exception:
        return DEFAULT_DOMAINS.copy()

def save_blocked_domains(domains: List[str]) -> bool:
    """Menyimpan daftar domain ke file JSON."""
    try:
        # Bersihkan spasi dan huruf kecilkan
        clean_domains = sorted(list(set(d.strip().lower() for d in domains if d.strip())))
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(clean_domains, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

