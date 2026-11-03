"""Penyimpanan lokal untuk daftar domain dan kata kunci yang diblokir."""
import json
import os
import sys
from typing import List

def get_config_file() -> str:
    """Mendapatkan path penyimpanan file konfigurasi yang persisten."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "blocked_sites.json")

DEFAULT_DOMAINS = [
    "youtube",
    "facebook",
    "instagram",
    "tiktok",
    "twitter",
    "roblox",
    "judi",
    "slot"
]

def load_blocked_domains() -> List[str]:
    """Memuat daftar kata kunci/domain yang diblokir."""
    cfg_file = get_config_file()
    if not os.path.exists(cfg_file):
        save_blocked_domains(DEFAULT_DOMAINS)
        return DEFAULT_DOMAINS.copy()
    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return DEFAULT_DOMAINS.copy()
    except Exception:
        return DEFAULT_DOMAINS.copy()

def save_blocked_domains(domains: List[str]) -> bool:
    """Menyimpan daftar kata kunci/domain ke file JSON."""
    try:
        cfg_file = get_config_file()
        clean_domains = sorted(list(set(d.strip().lower() for d in domains if d.strip())))
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(clean_domains, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False
