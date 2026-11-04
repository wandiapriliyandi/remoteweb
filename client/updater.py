"""Modul Client Auto-Updater: Mengunduh dan menimpa executable secara senyap di Windows."""
import os
import sys
import time
import urllib.request
import subprocess
from typing import Callable, Optional

def get_target_exe_path() -> str:
    """Mendapatkan path file ClientAgent.exe yang sedang berjalan atau terpasang."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    
    # Mode development (python script): cari di AppData atau dist
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    installed = os.path.join(local_app_data, "RemotePCWebMonitor", "ClientAgent.exe")
    if os.path.exists(installed):
        return installed

    dist_exe = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist", "ClientAgent.exe"))
    return dist_exe

def download_file_with_progress(
    url: str,
    destination: str,
    on_progress: Optional[Callable[[int, int], None]] = None
) -> bool:
    """Mengunduh file dari URL HTTP server lokal dengan indikator progres."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RemoteWebMonitor-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response, open(destination, "wb") as out_file:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 64 * 1024

            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                if on_progress:
                    on_progress(downloaded, total_size)

        # Validasi file hasil unduhan
        if not os.path.exists(destination) or os.path.getsize(destination) < 1024 * 1024:
            if os.path.exists(destination):
                os.remove(destination)
            return False

        # Cek header executable Windows (MZ)
        with open(destination, "rb") as f:
            header = f.read(2)
            if header != b"MZ":
                os.remove(destination)
                return False

        return True
    except Exception as e:
        print(f"[UPDATER] Gagal mengunduh file: {e}")
        if os.path.exists(destination):
            try:
                os.remove(destination)
            except Exception:
                pass
        return False

def run_detached_updater_batch(new_exe_path: str, target_exe_path: str) -> bool:
    """Menjalankan script batch detached untuk menimpa file exe lama dan merestart client di System Tray."""
    temp_dir = os.environ.get("TEMP", os.path.expanduser("~\\AppData\\Local\\Temp"))
    bat_path = os.path.join(temp_dir, f"update_client_{int(time.time())}.bat")
    current_pid = os.getpid()

    # Buat script batch pengganti executable
    bat_content = f"""@echo off
setlocal enabledelayedexpansion

:: 1. Berikan jeda agar proses lama berhenti sepenuhnya
timeout /t 2 /nobreak > nul

:: 2. Pastikan proses lama mati
taskkill /F /PID {current_pid} > nul 2>&1

:: 3. Timpa file lama dengan file baru
copy /y "{new_exe_path}" "{target_exe_path}" > nul 2>&1
if not errorlevel 1 (
    del "{new_exe_path}" > nul 2>&1
    :: 4. Jalankan kembali aplikasi client langsung ke System Tray
    start "" "{target_exe_path}" --minimized
)

:: 5. Hapus script batch ini
del "%~f0" > nul 2>&1
"""

    try:
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        # Jalankan detached tanpa jendela command prompt
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        flags = DETACHED_PROCESS | CREATE_NO_WINDOW

        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=flags,
            close_fds=True
        )
        return True
    except Exception as e:
        print(f"[UPDATER] Gagal menjalankan script updater: {e}")
        return False

def perform_auto_update(
    download_url: str,
    on_status: Optional[Callable[[str, int], None]] = None
) -> bool:
    """Alur lengkap: unduh file baru, verifikasi, jalankan batch runner, lalu exit."""
    target_exe = get_target_exe_path()
    install_dir = os.path.dirname(target_exe)
    os.makedirs(install_dir, exist_ok=True)
    
    new_exe = os.path.join(install_dir, "ClientAgent_new.exe")

    if on_status:
        on_status("downloading", 0)

    def _progress_cb(downloaded: int, total: int):
        percent = int((downloaded / total) * 100) if total > 0 else 0
        if on_status:
            on_status("downloading", percent)

    success = download_file_with_progress(download_url, new_exe, _progress_cb)
    if not success:
        if on_status:
            on_status("failed", 0)
        return False

    if on_status:
        on_status("installing", 100)

    # Jalankan script batch detached
    if run_detached_updater_batch(new_exe, target_exe):
        time.sleep(0.5)
        # Hentikan proses client saat ini
        os._exit(0)
        return True

    if on_status:
        on_status("failed", 0)
    return False

