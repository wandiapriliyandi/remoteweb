"""Modul untuk mengelola Auto-Start PC Client saat Windows dinyalakan."""
import os
import sys
import winreg

APP_NAME = "RemotePCWebMonitorClient"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def get_launch_command() -> str:
    """Mendapatkan baris perintah untuk menjalankan client secara background."""
    # Jika program dikompilasi jadi exe oleh PyInstaller
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        return f'"{exe_path}"'
    else:
        # Menjalankan script python dengan pythonw.exe (tanpa jendela command prompt hitam)
        python_dir = os.path.dirname(sys.executable)
        pythonw_path = os.path.join(python_dir, "pythonw.exe")
        if not os.path.exists(pythonw_path):
            pythonw_path = sys.executable  # fallback jika pythonw tidak ditemukan

        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "run_client.py"))
        return f'"{pythonw_path}" "{script_path}"'

def is_autostart_enabled() -> bool:
    """Mengecek apakah client sudah terdaftar di registry startup Windows."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(value)
    except FileNotFoundError:
        return False
    except Exception:
        return False

def enable_autostart() -> bool:
    """Mendaftarkan client ke registry startup Windows agar otomatis berjalan saat PC dinyalakan."""
    try:
        cmd = get_launch_command()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Gagal mengaktifkan auto-start: {e}")
        return False

def disable_autostart() -> bool:
    """Menghapus pendaftaran auto-start dari registry Windows."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        print(f"Gagal menonaktifkan auto-start: {e}")
        return False

