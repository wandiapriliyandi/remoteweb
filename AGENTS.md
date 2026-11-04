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
- Seluruh 9 skenario pengujian (Sintaks kode, SQLite AppData, Penyimpanan Konfigurasi, Protokol Pesan, Semantic Versioning, dan GitHub Updater) harus berstatus **OK (PASS)**.
- Jika ada satu saja pengujian yang gagal, batalkan proses komit dan perbaiki kodenya terlebih dahulu.
