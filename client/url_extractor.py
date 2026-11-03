"""Pengekstrak URL browser menggunakan Windows UI Automation / Accessibility API."""
import ctypes
from ctypes import wintypes, POINTER, c_void_p, c_wchar_p, Structure, HRESULT
import re
from typing import Optional

user32 = ctypes.windll.user32
ole32 = ctypes.windll.ole32

# Inisialisasi COM thread
def init_com():
    try:
        ole32.CoInitialize(None)
    except Exception:
        pass

def uninit_com():
    try:
        ole32.CoUninitialize()
    except Exception:
        pass

def extract_url_from_title(title: str) -> Optional[str]:
    """Mengekstrak kemungkinan domain atau URL dari judul jendela browser."""
    if not title:
        return None
    # Cek apakah judul mengandung domain umum
    domain_match = re.search(r"([a-zA-Z0-9-]+\.(?:com|org|net|id|co\.id|edu|gov|io|ai|xyz|me|tv|cc|info))", title, re.IGNORECASE)
    if domain_match:
        return domain_match.group(1).lower()
    return None

