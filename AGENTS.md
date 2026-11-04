# Aturan Otomatis Proyek RemoteWebMonitor

## 1. Pembaruan Versi Otomatis (Version Auto-Bump)
- Sumber utama nomor versi tunggal (*Single Source of Truth*) berada di `shared/protocol.py` pada variabel `APP_VERSION`.
- **Setiap kali Asisten AI melakukan perubahan, perbaikan bug, atau penambahan fitur** pada kode di folder `client/`, `server/`, `shared/`, atau `installer/`:
  1. AI **WAJIB** menaikkan nomor versi `APP_VERSION` di `shared/protocol.py` (atau menjalankan `python bump_version.py`).
  2. Gunakan aturan Semantic Versioning:
     - Bugfix / refactoring: naikkan **PATCH** (misal `1.1.0` -> `1.1.1`).
     - Fitur baru: naikkan **MINOR** (misal `1.1.0` -> `1.2.0`).
  3. AI wajib menginformasikan perubahan nomor versi terbaru kepada pengguna pada rangkuman respon.
  4. Ingatkan pengguna untuk melakukan compile ulang (`python bump_version.py --build` atau `pyinstaller ClientAgent.spec`) jika perubahan terjadi pada Client agar siap disebarkan via tombol Auto-Update Server.

## 2. Pengujian Wajib Sebelum Push (Pre-Push Automated Testing)
- **AI DILARANG melakukan commit atau push jika belum menjalankan pengujian!**
- Setiap sebelum melakukan push ke GitHub, AI **WAJIB** menjalankan pengujian otomatis:
  ```powershell
  python run_tests.py
  ```
- Seluruh 11 skenario pengujian (Sintaks kode, SQLite AppData, Penyimpanan Konfigurasi, Protokol Pesan, Semantic Versioning, dan GitHub Updater) harus berstatus **OK (PASS)**.
- Jika ada satu saja pengujian yang gagal, batalkan proses komit dan perbaiki kodenya terlebih dahulu.

## 3. Standar Arsitektur Updater & Anti "Failed to Load Python DLL / Local Temp" (STANDAR BAKU - JANGAN DIUBAH)
- **DILARANG MENGUBAH MEKANISME UPDATER NATIVE C#**:
  1. Updater wajib menggunakan binary native C# Windows murni (`updater_source/Updater.cs` -> `assets/Updater.exe`) berukuran ~5 KB tanpa dependensi Python runtime.
  2. `Updater.exe` bertanggung jawab membersihkan environment variable PyInstaller (`_MEIPASS2`, `_MEIPASS`, `PYTHONHOME`, `PYTHONPATH`) dan meluncurkan executable baru melalui Windows Shell (`explorer.exe`) agar proses baru tidak terkontaminasi path folder `%TEMP%` lama.
  3. Baik Setup Wizard (`installer/setup_gui.py` dan `installer/setup_client_gui.py`) maupun updater otomatis **WAJIB** menggunakan fungsi aman `safe_copy_file` (dengan fitur *auto-kill* proses lama, *retry loop*, dan trik *rename fallback* `.old`) untuk menghindari penguncian berkas Windows (`[WinError 32] / PermissionError`).
  4. Dokumentasi teknis lengkap tercatat di `DOCS_UPDATER_ARCHITECTURE.md`.
