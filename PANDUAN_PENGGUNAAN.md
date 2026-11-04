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
- **Auto-Startup Windows (Silent Tray)**: Otomatis berjalan dan terminimalkan langsung ke System Tray saat komputer baru dinyalakan tanpa memunculkan jendela, tanpa mengurangi performa.
- **Silent Auto-Update dari Server (LAN / WiFi)**: Memperbarui fitur di seluruh PC client secara massal langsung dari dashboard Server Admin tanpa perlu mendatangi PC target.

---

## 📦 Paket Installer Siap Pakai (.EXE)

Tersedia file installer di dalam folder `dist/`:

1. **`dist/Setup_Client.exe` (Disarankan untuk Komputer Target / Siswa / Karyawan)**:
   - **Khusus Client Agent saja** (tidak dicampur dengan Server Admin).
   - Pengguna target tidak akan melihat atau bisa mengakses dashboard server.
   - Bisa langsung mengisi IP Server Admin saat instalasi.
   - Otomatis mendaftarkan ke Windows Startup dan terminimalkan ke System Tray.
   - Mengemas file `Uninstall.exe` otomatis ke dalam menu Start.

2. **`dist/Setup_RemoteMonitor.exe` (Installer Gabungan Admin)**:
   - Master Installer Wizard serba guna dengan opsi memilih instalasi Server Admin atau Client Target.

3. **`dist/Uninstall.exe` (Aplikasi Pencopotan / Uninstaller)**:
   - Menghapus aplikasi secara tuntas, menghentikan proses latar belakang, menghapus auto-start registry, dan membersihkan seluruh shortcut.

---

## 🔄 Cara Memperbarui Fitur Client Otomatis (Auto-Update)

Jika Anda merilis pembaruan fitur baru untuk Client:
1. Simpan file `ClientAgent.exe` versi baru di folder `dist/` PC Server Admin.
2. Buka dashboard **Server Admin**.
3. Di sudut kanan atas daftar client, klik tombol **"🚀 Perbarui Semua Client"** (atau klik tombol **"Update"** pada client tertentu).
4. PC Server akan mengirimkan instruksi unduhan ke seluruh client via jaringan lokal (HTTP Port `8766`).
5. PC Client akan:
   - Mengunduh file baru secara senyap di latar belakang.
   - Mengganti file exe lama tanpa bentrok file-lock.
   - Merestart dirinya secara otomatis langsung ke **System Tray** dengan fitur terbaru.

---

## 🗑️ Cara Mencopot Pemasangan (Uninstall)

Terdapat 3 cara mudah untuk menghapus aplikasi dari komputer:
1. **Melalui Start Menu**: Buka Start Menu Windows > cari folder `RemotePCWebMonitor` > klik **"Copot Pemasangan (Uninstall)"**.
2. **Melalui Pengaturan Windows**: Buka **Windows Settings > Apps > Installed Apps** (atau Control Panel) > cari `Remote PC Web Monitor` > klik **Uninstall**.
3. **Melalui Installer**: Jalankan kembali file `Setup_Client.exe` atau `Setup_RemoteMonitor.exe`, sistem otomatis mendeteksi aplikasi sudah terpasang dan menampilkan tombol **"🗑️ Copot (Uninstall)"**.

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
7. Saat komputer baru dinyalakan, client akan langsung otomatis berjalan dan terminimalkan ke **System Tray** (di taskbar pojok kanan bawah dekat jam) tanpa memunculkan jendela di layar. Performa monitoring tetap berjalan 100% di latar belakang.
8. Untuk membuka kembali antarmuka dari latar belakang, klik kanan atau klik dua kali ikon perisai di System Tray lalu pilih **"Buka Aplikasi"**.

---

## ⚙️ Fitur Server Admin:
- **Tambah / Hapus Aturan**: Masukkan kata kunci atau nama situs (contoh: `youtube`, `facebook`, `tiktok`, `roblox`, `judi`, `slot`, dll.).
- **Terapkan ke Semua Client**: Sekali klik, semua client akan menerima aturan baru dan langsung menerapkannya seketika.
- **Live Feed Tab**: Melihat judul halaman atau situs yang sedang dibuka oleh setiap PC client secara langsung.
- **Paksa Tutup Tab (Force Close)**: Tombol darurat bagi admin untuk langsung menutup tab browser yang sedang dibuka di PC client tertentu dari jarak jauh.
- **Pembaruan Fitur Massal**: Memperbarui aplikasi client di semua komputer hanya dengan satu klik.

---

## 📦 Mengubah Menjadi File .EXE (Opsional)
Jika Anda ingin mengompilasi ulang file `.exe`:

1. **Untuk Server**:
   ```bash
   pyinstaller --noconsole --onefile run_server.py
   ```
2. **Untuk Client**:
   ```bash
   pyinstaller --noconsole --onefile --collect-all customtkinter -n ClientAgent run_client.py
   ```
3. **Untuk Uninstaller**:
   ```bash
   pyinstaller --noconsole --onefile --collect-all customtkinter -n Uninstall installer/uninstall_gui.py
   ```
4. **Untuk Installer Khusus Client**:
   ```bash
   pyinstaller --noconsole --onefile --collect-all customtkinter --add-data "dist/ClientAgent.exe;." --add-data "dist/Uninstall.exe;." -n Setup_Client installer/setup_client_gui.py
   ```
File `.exe` siap pakai akan berada di dalam folder `dist/`.
