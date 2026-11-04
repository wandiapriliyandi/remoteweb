# 🛡️ RemoteWebMonitor

<p align="center">
  <img src="assets/logo.png" width="160" height="160" alt="RemoteWebMonitor Logo" />
</p>

<p align="center">
  <b>Sistem Pemantauan Browser & Filter Keamanan Web Desktop Real-Time (LAN / Wi-Fi)</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows" alt="Platform Windows" />
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python" alt="Python Version" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
</p>

---

## 📌 Fitur Utama

- **Live URL & Tab Tracking**: Memantau tab dan domain aktif dari browser populer (Google Chrome, Microsoft Edge, Mozilla Firefox, Brave Browser) secara real-time via Windows UIAutomation.
- **Dynamic Web Filtering**: Blokir akses domain atau kata kunci terlarang secara otomatis di PC client.
- **Remote Power Control**: Server Admin dapat mengirim perintah Shutdown, Restart, Sleep, Lock, dan Log Off ke PC Client secara remote.
- **System Tray Mode**: Client berjalan senyap di System Tray dengan opsi auto-start saat Windows boot.
- **Database Riwayat SQLite**: Pencatatan riwayat aktivitas penjelajahan web lengkap dengan filter pencarian dan ekspor ke laporan CSV/Excel.
- **Auto-Update Cerdas**: Server dan Client mendukung pembaruan versi mandiri langsung dari GitHub Releases atau siaran server lokal.

---

## 🚀 Panduan Memulai Cepat

### 1. Menjalankan Server Admin
```powershell
python run_server.py
```
Atau jalankan file executable `ServerAdmin.exe`.

### 2. Menjalankan Client Agent
```powershell
python run_client.py
```
Atau jalankan file executable `ClientAgent.exe`.

### 3. Memasang via Installer Wizard
Jalankan file installer `Setup_RemoteMonitor.exe` untuk memilih peran komputer (Server Admin atau Client PC).

---

## 🧪 Pengujian Otomatis

Seluruh modul dan protokol diverifikasi melalui pengujian otomatis sebelum rilis:
```powershell
python run_tests.py
```

---

## 📦 Pembaruan Versi & Rilis Otomatis

Gunakan skrip otomasi versi:
```powershell
python bump_version.py          # Naikkan versi PATCH (bugfix/refactoring)
python bump_version.py --minor  # Naikkan versi MINOR (fitur baru)
python bump_version.py --push   # Rilis otomatis ke GitHub Releases
```

