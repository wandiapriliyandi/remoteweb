"""Modul Client Auto-Updater: Mengunduh dan menimpa executable secara senyap di Windows."""
import os
import sys
import time
import urllib.request
import subprocess
from typing import Callable, Optional

def get_target_exe_path() -> str:
    """Mendapatkan path file ClientAgent.exe resmi di AppData atau executable aktif."""
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    installed = os.path.join(local_app_data, "RemotePCWebMonitor", "ClientAgent.exe")
    if os.path.exists(installed):
        return installed

    if getattr(sys, 'frozen', False):
        return sys.executable

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

def get_updater_exe_path() -> str:
    """Mendapatkan path ke executable Updater.exe mandiri."""
    import shutil
    app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
    inst_updater = os.path.join(app_data, "RemotePCWebMonitor", "Updater.exe")
    if os.path.exists(inst_updater):
        return inst_updater

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle_updater = os.path.join(sys._MEIPASS, "assets", "Updater.exe")
        if os.path.exists(bundle_updater):
            try:
                os.makedirs(os.path.dirname(inst_updater), exist_ok=True)
                shutil.copy2(bundle_updater, inst_updater)
                return inst_updater
            except Exception:
                return bundle_updater

    local_updater = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "Updater.exe"))
    if os.path.exists(local_updater):
        return local_updater

    return inst_updater

def run_detached_updater_batch(new_exe_path: str, target_exe_path: str) -> bool:
    """Menjalankan Updater.exe mandiri untuk menimpa file lama dan merestart client ke tray secara bersih."""
    updater_bin = get_updater_exe_path()
    current_pid = str(os.getpid())

    try:
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(
            [updater_bin, current_pid, new_exe_path, target_exe_path, "--minimized"],
            creationflags=CREATE_NO_WINDOW,
            close_fds=True
        )
        return True
    except Exception as e:
        print(f"[UPDATER] Gagal menjalankan Updater.exe: {e}")
        return False

def perform_auto_update(
    download_url: str,
    on_status: Optional[Callable[[str, int], None]] = None
) -> bool:
    """Alur lengkap: unduh file baru, verifikasi, jalankan batch runner, lalu exit."""
    target_exe = get_target_exe_path()
    temp_dir = os.environ.get("TEMP", os.path.expanduser(r"~\AppData\Local\Temp"))
    new_exe = os.path.join(temp_dir, f"ClientAgent_dl_{int(time.time())}.exe")

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

