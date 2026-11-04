"""Antarmuka GUI Client Desktop (PC Target) dengan Integrasi System Tray."""
import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

from client.client_core import ClientEngine
from client.autostart import (
    is_autostart_enabled,
    enable_autostart,
    disable_autostart,
    sync_autostart_command
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def get_asset_path(filename: str) -> str:
    """Mendapatkan path absolut ke file aset, kompatibel dengan PyInstaller."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, "assets", filename)
        if os.path.exists(p):
            return p
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(base_dir, "assets", filename)
    if os.path.exists(p):
        return p
    return ""

def create_tray_icon_image():
    """Membuat atau memuat ikon perisai untuk System Tray."""
    ico_path = get_asset_path("icon.ico")
    png_path = get_asset_path("logo.png")
    for p in (png_path, ico_path):
        if p and os.path.exists(p):
            try:
                return Image.open(p).convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
            except Exception:
                pass

    img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill="#0284c7", outline="#38bdf8", width=3)
    draw.polygon([(32, 14), (48, 22), (48, 40), (32, 50), (16, 40), (16, 22)], fill="#ffffff")
    return img

class ClientApp(ctk.CTk):
    def __init__(self, start_minimized: bool = False):
        super().__init__()

        self.title("Client Agent - Remote Web Monitor & Filter")
        self.geometry("640x520")
        self.minsize(560, 460)

        ico_file = get_asset_path('icon.ico')
        if ico_file and os.path.exists(ico_file):
            try:
                self.iconbitmap(default=ico_file)
            except Exception:
                self.iconbitmap(ico_file)
            except Exception:
                pass

        self._is_in_tray = start_minimized

        # Jika diminta start_minimized (misal saat boot komputer), sembunyikan jendela sebelum digambar
        if start_minimized:
            self.withdraw()

        self.engine = ClientEngine()
        self.engine.on_log = self._append_log_threadsafe
        self.engine.on_connection_status = self._on_connection_change_threadsafe
        self.engine.on_activity_detected = self._on_activity_detected_threadsafe

        # System tray setup
        self.tray_icon = None

        self._build_ui()

        # 1. Tombol X (Close) NORMAL: menutup aplikasi sepenuhnya seperti umumnya
        self.protocol("WM_DELETE_WINDOW", self._on_exit)

        # 2. Tombol Minimize (_): otomatis menyembunyikan jendela ke System Tray
        self.bind("<Unmap>", self._on_minimize_to_tray)

        # Inisialisasi System Tray Icon di latar belakang
        self._setup_tray()

        # Sinkronisasi registry auto-start jika sebelumnya terdaftar tanpa argumen --minimized
        sync_autostart_command()

        # Jalankan engine client (pemantauan browser & komunikasi WebSocket)
        self.engine.start()

        if start_minimized:
            # Pastikan tetap withdraw setelah build UI selesai
            self.withdraw()
            self._append_log("Aplikasi berjalan di latar belakang (System Tray).")

    def _build_ui(self):
        # 1. Header
        header = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e293b")
        header.pack(fill="x", padx=16, pady=(16, 10))

        # Logo Visual & Judul
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", padx=16, pady=8)

        logo_file = get_asset_path("logo.png")
        if logo_file and os.path.exists(logo_file):
            try:
                pil_logo = Image.open(logo_file).convert("RGBA")
                self.header_logo = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(36, 36))
                lbl_icon = ctk.CTkLabel(title_box, image=self.header_logo, text="")
                lbl_icon.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        title_lbl = ctk.CTkLabel(
            title_box,
            text="WEB MONITOR CLIENT AGENT",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8"
        )
        title_lbl.pack(side="left")

        self.lbl_status = ctk.CTkLabel(
            header,
            text="● Menghubungkan...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f59e0b"
        )
        self.lbl_status.pack(side="right", padx=16, pady=12)

        # 2. Pengaturan Server & Auto-Start Card
        cfg_frame = ctk.CTkFrame(self, corner_radius=10)
        cfg_frame.pack(fill="x", padx=16, pady=6)

        # Baris IP & Port
        row1 = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(10, 6))

        lbl_ip = ctk.CTkLabel(row1, text="IP Server Admin:", font=ctk.CTkFont(size=13))
        lbl_ip.pack(side="left", padx=(0, 6))

        self.entry_ip = ctk.CTkEntry(row1, width=160, font=ctk.CTkFont(size=13))
        self.entry_ip.insert(0, self.engine.server_ip)
        self.entry_ip.pack(side="left", padx=(0, 10))

        lbl_port = ctk.CTkLabel(row1, text="Port:", font=ctk.CTkFont(size=13))
        lbl_port.pack(side="left", padx=(0, 6))

        self.entry_port = ctk.CTkEntry(row1, width=70, font=ctk.CTkFont(size=13))
        self.entry_port.insert(0, str(self.engine.server_port))
        self.entry_port.pack(side="left", padx=(0, 10))

        btn_save_ip = ctk.CTkButton(
            row1,
            text="Terapkan IP",
            width=100,
            command=self._apply_server_ip,
            fg_color="#2563eb",
            hover_color="#1d4ed8"
        )
        btn_save_ip.pack(side="right")

        # Baris Auto-Start Switch
        row2 = ctk.CTkFrame(cfg_frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(4, 10))

        self.switch_autostart = ctk.CTkSwitch(
            row2,
            text="Jalankan otomatis saat PC dinyalakan (Run on Startup Windows)",
            font=ctk.CTkFont(size=13),
            command=self._toggle_autostart
        )
        self.switch_autostart.pack(side="left")

        lbl_hint = ctk.CTkLabel(
            row2,
            text="(Otomatis langsung ke System Tray saat komputer baru nyala)",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        lbl_hint.pack(side="left", padx=8)

        if is_autostart_enabled():
            self.switch_autostart.select()
        else:
            self.switch_autostart.deselect()

        # 3. Card Monitoring Browser Saat Ini
        live_card = ctk.CTkFrame(self, corner_radius=10, fg_color="#111827")
        live_card.pack(fill="x", padx=16, pady=6)

        live_title = ctk.CTkLabel(
            live_card,
            text="⚡ Status Browser PC Saat Ini",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#9ca3af"
        )
        live_title.pack(anchor="w", padx=12, pady=(8, 2))

        self.lbl_current_browser = ctk.CTkLabel(
            live_card,
            text="Browser Aktif: Menunggu aktivitas peramban...",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_current_browser.pack(anchor="w", padx=12, pady=2)

        self.lbl_current_title = ctk.CTkLabel(
            live_card,
            text="Judul / Link: -",
            font=ctk.CTkFont(size=12),
            text_color="#cbd5e1"
        )
        self.lbl_current_title.pack(anchor="w", padx=12, pady=(0, 8))

        # 4. Kotak Log Aktivitas
        log_frame = ctk.CTkFrame(self, corner_radius=10)
        log_frame.pack(fill="both", expand=True, padx=16, pady=6)

        log_lbl = ctk.CTkLabel(log_frame, text="Log Aktivitas Client:", font=ctk.CTkFont(size=12, weight="bold"))
        log_lbl.pack(anchor="w", padx=12, pady=(6, 2))

        self.txt_log = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        # 5. Tombol Sembunyikan ke Tray
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=16, pady=(4, 16))

        btn_minimize = ctk.CTkButton(
            bottom_frame,
            text="📥 Sembunyikan ke System Tray",
            fg_color="#0369a1",
            hover_color="#0284c7",
            command=self._hide_to_tray
        )
        btn_minimize.pack(side="right")

    def _setup_tray(self):
        """Menyiapkan ikon System Tray di Windows taskbar (pojok kanan bawah dekat jam)."""
        image = create_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Buka Aplikasi", self._show_from_tray, default=True),
            pystray.MenuItem("Keluar (Exit)", self._exit_from_tray)
        )
        self.tray_icon = pystray.Icon("RemotePCClient", image, "Remote Web Monitor Client", menu)

        # Jalankan tray di thread terpisah
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _on_minimize_to_tray(self, event=None):
        """Dipicu saat tombol minimize (_) ditekan di pojok kanan atas jendela."""
        if event is not None and event.widget != self:
            return
        if self.state() == "iconic" and not self._is_in_tray:
            self._is_in_tray = True
            # Berikan sedikit jeda sebelum withdraw agar animasi Windows selesai
            self.after(50, self._perform_hide_to_tray)

    def _perform_hide_to_tray(self):
        self.withdraw()
        self._append_log("Aplikasi diminimalkan ke System Tray (Pojok kanan bawah dekat jam).")

    def _hide_to_tray(self):
        """Sembunyikan jendela manual ke System Tray."""
        self._is_in_tray = True
        self.withdraw()
        self._append_log("Aplikasi disembunyikan ke System Tray.")

    def _show_from_tray(self, icon=None, item=None):
        """Memunculkan kembali jendela dari System Tray ke layar."""
        self.after(0, self._restore_window)

    def _restore_window(self):
        self._is_in_tray = False
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()
        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))

    def _exit_from_tray(self, icon=None, item=None):
        """Keluar sepenuhnya dari menu klik kanan System Tray."""
        self.after(0, self._on_exit)

    def _on_exit(self):
        """Tutup normal ketika tombol X ditekan atau menu Keluar dipilih."""
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.engine.stop()
        self.destroy()

    def _apply_server_ip(self):
        ip = self.entry_ip.get().strip()
        port_str = self.entry_port.get().strip()
        if not ip:
            messagebox.showwarning("Peringatan", "Alamat IP server tidak boleh kosong.")
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showwarning("Peringatan", "Port harus berupa angka.")
            return

        self.engine.update_server_target(ip, port)
        messagebox.showinfo("Berhasil", f"Target server diatur ke {ip}:{port}")

    def _toggle_autostart(self):
        if self.switch_autostart.get():
            if enable_autostart():
                self._append_log("Auto-start Windows AKTIF (Otomatis berjalan di System Tray saat PC boot).")
            else:
                self.switch_autostart.deselect()
                messagebox.showerror("Gagal", "Gagal mengaktifkan auto-start di registry Windows.")
        else:
            if disable_autostart():
                self._append_log("Auto-start Windows DINONAKTIFKAN.")
            else:
                self.switch_autostart.select()
                messagebox.showerror("Gagal", "Gagal menonaktifkan auto-start di registry Windows.")

    def _on_connection_change_threadsafe(self, is_online: bool):
        self.after(0, lambda: self._update_connection_badge(is_online))

    def _update_connection_badge(self, is_online: bool):
        if is_online:
            self.lbl_status.configure(text="● Terhubung ke Server", text_color="#10b981")
        else:
            self.lbl_status.configure(text="● Menghubungkan...", text_color="#f59e0b")

    def _on_activity_detected_threadsafe(self, browser: str, title: str, is_blocked: bool):
        self.after(0, lambda: self._update_activity_display(browser, title, is_blocked))

    def _update_activity_display(self, browser: str, title: str, is_blocked: bool):
        b_text = f"Browser Aktif: {browser}"
        if is_blocked:
            b_text += " [AKSI: TAB DITUTUP OTOMATIS]"
            self.lbl_current_browser.configure(text=b_text, text_color="#ef4444")
        else:
            self.lbl_current_browser.configure(text=b_text, text_color="#38bdf8")

        self.lbl_current_title.configure(text=f"Judul / Link: {title[:80]}")

    def _append_log_threadsafe(self, message: str):
        self.after(0, lambda: self._append_log(message))

    def _append_log(self, message: str):
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        entry = f"[{now}] {message}\n"
        self.txt_log.insert("end", entry)
        self.txt_log.see("end")

def run_client_gui():
    args = [a.lower() for a in sys.argv[1:]]
    minimized_flags = {"--minimized", "-minimized", "/minimized", "--tray", "-tray", "--hidden", "-hidden", "-m"}
    start_minimized = any(flag in args for flag in minimized_flags)

    app = ClientApp(start_minimized=start_minimized)
    app.mainloop()

if __name__ == "__main__":
    run_client_gui()
