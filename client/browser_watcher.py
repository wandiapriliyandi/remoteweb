"""Modul pemantau browser dan penegak aturan pemblokiran di Windows."""
import ctypes
from ctypes import wintypes, byref
import time
import os
from typing import Optional, Tuple, List, Callable

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

def force_foreground_window(hwnd: int):
    """
    Memaksa jendela target menjadi foreground aktif meskipun aplikasi pemanggil
    sedang berada di latar belakang (background), menggunakan teknik AttachThreadInput.
    """
    try:
        fore_hwnd = user32.GetForegroundWindow()
        if fore_hwnd == hwnd:
            return

        fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
        cur_thread = kernel32.GetCurrentThreadId()

        # Lampirkan thread input untuk melewati batasan keamanan SetForegroundWindow Windows
        user32.AttachThreadInput(cur_thread, fore_thread, True)
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(cur_thread, fore_thread, False)
    except Exception as e:
        try:
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

def close_active_tab(hwnd: int):
    """
    Menutup tab yang sedang aktif di browser dengan mengirimkan kombinasi Ctrl + W secara handal.
    """
    try:
        force_foreground_window(hwnd)
        time.sleep(0.06)

        scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
        scan_w = user32.MapVirtualKeyW(VK_W, 0)

        # Tekan Ctrl + W (dengan scancode agar dikenali peramban Chromium/Firefox)
        user32.keybd_event(VK_CONTROL, scan_ctrl, 0, 0)
        user32.keybd_event(VK_W, scan_w, 0, 0)
        time.sleep(0.08)
        user32.keybd_event(VK_W, scan_w, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, scan_ctrl, KEYEVENTF_KEYUP, 0)
    except Exception:
        # Fallback jika gagal: kirim pesan close ke jendela
        try:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        except Exception:
            pass

def close_entire_window(hwnd: int):
    """Menutup seluruh jendela browser secara paksa."""
    try:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    except Exception:
        pass

def get_active_window_info() -> Tuple[int, str, str]:
    """
    Mendapatkan handle jendela aktif (hwnd), judul jendela (title),
    dan nama proses eksekutabel (process_name).
    """
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

def find_top_browser_window() -> Tuple[int, str, str]:
    """
    Mencari jendela browser yang sedang dibuka di Windows,
    baik jendela yang sedang di depan (foreground) maupun jendela browser teratas.
    """
    # 1. Cek dulu apakah jendela foreground saat ini adalah browser
    hwnd, title, proc_name = get_active_window_info()
    if proc_name in BROWSER_PROCESSES:
        return hwnd, title, BROWSER_PROCESSES.get(proc_name, proc_name)

    # 2. Jika bukan foreground (misal admin remote klik saat user sedang tidak aktif),
    # cari jendela browser yang terlihat (visible) di layar
    found_hwnd = 0
    found_title = ""
    found_name = ""

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def enum_windows_callback(h, lparam):
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
                return False # Berhenti enumerasi, ambil yang pertama
        return True

    user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    return found_hwnd, found_title, found_name

class BrowserWatcher:
    def __init__(self, check_interval: float = 0.5):
        self.check_interval = check_interval
        self.is_running = False
        self.blocked_rules: List[str] = []

    def update_rules(self, rules: List[str]):
        self.blocked_rules = [r.strip().lower() for r in rules if r.strip()]

    def is_violating(self, title: str, url_or_snippet: str) -> Tuple[bool, str]:
        content_to_check = f"{title.lower()} {url_or_snippet.lower()}"
        for rule in self.blocked_rules:
            if rule in content_to_check:
                return True, rule
        return False, ""

    def inspect_once(self) -> Optional[Tuple[str, str, str, bool, str]]:
        hwnd, title, proc_name = get_active_window_info()
        if not hwnd or not proc_name:
            return None

        is_browser = proc_name in BROWSER_PROCESSES
        browser_name = BROWSER_PROCESSES.get(proc_name, proc_name)

        if not is_browser or not title:
            return None

        is_blocked, matched_rule = self.is_violating(title, "")

        if is_blocked:
            # Langsung tutup tab browser tersebut secara handal!
            close_active_tab(hwnd)
            return (browser_name, title, f"[TERBLOKIR: {matched_rule}]", True, matched_rule)

        return (browser_name, title, title, False, "")
