#!/usr/bin/env python3
"""
Skrip Otomasi Pembaruan Versi (Semantic Versioning) & Rilis GitHub
Digunakan untuk menaikkan versi aplikasi secara otomatis pada shared/protocol.py,
serta mempublikasikan Tag rilis ke GitHub untuk build otomatis via GitHub Actions.

Penggunaan:
    python bump_version.py                  # Naikkan versi PATCH (misal 1.1.0 -> 1.1.1)
    python bump_version.py --minor          # Naikkan versi MINOR (misal 1.1.0 -> 1.2.0)
    python bump_version.py --major          # Naikkan versi MAJOR (misal 1.1.0 -> 2.0.0)
    python bump_version.py --set 1.2.5      # Atur manual ke versi tertentu
    python bump_version.py --build          # Naikkan versi & langsung compile ClientAgent.exe lokal
    python bump_version.py --push           # Naikkan versi, commit, tag vX.Y.Z, & push ke GitHub (Memicu Build Otomatis)
"""
import os
import re
import sys
import argparse
import subprocess

PROTOCOL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shared", "protocol.py")

def get_current_version() -> str:
    if not os.path.exists(PROTOCOL_FILE):
        print(f"Error: File '{PROTOCOL_FILE}' tidak ditemukan!")
        sys.exit(1)

    with open(PROTOCOL_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        print("Error: Variabel APP_VERSION tidak ditemukan di shared/protocol.py!")
        sys.exit(1)

    return match.group(1)

def bump_semver(current: str, bump_type: str = "patch") -> str:
    parts = current.strip().lstrip("v").split(".")
    major = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    return f"{major}.{minor}.{patch}"

def save_version(new_version: str):
    with open(PROTOCOL_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r'APP_VERSION\s*=\s*["\'][^"\']+["\']',
        f'APP_VERSION = "{new_version}"',
        content,
        count=1
    )

    with open(PROTOCOL_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

def main():
    parser = argparse.ArgumentParser(description="Pembaruan versi otomatis untuk RemoteWebMonitor")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--patch", action="store_true", help="Naikkan versi PATCH (default)")
    group.add_argument("--minor", action="store_true", help="Naikkan versi MINOR (fitur baru)")
    group.add_argument("--major", action="store_true", help="Naikkan versi MAJOR (perubahan besar)")
    group.add_argument("--set", type=str, metavar="VERSION", help="Tentukan versi spesifik secara manual")
    parser.add_argument("--build", action="store_true", help="Jalankan pyinstaller ClientAgent.spec lokal")
    parser.add_argument("--push", action="store_true", help="Commit, beri Tag git vX.Y.Z, dan push ke GitHub untuk memicu rilis otomatis")

    args = parser.parse_args()

    # 1. Jalankan Pengujian Otomatis Terlebih Dahulu
    print("[TEST] Menjalankan pengujian otomatis (run_tests.py)...")
    test_res = subprocess.run([sys.executable, "run_tests.py"], check=False)
    if test_res.returncode != 0:
        print("\n[GAGAL] Pengujian gagal! Batalkan pembaruan versi dan push.")
        sys.exit(1)
    print("[TEST] Seluruh pengujian berhasil (PASS)!\n")

    current_ver = get_current_version()

    if args.set:
        new_ver = args.set.strip().lstrip("v")
    elif args.major:
        new_ver = bump_semver(current_ver, "major")
    elif args.minor:
        new_ver = bump_semver(current_ver, "minor")
    else:
        new_ver = bump_semver(current_ver, "patch")

    save_version(new_ver)
    print(f"[OK] Versi berhasil diperbarui: v{current_ver} -> v{new_ver}")

    if args.build:
        print("\n[BUILD] Memulai kompilasi ClientAgent.exe dengan PyInstaller...")
        spec_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ClientAgent.spec")
        result = subprocess.run(["pyinstaller", spec_path], check=False)
        if result.returncode == 0:
            import shutil
            dist_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "ClientAgent.exe")
            ver_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", f"ClientAgent_v{new_ver}.exe")
            if os.path.exists(dist_exe):
                shutil.copy2(dist_exe, ver_exe)
            print(f"[BUILD SUKSES] File dist/ClientAgent.exe dan dist/ClientAgent_v{new_ver}.exe berhasil dibuat!")
        else:
            print("[BUILD GAGAL] Terjadi kesalahan saat menjalankan PyInstaller.")

    if args.push:
        tag_name = f"v{new_ver}"
        print(f"\n[GIT] Melakukan commit dan push tag {tag_name} ke GitHub...")
        subprocess.run(["git", "add", "."], check=False)
        subprocess.run(["git", "commit", "-m", f"release: bump version to {tag_name}"], check=False)
        subprocess.run(["git", "tag", tag_name], check=False)
        push_res = subprocess.run(["git", "push", "origin", "main", "--tags"], check=False)
        if push_res.returncode == 0:
            print(f"[RELEASE DIPICU] Tag {tag_name} berhasil di-push ke GitHub!")
            print("GitHub Actions sedang mengkompilasi file .exe dan akan mempublikasikan Release secara otomatis.")
        else:
            print("[GIT WARNING] Gagal melakukan push ke remote GitHub. Pastikan hak akses git sudah login.")

if __name__ == "__main__":
    main()
