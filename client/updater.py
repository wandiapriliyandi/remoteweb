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

def run_detached_updater_batch(new_exe_path: str, target_exe_path: str) -> bool:
    """Menjalankan instruksi PowerShell terisolasi untuk menimpa ClientAgent.exe lama dan merestart client ke tray tanpa file script baru."""
    current_pid = os.getpid()
    target_dir = os.path.dirname(os.path.abspath(target_exe_path))

    ps_cmd = (
        f"$ErrorActionPreference = 'SilentlyContinue'; "
        f"Remove-Item Env:_MEIPASS2 -Force; Remove-Item Env:_MEIPASS -Force; "
        f"Remove-Item Env:PYTHONHOME -Force; Remove-Item Env:PYTHONPATH -Force; "
        f"Start-Sleep -Seconds 1; "
        f"try {{ Wait-Process -Id {current_pid} -Timeout 3 }} catch {{}}; "
        f"Stop-Process -Id {current_pid} -Force; "
        f"Stop-Process -Name 'ClientAgent' -Force; "
        f"Start-Sleep -Seconds 1; "
        f"$ok = $false; "
        f"for ($i=0; $i -lt 10; $i++) {{ "
        f"  try {{ Copy-Item -Path '{new_exe_path}' -Destination '{target_exe_path}' -Force; $ok = $true; break }} "
        f"  catch {{ Start-Sleep -Seconds 1 }} "
        f"}}; "
        f"Remove-Item -Path '{new_exe_path}' -Force; "
        f"if ($ok) {{ Start-Process -FilePath '{target_exe_path}' -ArgumentList '--minimized' -WorkingDirectory '{target_dir}' }}"
    )

    try:
        CREATE_NO_WINDOW = 0x08000000
        clean_env = os.environ.copy()
        clean_env.pop("_MEIPASS2", None)
        clean_env.pop("_MEIPASS", None)
        clean_env.pop("PYTHONHOME", None)
        clean_env.pop("PYTHONPATH", None)

        subprocess.Popen(
            ["powershell.exe", "-WindowStyle", "Hidden", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            creationflags=CREATE_NO_WINDOW,
            close_fds=True,
            env=clean_env
        )
        return True
    except Exception as e:
        print(f"[UPDATER] Gagal menjalankan update powershell: {e}")
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

