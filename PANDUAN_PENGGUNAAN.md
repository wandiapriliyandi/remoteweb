# Panduan Penggunaan: Aplikasi Remote Web Monitor & Blocker (LAN / WiFi)

Aplikasi ini terdiri dari dua program desktop berbasis Python:
1. **PC Server (Admin)**: Dashboard kontrol untuk melihat aktivitas browser di setiap PC client secara *real-time* dan mengatur kata kunci/domain yang dilarang.
2. **PC Client (Target)**: Aplikasi latar belakang (*background agent*) yang memantau peramban yang sedang dibuka di PC target, menutup tab terlarang secara otomatis, dan dapat berjalan otomatis saat PC dinyalakan (*Run on Startup*).

---

## 🚀 Keunggulan Metode Ini:
- **Tanpa Edit File Hosts**: 100% aman bagi file sistem Windows.
- **Tanpa Perlu Hak Akses Administrator (UAC)**: Dapat langsung berjalan lancar sebagai pengguna biasa.
- **Live Monitor**: Admin server bisa melihat langsung situs apa yang sedang dibuka oleh client.
- **Deteksi Cepat**: Jika pengguna membuka kata kunci atau domain terlarang (misal: YouTube, Facebook, judi, game), tab browser langsung ditutup secara instan dalam hitungan milidetik.
- **Auto-Startup Windows**: Terdapat tombol sakelar untuk mengaktifkan agar program langsung aktif saat komputer dinyalakan.

---

## 📦 Paket Installer Siap Pakai (.EXE)

Tersedia file master installer terpadu di dalam folder `dist/`:
- **`dist/Setup_RemoteMonitor.exe`**: Master Installer Wizard serba guna.
  - Cukup jalankan file ini di komputer manapun.
  - Terdapat pilihan:
    - 🔘 **PC Client (Komputer Target yang Diawasi)**: Otomatis memasang ke komputer, membuat shortcut Desktop, dan mendaftarkan ke Windows Startup agar aktif saat PC dinyalakan.
    - 🔘 **PC Server (Komputer Admin Pemantau)**: Otomatis memasang dashboard Server Admin dan membuat shortcut Desktop.

---

## 🛠️ Cara Menjalankan Manual via Python

### 1. Di PC Server (Komputer Admin):
1. Buka folder proyek ini di Command Prompt / Terminal.
2. Jalankan perintah:
   ```bash
   python run_server.py
   ```
3. Di bagian atas jendela Server Admin akan muncul alamat IP lokal server (contoh: `ws://192.168.1.50:8765`). Catat alamat IP tersebut.

---

### 2. Di PC Client (Komputer Target):
1. Pastikan PC Client terhubung ke jaringan **WiFi atau LAN yang sama** dengan PC Server.
2. Jalankan aplikasi client:
   ```bash
   python run_client.py
   ```
3. Masukkan **IP Server** (yang muncul di PC Server pada langkah 1).
4. Klik **"Terapkan IP"**.
5. Status di sudut kanan atas akan berubah menjadi **"● Terhubung ke Server"**.
6. Aktifkan sakelar **"Jalankan otomatis saat PC dinyalakan (Run on Startup Windows)"**.
7. Klik tombol **"Sembunyikan Jendela (Jalan di Latar Belakang)"** agar aplikasi bekerja tanpa mengganggu pengguna target.

---

## ⚙️ Fitur Server Admin:
- **Tambah / Hapus Aturan**: Masukkan kata kunci atau nama situs (contoh: `youtube`, `facebook`, `tiktok`, `roblox`, `judi`, `slot`, dll.).
- **Terapkan ke Semua Client**: Sekali klik, semua client akan menerima aturan baru dan langsung menerapkannya seketika.
- **Live Feed Tab**: Melihat judul halaman atau situs yang sedang dibuka oleh setiap PC client secara langsung.
- **Paksa Tutup Tab (Force Close)**: Tombol darurat bagi admin untuk langsung menutup tab browser yang sedang dibuka di PC client tertentu dari jarak jauh.

---

## 📦 Mengubah Menjadi File .EXE (Opsional)
Jika Anda ingin aplikasi ini berupa file `.exe` yang bisa langsung diklik dua kali tanpa harus membuka terminal:

1. **Untuk Server**:
   ```bash
   pyinstaller --noconsole --onefile run_server.py
   ```
2. **Untuk Client**:
   ```bash
   pyinstaller --noconsole --onefile run_client.py
   ```
File `.exe` siap pakai akan berada di dalam folder `dist/`.

