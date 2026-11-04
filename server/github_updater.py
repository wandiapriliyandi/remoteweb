"""Modul GitHub Updater untuk Server Admin.
Memeriksa versi rilis terbaru di GitHub Releases dan memperbarui file executable ServerAdmin.exe secara otomatis.
"""
import os
import sys
import time
import json
import urllib.request
import subprocess
from typing import Callable, Optional, Dict, Any

from shared.protocol import APP_VERSION, is_newer_version

GITHUB_REPO = "wandiapriliyandi/remoteweb"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def get_server_exe_path() -> str:
    """Mendapatkan path file ServerAdmin.exe resmi di AppData atau executable aktif."""
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    installed = os.path.join(local_app_data, "RemotePCWebMonitor", "ServerAdmin.exe")
    if os.path.exists(installed):
        return installed

    if getattr(sys, 'frozen', False):
        return sys.executable

    dist_exe = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist", "ServerAdmin.exe"))
    return dist_exe

def check_github_update() -> Dict[str, Any]:
    """
    Mengecek ketersediaan rilis baru di GitHub Releases.
    Mengembalikan dictionary status:
    {
        "has_update": bool,
        "latest_version": str,
        "current_version": str,
        "server_asset_url": Optional[str],
        "client_asset_url": Optional[str],
        "release_notes": str,
        "html_url": str,
        "error": Optional[str]
    }
    """
    result = {
        "has_update": False,
        "latest_version": APP_VERSION,
        "current_version": APP_VERSION,
        "server_asset_url": None,
        "client_asset_url": None,
        "release_notes": "",
        "html_url": f"https://github.com/{GITHUB_REPO}/releases",
        "error": None
    }

    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={
                "User-Agent": "RemoteWebMonitor-Server-Updater/1.0",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        tag_name = data.get("tag_name", "").lstrip("v").strip()
        result["latest_version"] = tag_name
        result["release_notes"] = data.get("body", "")
        result["html_url"] = data.get("html_url", result["html_url"])

        # Cari file asset yang cocok di release (utamakan nama persis)
        assets = data.get("assets", [])
        for asset in assets:
            name = asset.get("name", "").lower()
            url = asset.get("browser_download_url")
            if name == "serveradmin.exe":
                result["server_asset_url"] = url
            elif name == "clientagent.exe":
                result["client_asset_url"] = url

        # Fallback jika nama persis tidak ditemukan
        if not result["server_asset_url"]:
            for asset in assets:
                name = asset.get("name", "").lower()
                if "serveradmin" in name and name.endswith(".exe"):
                    result["server_asset_url"] = asset.get("browser_download_url")
                    break
        if not result["client_asset_url"]:
            for asset in assets:
                name = asset.get("name", "").lower()
                if "clientagent" in name and name.endswith(".exe"):
                    result["client_asset_url"] = asset.get("browser_download_url")
                    break

        if is_newer_version(tag_name, APP_VERSION):
            result["has_update"] = True

    except urllib.error.HTTPError as e:
        if e.code == 404:
            result["error"] = "Belum ada rilis resmi (Release) yang dipublikasikan di repositori GitHub."
        else:
            result["error"] = f"HTTP Error {e.code}: {e.reason}"
    except Exception as e:
        result["error"] = f"Gagal memeriksa pembaruan: {e}"

    return result

def download_file_with_progress(
    url: str,
    destination: str,
    on_progress: Optional[Callable[[int, int], None]] = None
) -> bool:
    """Mengunduh file dari URL dengan callback progres."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RemoteWebMonitor-Server-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=60) as response, open(destination, "wb") as out_file:
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
            if f.read(2) != b"MZ":
                os.remove(destination)
                return False

        return True
    except Exception as e:
        print(f"[GH_UPDATER] Gagal mengunduh file: {e}")
        if os.path.exists(destination):
            try:
                os.remove(destination)
            except Exception:
                pass
        return False

def run_server_detached_updater_batch(new_exe_path: str, target_exe_path: str) -> bool:
    """Menjalankan script batch terpisah untuk menimpa file ServerAdmin.exe lama dan merestart aplikasi."""
    temp_dir = os.environ.get("TEMP", os.path.expanduser("~\\AppData\\Local\\Temp"))
    bat_path = os.path.join(temp_dir, f"update_server_{int(time.time())}.bat")
    current_pid = os.getpid()
    target_dir = os.path.dirname(os.path.abspath(target_exe_path))

    bat_content = f"""@echo off
setlocal enabledelayedexpansion

:: 1. Hapus variabel lingkungan PyInstaller agar executable baru tidak mewarisi cache MEIPASS lama
set _MEIPASS2=
set _MEIPASS=
set PYTHONHOME=
set PYTHONPATH=

:: 2. Jeda agar aplikasi server berhenti sepenuhnya
timeout /t 2 /nobreak > nul

:: 3. Matikan proses lama (PID dan nama proses) untuk melepaskan file lock
taskkill /F /PID {current_pid} > nul 2>&1
taskkill /F /IM ServerAdmin.exe > nul 2>&1

:: 4. Loop menimpa file lama dengan file baru (hingga 10 kali retry jika file masih terkunci)
set SUCCESS=0
for /L %%i in (1,1,10) do (
    if !SUCCESS! equ 0 (
        copy /y "{new_exe_path}" "{target_exe_path}" > nul 2>&1
        if not errorlevel 1 (
            set SUCCESS=1
        ) else (
            timeout /t 1 /nobreak > nul
        )
    )
)

if !SUCCESS! equ 1 (
    del "{new_exe_path}" > nul 2>&1
    :: 5. Jalankan kembali Server Admin baru dengan direktori kerja yang tepat
    cd /d "{target_dir}"
    start "" /D "{target_dir}" "{target_exe_path}"
)

:: 6. Bersihkan script batch
del "%~f0" > nul 2>&1
"""

    try:
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000
        flags = DETACHED_PROCESS | CREATE_NO_WINDOW

        # Bersihkan _MEIPASS2 dari env child process
        clean_env = os.environ.copy()
        clean_env.pop("_MEIPASS2", None)
        clean_env.pop("_MEIPASS", None)

        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=flags,
            close_fds=True,
            env=clean_env
        )
        return True
    except Exception as e:
        print(f"[GH_UPDATER] Gagal menjalankan script updater server: {e}")
        return False

def perform_server_update(
    download_url: str,
    on_status: Optional[Callable[[str, int], None]] = None
) -> bool:
    """Alur lengkap: unduh file baru, verifikasi, jalankan batch runner, lalu keluar dari proses."""
    target_exe = get_server_exe_path()
    install_dir = os.path.dirname(target_exe)
    os.makedirs(install_dir, exist_ok=True)

    new_exe = os.path.join(install_dir, "ServerAdmin_new.exe")

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

    if run_server_detached_updater_batch(new_exe, target_exe):
        time.sleep(0.5)
        os._exit(0)
        return True

    if on_status:
        on_status("failed", 0)
    return False

