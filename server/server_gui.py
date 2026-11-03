"""GUI Server Admin: Pemantau Browser & Filter Web Real-time."""
import os
import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import List

from server.server_core import RemoteServerEngine
from server.storage import load_blocked_domains, save_blocked_domains

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ServerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Server Admin - Live Browser Monitor & Web Filter (LAN / WiFi)")
        self.geometry("1100x740")
        self.minsize(980, 650)

        # Inisialisasi engine server
        self.engine = RemoteServerEngine(port=8765)
        self.engine.on_log = self._append_log_threadsafe
        self.engine.on_clients_changed = self._update_client_list_threadsafe

        # Data aturan blokir
        self.rules: List[str] = load_blocked_domains()
        self.engine.active_rules = self.rules

        # Setup GUI Components
        self._build_ui()

        # Jalankan server
        self.engine.start()

    def _build_ui(self):
        # 1. Header Frame
        header = ctk.CTkFrame(self, corner_radius=10, fg_color="#0f172a")
        header.pack(fill="x", padx=16, pady=(16, 10))

        title_lbl = ctk.CTkLabel(
            header,
            text="🛡️ PC ACTIVITY MONITOR & WEB FILTER - SERVER",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8"
        )
        title_lbl.pack(side="left", padx=16, pady=12)

        local_ip = self.engine.get_local_ip()
        ip_info = f"Alamat Server: ws://{local_ip}:{self.engine.port}"
        self.lbl_server_info = ctk.CTkLabel(
            header,
            text=ip_info,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4ade80"
        )
        self.lbl_server_info.pack(side="right", padx=16, pady=12)

        # 2. Main Content Split: Kiri (Daftar Aturan) & Kanan (Live Monitoring Client)
        main_pane = ctk.CTkFrame(self, fg_color="transparent")
        main_pane.pack(fill="both", expand=True, padx=16, pady=6)

        # --- KOLOM KIRI: Manajemen Kata Kunci & Domain Terlarang ---
        left_frame = ctk.CTkFrame(main_pane, width=380, corner_radius=10)
        left_frame.pack(side="left", fill="both", padx=(0, 8), pady=0)
        left_frame.pack_propagate(False)

        left_title = ctk.CTkLabel(
            left_frame,
            text="🚫 Kata Kunci / Domain Terlarang",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        left_title.pack(padx=12, pady=(12, 4), anchor="w")

        hint_lbl = ctk.CTkLabel(
            left_frame,
            text="Jika judul/link di browser client memuat kata ini,\ntab akan langsung ditutup otomatis oleh sistem.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        )
        hint_lbl.pack(padx=12, pady=(0, 8), anchor="w")

        # Input tambah kata kunci/domain
        input_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        input_frame.pack(fill="x", padx=12, pady=4)

        self.entry_rule = ctk.CTkEntry(
            input_frame,
            placeholder_text="Contoh: youtube, facebook, judi",
            font=ctk.CTkFont(size=13)
        )
        self.entry_rule.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry_rule.bind("<Return>", lambda e: self._add_rule())

        btn_add = ctk.CTkButton(
            input_frame,
            text="Tambah",
            width=75,
            command=self._add_rule,
            fg_color="#0284c7",
            hover_color="#0369a1"
        )
        btn_add.pack(side="right")

        # Scrollable list untuk aturan
        self.scroll_rules = ctk.CTkScrollableFrame(left_frame, label_text="Daftar Aturan Aktif")
        self.scroll_rules.pack(fill="both", expand=True, padx=12, pady=6)

        # Tombol aksi aturan
        left_action_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        left_action_frame.pack(fill="x", padx=12, pady=(4, 12))

        btn_apply_all = ctk.CTkButton(
            left_action_frame,
            text="🚀 Terapkan ke SEMUA Client",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._broadcast_rules_action,
            fg_color="#dc2626",
            hover_color="#b91c1c"
        )
        btn_apply_all.pack(fill="x", pady=2)

        # --- KOLOM KANAN: Live Monitoring Komputer Client ---
        right_frame = ctk.CTkFrame(main_pane, corner_radius=10)
        right_frame.pack(side="right", fill="both", expand=True, padx=(8, 0), pady=0)

        # Header client online
        right_top = ctk.CTkFrame(right_frame, fg_color="transparent")
        right_top.pack(fill="x", padx=12, pady=(12, 6))

        self.lbl_client_count = ctk.CTkLabel(
            right_top,
            text="💻 PC Client Terpantau: 0 Online",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_client_count.pack(side="left")

        # Daftar Client Scrollable (Live Cards)
        self.scroll_clients = ctk.CTkScrollableFrame(right_frame, label_text="Aktivitas Browser Real-time")
        self.scroll_clients.pack(fill="both", expand=True, padx=12, pady=6)

        # 3. Log Box Bawah
        log_frame = ctk.CTkFrame(self, corner_radius=10, height=130)
        log_frame.pack(fill="x", padx=16, pady=(6, 16))
        log_frame.pack_propagate(False)

        log_lbl = ctk.CTkLabel(
            log_frame,
            text="📋 Log Kejadian Real-time",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        log_lbl.pack(padx=12, pady=(6, 2), anchor="w")

        self.txt_log = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # Render daftar aturan awal
        self._refresh_rules_ui()

    def _refresh_rules_ui(self):
        """Memperbarui tampilan daftar aturan di GUI."""
        for widget in self.scroll_rules.winfo_children():
            widget.destroy()

        if not self.rules:
            empty_lbl = ctk.CTkLabel(self.scroll_rules, text="Belum ada aturan yang dibuat.", text_color="#94a3b8")
            empty_lbl.pack(pady=10)
            return

        for rule in self.rules:
            item_frame = ctk.CTkFrame(self.scroll_rules, fg_color="#1e293b", corner_radius=6)
            item_frame.pack(fill="x", pady=2, padx=2)

            d_lbl = ctk.CTkLabel(item_frame, text=f"⛔  {rule}", font=ctk.CTkFont(size=13))
            d_lbl.pack(side="left", padx=8, pady=4)

            btn_del = ctk.CTkButton(
                item_frame,
                text="✕",
                width=28,
                height=24,
                fg_color="#ef4444",
                hover_color="#dc2626",
                command=lambda r=rule: self._remove_rule(r)
            )
            btn_del.pack(side="right", padx=6, pady=4)

    def _add_rule(self):
        rule = self.entry_rule.get().strip().lower()
        if not rule:
            return
        if rule in self.rules:
            messagebox.showinfo("Informasi", f"Aturan '{rule}' sudah ada dalam daftar.")
            return

        self.rules.append(rule)
        self.entry_rule.delete(0, "end")
        self._refresh_rules_ui()
        save_blocked_domains(self.rules)
        self._broadcast_rules_action()
        self._append_log(f"Menambahkan aturan baru: '{rule}' dan menyinkronkan ke client.")

    def _remove_rule(self, rule: str):
        if rule in self.rules:
            self.rules.remove(rule)
            self._refresh_rules_ui()
            save_blocked_domains(self.rules)
            self._broadcast_rules_action()
            self._append_log(f"Menghapus aturan: '{rule}' dan menyinkronkan ke client.")

    def _broadcast_rules_action(self):
        self.engine.broadcast_rules(self.rules)
        self._append_log(f"Aturan berhasil disinkronkan ke {len(self.engine.clients)} PC Client.")

    def _update_client_list_threadsafe(self):
        self.after(0, self._render_clients_ui)

    def _render_clients_ui(self):
        for widget in self.scroll_clients.winfo_children():
            widget.destroy()

        clients = self.engine.clients
        self.lbl_client_count.configure(text=f"💻 PC Client Terpantau: {len(clients)} Online")

        if not clients:
            empty_lbl = ctk.CTkLabel(
                self.scroll_clients,
                text="Menunggu PC Client terhubung dalam jaringan WiFi / LAN...",
                text_color="#94a3b8",
                font=ctk.CTkFont(size=13, slant="italic")
            )
            empty_lbl.pack(pady=30)
            return

        for cid, session in clients.items():
            card = ctk.CTkFrame(self.scroll_clients, fg_color="#1e293b", corner_radius=10)
            card.pack(fill="x", pady=6, padx=4)

            # Baris 1: Hostname & IP & Status Pelanggaran
            top_bar = ctk.CTkFrame(card, fg_color="transparent")
            top_bar.pack(fill="x", padx=12, pady=(8, 2))

            h_lbl = ctk.CTkLabel(
                top_bar,
                text=f"🖥️ {session.hostname}",
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color="#f8fafc"
            )
            h_lbl.pack(side="left")

            ip_badge = ctk.CTkLabel(
                top_bar,
                text=f"IP: {session.ip}",
                font=ctk.CTkFont(size=12),
                fg_color="#334155",
                corner_radius=4,
                padx=6,
                pady=2
            )
            ip_badge.pack(side="left", padx=10)

            viol_text = f"Pelanggaran: {session.violation_count}x"
            viol_color = "#ef4444" if session.violation_count > 0 else "#22c55e"
            viol_badge = ctk.CTkLabel(
                top_bar,
                text=viol_text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=viol_color
            )
            viol_badge.pack(side="right")

            # Baris 2: Aktivitas Browser Saat Ini (LIVE FEED)
            act_box = ctk.CTkFrame(card, fg_color="#0f172a", corner_radius=6)
            act_box.pack(fill="x", padx=12, pady=4)

            browser_info = f"🌐 {session.current_browser}"
            b_lbl = ctk.CTkLabel(
                act_box,
                text=browser_info,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#38bdf8"
            )
            b_lbl.pack(anchor="w", padx=10, pady=(6, 2))

            # Judul tab / URL yang dibuka
            page_title = session.current_title if session.current_title else "Belum membuka browser"
            status_tag = ""
            tag_color = "#e2e8f0"
            if session.is_last_blocked:
                status_tag = f" 🚨 [DITUTUP KARENA COCOK: '{session.last_matched_rule}']"
                tag_color = "#f87171"

            title_display = f"Membuka: {page_title[:75]}{'...' if len(page_title) > 75 else ''}{status_tag}"
            t_lbl = ctk.CTkLabel(
                act_box,
                text=title_display,
                font=ctk.CTkFont(size=12),
                text_color=tag_color,
                anchor="w"
            )
            t_lbl.pack(anchor="w", padx=10, pady=(0, 6))

            # Baris 3: Remote Action
            btn_bar = ctk.CTkFrame(card, fg_color="transparent")
            btn_bar.pack(fill="x", padx=12, pady=(2, 8))

            btn_force_tab = ctk.CTkButton(
                btn_bar,
                text="🛑 Tutup Tab",
                width=120,
                height=26,
                fg_color="#e11d48",
                hover_color="#be123c",
                command=lambda c=cid: self.engine.send_force_close_to_client(c, mode="tab")
            )
            btn_force_tab.pack(side="right", padx=(6, 0))

            btn_force_win = ctk.CTkButton(
                btn_bar,
                text="❌ Tutup Jendela Browser",
                width=160,
                height=26,
                fg_color="#991b1b",
                hover_color="#7f1d1d",
                command=lambda c=cid: self.engine.send_force_close_to_client(c, mode="window")
            )
            btn_force_win.pack(side="right")

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

def run_server_gui():
    app = ServerApp()
    app.mainloop()

if __name__ == "__main__":
    run_server_gui()
