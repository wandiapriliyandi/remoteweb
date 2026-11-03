"""Modul pemantau browser, inspeksi URL address bar, dan penutupan otomatis tab terlarang."""
import ctypes
from ctypes import wintypes, byref
import time
import os
import re
from typing import Optional, Tuple, List, Set

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Konstanta Windows
WM_CLOSE = 0x0010
VK_CONTROL = 0x11
VK_W = 0x57
KEYEVENTF_KEYUP = 0x0002
SW_RESTORE = 9

BROWSER_PROCESSES = {
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "brave.exe": "Brave",
    "opera.exe": "Opera"
}

def expand_rules(rules: List[str]) -> Set[str]:
    """
    Mengembangkan daftar aturan agar mencakup nama domain dan nama kata kunci intinya.
    Contoh: 'youtube.com' -> 'youtube.com' DAN 'youtube'
    """
    expanded = set()
    for r in rules:
        r = r.strip().lower()
        if not r:
            continue
        expanded.add(r)
        
        # Bersihkan https://, http://, www.
        clean = r.replace("https://", "").replace("http://", "").split("/")[0]
        if clean.startswith("www."):
            clean = clean[4:]
        expanded.add(clean)

        # Ambil nama inti jika berupa domain (misal: 'youtube' dari 'youtube.com')
        parts = clean.split(".")
        if len(parts) >= 2 and len(parts[0]) >= 3:
            expanded.add(parts[0])

    return expanded

def force_foreground_window(hwnd: int):
    """Memaksa jendela target menjadi foreground aktif."""
    try:
        fore_hwnd = user32.GetForegroundWindow()
        if fore_hwnd == hwnd:
            return

        fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
        cur_thread = kernel32.GetCurrentThreadId()

        user32.AttachThreadInput(cur_thread, fore_thread, True)
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(cur_thread, fore_thread, False)
    except Exception:
        try:
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

def close_active_tab(hwnd: int):
    """Menutup tab yang sedang aktif di browser dengan kombinasi Ctrl + W."""
    try:
        force_foreground_window(hwnd)
        time.sleep(0.04)

        scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
        scan_w = user32.MapVirtualKeyW(VK_W, 0)

        user32.keybd_event(VK_CONTROL, scan_ctrl, 0, 0)
        user32.keybd_event(VK_W, scan_w, 0, 0)
        time.sleep(0.06)
        user32.keybd_event(VK_W, scan_w, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, scan_ctrl, KEYEVENTF_KEYUP, 0)
    except Exception:
        try:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        except Exception:
            pass

def close_entire_window(hwnd: int):
    """Menutup seluruh jendela peramban seketika."""
    try:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    except Exception:
        pass

def get_active_window_info() -> Tuple[int, str, str]:
    """Mendapatkan handle jendela aktif (hwnd), judul, dan nama file proses."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return 0, "", ""

    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    title = buff.value

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, byref(pid))
    
    process_name = ""
    h_process = kernel32.OpenProcess(0x1000, False, pid.value)
    if h_process:
        proc_buff = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h_process, 0, proc_buff, byref(size)):
            process_name = os.path.basename(proc_buff.value).lower()
        kernel32.CloseHandle(h_process)

    return hwnd, title, process_name

def get_browser_address_bar_value() -> str:
    """Mencoba membaca teks kolom alamat URL (Address Bar) menggunakan UI Automation."""
    try:
        import uiautomation as auto
        fg = auto.GetForegroundControl()
        if fg:
            edit = fg.EditControl(searchDepth=5)
            if edit.Exists(0, 0):
                val = edit.GetValuePattern().Value
                if val:
                    return val.strip().lower()
    except Exception:
        pass
    return ""

def find_top_browser_window() -> Tuple[int, str, str]:
    """Mencari jendela browser yang sedang dibuka pengguna."""
    hwnd, title, proc_name = get_active_window_info()
    if proc_name in BROWSER_PROCESSES:
        return hwnd, title, BROWSER_PROCESSES.get(proc_name, proc_name)

    found_hwnd = 0
    found_title = ""
    found_name = ""

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def enum_cb(h, lparam):
        nonlocal found_hwnd, found_title, found_name
        if not user32.IsWindowVisible(h):
            return True
        length = user32.GetWindowTextLengthW(h)
        if length == 0:
            return True

        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(h, buff, length + 1)
        t = buff.value

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, byref(pid))
        hp = kernel32.OpenProcess(0x1000, False, pid.value)
        if hp:
            pbuff = ctypes.create_unicode_buffer(1024)
            sz = wintypes.DWORD(1024)
            pname = ""
            if kernel32.QueryFullProcessImageNameW(hp, 0, pbuff, byref(sz)):
                pname = os.path.basename(pbuff.value).lower()
            kernel32.CloseHandle(hp)

            if pname in BROWSER_PROCESSES:
                found_hwnd = h
                found_title = t
                found_name = BROWSER_PROCESSES.get(pname, pname)
                return False
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return found_hwnd, found_title, found_name

class BrowserWatcher:
    def __init__(self, check_interval: float = 0.3):
        self.check_interval = check_interval
        self.is_running = False
        self.blocked_keywords: Set[str] = set()

    def update_rules(self, rules: List[str]):
        """Memperbarui daftar aturan dan mengekspansinya menjadi kata kunci komprehensif."""
        self.blocked_keywords = expand_rules(rules)

    def is_violating(self, title: str, url_bar_text: str) -> Tuple[bool, str]:
        """
        Mengecek apakah judul halaman ATAU teks kolom URL melanggar salah satu kata kunci.
        """
        combined = f"{title.lower()} {url_bar_text.lower()}"
        for kw in self.blocked_keywords:
            if kw in combined:
                return True, kw
        return False, ""

    def inspect_once(self) -> Optional[Tuple[str, str, str, bool, str]]:
        hwnd, title, proc_name = get_active_window_info()
        if not hwnd or not proc_name:
            return None

        is_browser = proc_name in BROWSER_PROCESSES
        browser_name = BROWSER_PROCESSES.get(proc_name, proc_name)

        if not is_browser or not title:
            return None

        # Baca teks kolom alamat URL jika bisa
        url_text = get_browser_address_bar_value()

        # Evaluasi apakah judul ATAU url_text melanggar aturan
        is_blocked, matched_rule = self.is_violating(title, url_text)

        display_text = f"URL: {url_text}" if url_text else title

        if is_blocked:
            # Langsung tutup tab yang melanggar seketika!
            close_active_tab(hwnd)
            return (browser_name, title, f"[TERBLOKIR: {matched_rule}] {display_text}", True, matched_rule)

        return (browser_name, title, display_text, False, "")
