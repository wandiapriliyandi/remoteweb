"""Antarmuka GUI Client Desktop (PC Target)."""
import os
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from client.client_core import ClientEngine
from client.autostart import is_autostart_enabled, enable_autostart, disable_autostart

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ClientApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Client Agent - Remote Web Monitor & Filter")
        self.geometry("640x520")
        self.minsize(560, 460)

        self.engine = ClientEngine()
        self.engine.on_log = self._append_log_threadsafe
        self.engine.on_connection_status = self._on_connection_change_threadsafe
        self.engine.on_activity_detected = self._on_activity_detected_threadsafe

        self._build_ui()

        # Atur agar saat tombol X (Close) diklik, jendela hanya sembunyi dan TETAP AKTIF di background
        self.protocol("WM_DELETE_WINDOW", self._on_close_clicked)

        # Jalankan engine client
        self.engine.start()

    def _build_ui(self):
        # 1. Header
        header = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e293b")
        header.pack(fill="x", padx=16, pady=(16, 10))

        title_lbl = ctk.CTkLabel(
            header,
            text="👁️ WEB MONITOR CLIENT AGENT",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8"
        )
        title_lbl.pack(side="left", padx=16, pady=12)

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

        # Set status switch berdasarkan registry Windows saat ini
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

        # 5. Tombol Sembunyikan ke Background
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=16, pady=(4, 16))

        btn_minimize = ctk.CTkButton(
            bottom_frame,
            text="Sembunyikan Jendela (Jalan di Latar Belakang)",
            fg_color="#475569",
            hover_color="#334155",
            command=self._minimize_to_bg
        )
        btn_minimize.pack(side="right")

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
                self._append_log("Auto-start Windows AKTIF (Akan otomatis berjalan saat PC boot).")
            else:
                self.switch_autostart.deselect()
                messagebox.showerror("Gagal", "Gagal mengaktifkan auto-start di registry Windows.")
        else:
            if disable_autostart():
                self._append_log("Auto-start Windows DINONAKTIFKAN.")
            else:
                self.switch_autostart.select()
                messagebox.showerror("Gagal", "Gagal menonaktifkan auto-start di registry Windows.")

    def _on_close_clicked(self):
        """Ketika tombol X (Close) diklik, sembunyikan jendela agar tetap aktif memantau di background."""
        self.withdraw()
        self._append_log("Jendela ditutup tetapi aplikasi TETAP AKTIF di latar belakang.")

    def _minimize_to_bg(self):
        self.withdraw()  # Sembunyikan jendela dari taskbar
        self._append_log("Aplikasi disembunyikan. Tetap memantau di latar belakang.")

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

    def destroy(self):
        self.engine.stop()
        super().destroy()

def run_client_gui():
    app = ClientApp()
    app.mainloop()

if __name__ == "__main__":
    run_client_gui()

