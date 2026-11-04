# Arsitektur Resmi Pembaruan Aplikasi (Updater Architecture)
> **PENTING (STANDAR BAKU - JANGAN DIUBAH / DO NOT ALTER)**:  
> Dokumen ini menjelaskan mekanisme pembaruan mandiri (*self-update*) dan instalasi pada RemoteWebMonitor. Seluruh asisten AI dan pengembang WAJIB mempertahankan konsep ini.

---

## 1. Latar Belakang Masalah (Root Cause)
Pada aplikasi Windows berbasis **PyInstaller Single-File (`--onefile`)**:
1. Saat berkas executable dijalankan, PyInstaller bootloader mengekstrak pustaka Python runtime ke folder sementara: `%LOCALAPPDATA%\Temp\_MEIxxxxxx`.
2. PyInstaller menetapkan *environment variable* `_MEIPASS2` dan `_MEIPASS` yang menunjuk ke folder sementara tersebut.
3. **Akar Masalah**: Jika aplikasi me-restart dirinya sendiri atau meluncurkan file baru menggunakan subprocess biasa (`subprocess.Popen`), batch script, atau PowerShell runner, proses baru **mewarisi environment variable `_MEIPASS2` dari proses lama**.
4. Begitu proses lama ditutup dan folder `%TEMP%` lama terhapus oleh sistem, proses baru yang mewarisi variabel tersebut akan mencari berkas DLL di direktori `%TEMP%` lama yang sudah hilang.
5. Akibatnya Windows memunculkan dialog kesalahan fatal:
   > *"Failed to load Python DLL ... C:\Users\...\AppData\Local\Temp\_MEIxxxxx\python311.dll"*

---

## 2. Solusi Permanen: Native C# Executable (`assets/Updater.exe`)
Untuk menyelesaikan masalah ini secara 100% tuntas, mekanisme pembaruan **DILARANG** menggunakan runtime Python atau script batch/powershell turunan yang mewarisi environment variabel parent.

Digunakan binary C# Windows native murni (**`updater_source/Updater.cs`** -> dikompilasi menjadi **`assets/Updater.exe`** ukuran ~5 KB) dengan keunggulan:
- **Zero Python Dependency**: Dijalankan langsung oleh Windows .NET Framework 4.0+ bawaan OS tanpa butuh Python runtime.
- **Pembersihan Environment Total**:
  ```csharp
  // Membersihkan variabel PyInstaller agar proses baru fresh
  psi.EnvironmentVariables.Remove("_MEIPASS2");
  psi.EnvironmentVariables.Remove("_MEIPASS");
  psi.EnvironmentVariables.Remove("PYTHONHOME");
  psi.EnvironmentVariables.Remove("PYTHONPATH");
  ```
- **Peluncuran via Windows Explorer Shell**:
  Meluncurkan executable baru melalui Windows Shell (`explorer.exe "<path_exe>"`) sehingga proses baru benar-benar menjadi proses *top-level root* baru yang bersih dan terisolasi dari proses instalasi/updater sebelumnya.
- **Penanganan File Lock yang Andal**:
  - Menunggu proses lama berhenti (`WaitForExit`).
  - Jika masih terkunci, proses lama dihentikan secara paksa (`Kill`).
  - Melakukan perulangan retry (hingga 10 kali jeda 500ms).
  - Mengganti (*overwrite*) file target lama dengan file unduhan baru.

---

## 3. Kompilasi & Distribusi
1. **Kompilasi Otomatis di CI/CD (`.github/workflows/build-and-release.yml`)**:
   ```powershell
   & "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /out:assets\Updater.exe "updater_source\Updater.cs"
   ```
2. **Penyertaan di Bundle Installer & Client/Server**:
   - `assets/Updater.exe` disertakan dalam seluruh paket rilis GitHub.
   - Installer Wizard (`installer/setup_gui.py` & `setup_client_gui.py`) otomatis menyalin `Updater.exe` ke direktori instalasi target (`%LOCALAPPDATA%\RemotePCWebMonitor\Updater.exe`).
   - Server Admin dan Client Agent memanggil `Updater.exe` saat memperbarui aplikasi.

---

## 4. Mekanisme Safe-Copy pada Installer Setup
Saat pengguna menjalankan installer (`Setup_RemoteMonitor.exe`):
1. **Auto-Close**: Installer otomatis mendeteksi dan menghentikan `ServerAdmin.exe` atau `ClientAgent.exe` lama agar berkas tidak terkunci.
2. **Rename Fallback**: Jika sistem Windows menahan kunci file sesaat, installer melakukan trik me-rename file lama menjadi `.old_<timestamp>`, menimpa dengan file baru, lalu menjadwalkan penghapusan file lama.
3. **Retry Loop**: Diterapkan retry 5 kali dengan jeda waktu untuk menjamin keberhasilan instalasi 100%.

---

## 5. Ringkasan Aturan Bagi Developer & AI
- ⛔ **JANGAN PERNAH** menghapus `Updater.exe` atau `updater_source/Updater.cs`.
- ⛔ **JANGAN PERNAH** mengubah pemanggilan update kembali ke batch file mentah atau subprocess python langsung tanpa isolasi environment `_MEIPASS2`.
- ✅ **SELALU PERTAHANKAN** peluncuran aplikasi baru melalui mekanisme native C# atau Windows Shell murni.

