"""GUI Server Admin: Pemantau Browser & Filter Web Real-time dengan Kontrol Auto-Update."""
import os
import sys
import shutil
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
from typing import List, Optional, Dict, Any
import customtkinter as ctk
from PIL import Image

from shared.protocol import APP_VERSION
from server.server_core import RemoteServerEngine
from server.storage import load_blocked_domains, save_blocked_domains
from server.github_updater import (
    check_github_update,
    perform_server_update,
    get_server_exe_path
)

try:
    from server.history_db import (
        get_history,
        get_distinct_hostnames,
        export_history_to_csv,
        clear_history
    )
except (ImportError, ModuleNotFoundError):
    from history_db import (
        get_history,
        get_distinct_hostnames,
        export_history_to_csv,
        clear_history
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


class ServerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Server Admin - Live Browser Monitor & Web Filter (LAN / WiFi)")
        self.geometry("1100x740")
        self.minsize(980, 650)

        ico_file = get_asset_path('icon.ico')
        if ico_file and os.path.exists(ico_file):
            try:
                self.iconbitmap(default=ico_file)
            except Exception:
                self.iconbitmap(ico_file)
            except Exception:
                pass

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
        self._start_background_update_check()

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
        ip_info = f"🟢 ws://{local_ip}:{self.engine.port} (v{APP_VERSION})"
        self.lbl_server_info = ctk.CTkLabel(
            header,
            text=ip_info,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#4ade80"
        )
        self.lbl_server_info.pack(side="right", padx=16, pady=12)

        # Tombol Banner Pembaruan GitHub (Tersembunyi sampai ada rilis baru)
        self.latest_release_info: Optional[Dict[str, Any]] = None
        self.btn_update_banner = ctk.CTkButton(
            header,
            text="🚀 Versi Baru Tersedia!",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            height=30,
            command=self._prompt_server_update
        )

        # Tombol Manual Cek Update GitHub
        self.btn_check_update = ctk.CTkButton(
            header,
            text="🔄 Cek Update",
            font=ctk.CTkFont(size=12),
            width=95,
            height=30,
            fg_color="#1e293b",
            hover_color="#334155",
            command=lambda: self._check_github_update_action(silent=False)
        )
        self.btn_check_update.pack(side="right", padx=(0, 10), pady=12)

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
            width=70,
            command=self._add_rule,
            fg_color="#0284c7",
            hover_color="#0369a1"
        )
        btn_add.pack(side="right")

        # Daftar Aturan Scrollable
        self.scroll_rules = ctk.CTkScrollableFrame(left_frame, label_text="Daftar Aturan Aktif")
        self.scroll_rules.pack(fill="both", expand=True, padx=12, pady=8)

        # Tombol Sinkronisasi
        btn_sync = ctk.CTkButton(
            left_frame,
            text="🔄 Terapkan Aturan ke Semua Client",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=36,
            command=self._broadcast_rules_action
        )
        btn_sync.pack(fill="x", padx=12, pady=(0, 12))

        # --- KOLOM KANAN: Multi-Tab (Live Monitoring & Riwayat Aktivitas) ---
        self.right_tabview = ctk.CTkTabview(main_pane, corner_radius=10, command=self._on_tab_changed)
        self.right_tabview.pack(side="right", fill="both", expand=True, padx=(8, 0), pady=0)

        # Tab 1: Live Monitoring
        tab_live = self.right_tabview.add("⚡ Live Monitoring")
        
        # Tab 2: Riwayat Browser (History)
        tab_history = self.right_tabview.add("📜 Riwayat Aktivitas")

        # --- ISI TAB 1: Live Monitoring Komputer Client ---
        right_top = ctk.CTkFrame(tab_live, fg_color="transparent")
        right_top.pack(fill="x", padx=6, pady=(4, 6))

        self.lbl_client_count = ctk.CTkLabel(
            right_top,
            text="💻 PC Client Terpantau: 0 Online",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.lbl_client_count.pack(side="left")

        # Tombol Aksi Massal (Shutdown, Restart, Update)
        self.btn_shutdown_all = ctk.CTkButton(
            right_top,
            text="⚡ Matikan Semua",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=32,
            command=self._mass_shutdown_action
        )
        self.btn_shutdown_all.pack(side="right", padx=(6, 0))

        self.btn_restart_all = ctk.CTkButton(
            right_top,
            text="🔄 Restart Semua",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#ea580c",
            hover_color="#c2410c",
            height=32,
            command=self._mass_restart_action
        )
        self.btn_restart_all.pack(side="right", padx=(6, 0))

        self.btn_update_all = ctk.CTkButton(
            right_top,
            text="🚀 Perbarui Semua Client",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=32,
            command=self._update_all_clients_action
        )
        self.btn_update_all.pack(side="right", padx=(0, 6))

        # Daftar Client Scrollable (Live Cards)
        self.scroll_clients = ctk.CTkScrollableFrame(tab_live, label_text="Aktivitas Browser Real-time")
        self.scroll_clients.pack(fill="both", expand=True, padx=4, pady=4)

        # --- ISI TAB 2: Riwayat Aktivitas (History) ---
        filter_bar = ctk.CTkFrame(tab_history, fg_color="#1e293b", corner_radius=8)
        filter_bar.pack(fill="x", padx=6, pady=(4, 6))

        lbl_f_pc = ctk.CTkLabel(filter_bar, text="PC:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_f_pc.pack(side="left", padx=(10, 4), pady=8)

        self.opt_filter_pc = ctk.CTkOptionMenu(
            filter_bar,
            values=["Semua PC"],
            width=130,
            command=lambda _: self._refresh_history_ui()
        )
        self.opt_filter_pc.pack(side="left", padx=(0, 8), pady=8)

        lbl_f_st = ctk.CTkLabel(filter_bar, text="Status:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_f_st.pack(side="left", padx=(4, 4), pady=8)

        self.opt_filter_status = ctk.CTkOptionMenu(
            filter_bar,
            values=["Semua Aktivitas", "🚨 Hanya yang Diblokir"],
            width=165,
            command=lambda _: self._refresh_history_ui()
        )
        self.opt_filter_status.pack(side="left", padx=(0, 8), pady=8)

        self.entry_search_hist = ctk.CTkEntry(
            filter_bar,
            placeholder_text="Cari judul web atau URL...",
            font=ctk.CTkFont(size=12)
        )
        self.entry_search_hist.pack(side="left", fill="x", expand=True, padx=(4, 6), pady=8)
        self.entry_search_hist.bind("<Return>", lambda e: self._refresh_history_ui())

        btn_search = ctk.CTkButton(
            filter_bar,
            text="🔍 Cari",
            width=65,
            command=self._refresh_history_ui,
            fg_color="#0284c7",
            hover_color="#0369a1"
        )
        btn_search.pack(side="right", padx=(0, 10), pady=8)

        # Daftar Scrollable Riwayat
        self.scroll_history = ctk.CTkScrollableFrame(tab_history, label_text="Catatan Riwayat Browser Terkini")
        self.scroll_history.pack(fill="both", expand=True, padx=4, pady=4)

        # Bilah Aksi Bawah Tab Riwayat
        action_bar = ctk.CTkFrame(tab_history, fg_color="transparent")
        action_bar.pack(fill="x", padx=6, pady=(4, 6))

        self.lbl_history_info = ctk.CTkLabel(
            action_bar,
            text="Menampilkan 0 riwayat",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.lbl_history_info.pack(side="left", padx=6)

        btn_clear_hist = ctk.CTkButton(
            action_bar,
            text="🗑️ Bersihkan",
            width=90,
            height=28,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=self._clear_history_action
        )
        btn_clear_hist.pack(side="right", padx=(6, 0))

        btn_export = ctk.CTkButton(
            action_bar,
            text="📥 Ekspor ke CSV / Excel",
            width=165,
            height=28,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._export_history_action
        )
        btn_export.pack(side="right", padx=6)

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

    def _update_all_clients_action(self):
        if not self.engine.clients:
            messagebox.showinfo("Informasi", "Belum ada PC Client yang terhubung saat ini.")
            return

        exe_path = self.engine.find_client_exe_path()
        if not exe_path or not os.path.exists(exe_path):
            messagebox.showerror(
                "File Tidak Ditemukan",
                "File master 'ClientAgent.exe' tidak ditemukan di folder server.\nPastikan file ada di folder 'dist/ClientAgent.exe'."
            )
            return

        if messagebox.askyesno(
            "Konfirmasi Pembaruan",
            f"Apakah Anda yakin ingin mengirimkan perintah pembaruan fitur (v{APP_VERSION}) ke {len(self.engine.clients)} client yang terhubung?\n\nClient akan otomatis mengunduh file baru dan langsung restart di System Tray."
        ):
            count = self.engine.broadcast_update(APP_VERSION)
            self._append_log(f"🚀 Memulai siaran pembaruan v{APP_VERSION} ke {count} PC Client.")

    def _update_single_client_action(self, client_id: str):
        session = self.engine.clients.get(client_id)
        if not session:
            return

        exe_path = self.engine.find_client_exe_path()
        if not exe_path or not os.path.exists(exe_path):
            messagebox.showerror(
                "File Tidak Ditemukan",
                "File master 'ClientAgent.exe' tidak ditemukan di folder server."
            )
            return

        if messagebox.askyesno(
            "Konfirmasi Pembaruan",
            f"Perbarui client '{session.hostname}' ke versi {APP_VERSION}?"
        ):
            self.engine.update_single_client(client_id, APP_VERSION)
            self._append_log(f"🚀 Mengirim instruksi update v{APP_VERSION} ke {session.hostname}.")

    def _mass_shutdown_action(self):
        """Mematikan SEMUA PC Client yang terhubung dengan konfirmasi aman."""
        if not self.engine.clients:
            messagebox.showinfo("Informasi", "Belum ada PC Client yang terhubung saat ini.")
            return

        count = len(self.engine.clients)
        if messagebox.askyesno(
            "⚠️ Konfirmasi Matikan Semua PC",
            f"PERINGATAN:\nApakah Anda yakin ingin MEMATIKAN ({count}) PC Client yang sedang terhubung?\n\nKomputer client akan otomatis dimatikan dalam 5 detik.",
            icon="warning"
        ):
            sent = self.engine.broadcast_power_command(action="shutdown", delay=5, message="Komputer dimatikan oleh Server Admin.")
            self._append_log(f"⚡ Perintah SHUTDOWN massal dikirim ke {sent} PC Client.")
            messagebox.showinfo("Perintah Terkirim", f"Perintah Shutdown berhasil dikirim ke {sent} PC Client.")

    def _mass_restart_action(self):
        """Me-restart SEMUA PC Client yang terhubung dengan konfirmasi."""
        if not self.engine.clients:
            messagebox.showinfo("Informasi", "Belum ada PC Client yang terhubung saat ini.")
            return

        count = len(self.engine.clients)
        if messagebox.askyesno(
            "🔄 Konfirmasi Restart Semua PC",
            f"Apakah Anda yakin ingin ME-RESTART ({count}) PC Client yang sedang terhubung?\n\nKomputer client akan otomatis di-restart dalam 5 detik.",
            icon="question"
        ):
            sent = self.engine.broadcast_power_command(action="restart", delay=5, message="Komputer direstart oleh Server Admin.")
            self._append_log(f"🔄 Perintah RESTART massal dikirim ke {sent} PC Client.")
            messagebox.showinfo("Perintah Terkirim", f"Perintah Restart berhasil dikirim ke {sent} PC Client.")

    def _single_shutdown_action(self, client_id: str):
        """Mematikan SATU PC Client tertentu dengan konfirmasi aman."""
        session = self.engine.clients.get(client_id)
        if not session:
            messagebox.showwarning("Peringatan", "PC Client tidak ditemukan atau sudah terputus.")
            return

        if messagebox.askyesno(
            "⚠️ Konfirmasi Matikan PC",
            f"Apakah Anda yakin ingin MEMATIKAN komputer ini?\n\nPC: {session.hostname}\nIP: {session.ip}\n\nKomputer akan dimatikan dalam 5 detik.",
            icon="warning"
        ):
            self.engine.send_power_command(client_id, action="shutdown", delay=5, message="Komputer dimatikan oleh Server Admin.")
            self._append_log(f"⚡ Perintah SHUTDOWN dikirim ke PC '{session.hostname}' ({session.ip}).")

    def _single_restart_action(self, client_id: str):
        """Me-restart SATU PC Client tertentu dengan konfirmasi."""
        session = self.engine.clients.get(client_id)
        if not session:
            messagebox.showwarning("Peringatan", "PC Client tidak ditemukan atau sudah terputus.")
            return

        if messagebox.askyesno(
            "🔄 Konfirmasi Restart PC",
            f"Apakah Anda yakin ingin ME-RESTART komputer ini?\n\nPC: {session.hostname}\nIP: {session.ip}\n\nKomputer akan di-restart dalam 5 detik.",
            icon="question"
        ):
            self.engine.send_power_command(client_id, action="restart", delay=5, message="Komputer direstart oleh Server Admin.")
            self._append_log(f"🔄 Perintah RESTART dikirim ke PC '{session.hostname}' ({session.ip}).")

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

            # Baris 1: Hostname & IP & Versi & Status Pelanggaran
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
            ip_badge.pack(side="left", padx=6)

            v_color = "#0369a1" if session.version == APP_VERSION else "#b45309"
            v_badge = ctk.CTkLabel(
                top_bar,
                text=f"v{session.version}",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=v_color,
                text_color="#ffffff",
                corner_radius=4,
                padx=6,
                pady=2
            )
            v_badge.pack(side="left", padx=4)

            if session.update_status:
                upd_badge = ctk.CTkLabel(
                    top_bar,
                    text=f"🔄 {session.update_status}",
                    font=ctk.CTkFont(size=11),
                    text_color="#38bdf8"
                )
                upd_badge.pack(side="left", padx=6)

            if getattr(session, "power_status", ""):
                p_text = session.power_status
                p_color = "#ef4444" if "shutdown" in p_text.lower() else "#ea580c"
                p_icon = "⚡" if "shutdown" in p_text.lower() else "🔄"
                power_badge = ctk.CTkLabel(
                    top_bar,
                    text=f"{p_icon} {p_text}",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color=p_color,
                    text_color="#ffffff",
                    corner_radius=4,
                    padx=6,
                    pady=2
                )
                power_badge.pack(side="left", padx=6)

            # Tombol Update Satuan di sisi kanan
            btn_upd_single = ctk.CTkButton(
                top_bar,
                text="Update",
                width=60,
                height=24,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#0284c7",
                hover_color="#0369a1",
                command=lambda c=cid: self._update_single_client_action(c)
            )
            btn_upd_single.pack(side="right", padx=(8, 0))

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

            # Aksi Browser di sisi kiri
            btn_force_tab = ctk.CTkButton(
                btn_bar,
                text="🛑 Tutup Tab",
                width=100,
                height=26,
                fg_color="#e11d48",
                hover_color="#be123c",
                command=lambda c=cid: self.engine.send_force_close_to_client(c, mode="tab")
            )
            btn_force_tab.pack(side="left", padx=(0, 6))

            btn_force_win = ctk.CTkButton(
                btn_bar,
                text="❌ Tutup Jendela",
                width=110,
                height=26,
                fg_color="#991b1b",
                hover_color="#7f1d1d",
                command=lambda c=cid: self.engine.send_force_close_to_client(c, mode="window")
            )
            btn_force_win.pack(side="left")

            # Aksi Kontrol Daya di sisi kanan
            btn_single_shut = ctk.CTkButton(
                btn_bar,
                text="⚡ Matikan PC",
                width=105,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#dc2626",
                hover_color="#b91c1c",
                command=lambda c=cid: self._single_shutdown_action(c)
            )
            btn_single_shut.pack(side="right", padx=(6, 0))

            btn_single_res = ctk.CTkButton(
                btn_bar,
                text="🔄 Restart PC",
                width=105,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#ea580c",
                hover_color="#c2410c",
                command=lambda c=cid: self._single_restart_action(c)
            )
            btn_single_res.pack(side="right", padx=(6, 0))

    def _on_tab_changed(self):
        """Dipanggil ketika pengguna beralih tab."""
        if self.right_tabview.get() == "📜 Riwayat Aktivitas":
            self._update_hostname_dropdown()
            self._refresh_history_ui()

    def _update_hostname_dropdown(self):
        """Memperbarui daftar opsi dropdown PC berdasarkan data riwayat."""
        current_val = self.opt_filter_pc.get()
        hostnames = get_distinct_hostnames()
        for c in self.engine.clients.values():
            if c.hostname and c.hostname not in hostnames:
                hostnames.append(c.hostname)
        hostnames = sorted(list(set(hostnames)))
        options = ["Semua PC"] + [h for h in hostnames if h]
        self.opt_filter_pc.configure(values=options)
        if current_val in options:
            self.opt_filter_pc.set(current_val)
        else:
            self.opt_filter_pc.set("Semua PC")

    def _refresh_history_ui(self):
        """Memperbarui daftar riwayat di Tab Riwayat."""
        for widget in self.scroll_history.winfo_children():
            widget.destroy()

        selected_pc = self.opt_filter_pc.get()
        selected_cat = self.opt_filter_status.get()
        search_q = self.entry_search_hist.get().strip()

        is_blocked_only = (selected_cat == "🚨 Hanya yang Diblokir")
        records = get_history(
            hostname=selected_pc if selected_pc != "Semua PC" else None,
            is_blocked_only=is_blocked_only,
            search_query=search_q if search_q else None,
            limit=250
        )

        self.lbl_history_info.configure(text=f"Menampilkan {len(records)} riwayat terbaru")

        if not records:
            empty_lbl = ctk.CTkLabel(
                self.scroll_history,
                text="Belum ada riwayat aktivitas yang tercatat sesuai filter.",
                text_color="#94a3b8",
                font=ctk.CTkFont(size=13, slant="italic")
            )
            empty_lbl.pack(pady=40)
            return

        for r in records:
            card = ctk.CTkFrame(self.scroll_history, fg_color="#1e293b", corner_radius=8)
            card.pack(fill="x", pady=3, padx=2)

            # Baris 1: Waktu, Hostname, Browser, Lencana Status
            header_row = ctk.CTkFrame(card, fg_color="transparent")
            header_row.pack(fill="x", padx=10, pady=(6, 2))

            time_lbl = ctk.CTkLabel(
                header_row,
                text=r["timestamp"],
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color="#94a3b8"
            )
            time_lbl.pack(side="left")

            host_badge = ctk.CTkLabel(
                header_row,
                text=f"🖥️ {r['hostname']}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#38bdf8",
                fg_color="#0f172a",
                corner_radius=4,
                padx=6,
                pady=1
            )
            host_badge.pack(side="left", padx=8)

            browser_lbl = ctk.CTkLabel(
                header_row,
                text=f"🌐 {r['browser']}",
                font=ctk.CTkFont(size=11),
                text_color="#cbd5e1"
            )
            browser_lbl.pack(side="left")

            if r["is_blocked"]:
                status_text = f"🚨 DIBLOKIR: {r['matched_rule']}" if r["matched_rule"] else "🚨 DIBLOKIR"
                status_badge = ctk.CTkLabel(
                    header_row,
                    text=status_text,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#fecaca",
                    fg_color="#991b1b",
                    corner_radius=4,
                    padx=8,
                    pady=2
                )
                status_badge.pack(side="right")
            else:
                status_badge = ctk.CTkLabel(
                    header_row,
                    text="✓ Normal",
                    font=ctk.CTkFont(size=11),
                    text_color="#86efac",
                    fg_color="#14532d",
                    corner_radius=4,
                    padx=6,
                    pady=2
                )
                status_badge.pack(side="right")

            # Baris 2: Judul Tab / Halaman
            title_text = r["title"] if r["title"] else "(Tanpa Judul)"
            title_lbl = ctk.CTkLabel(
                card,
                text=title_text,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#ffffff",
                anchor="w",
                justify="left"
            )
            title_lbl.pack(fill="x", padx=10, pady=(0, 2))

            # Baris 3: URL / Link
            if r["url_snippet"]:
                url_lbl = ctk.CTkLabel(
                    card,
                    text=f"🔗 {r['url_snippet']}",
                    font=ctk.CTkFont(size=11),
                    text_color="#67e8f9",
                    anchor="w",
                    justify="left"
                )
                url_lbl.pack(fill="x", padx=10, pady=(0, 6))

    def _export_history_action(self):
        """Mengekspor seluruh riwayat yang sesuai kriteria filter ke file CSV/Excel."""
        selected_pc = self.opt_filter_pc.get()
        selected_cat = self.opt_filter_status.get()
        search_q = self.entry_search_hist.get().strip()

        is_blocked_only = (selected_cat == "🚨 Hanya yang Diblokir")
        from datetime import datetime
        default_filename = f"Riwayat_Browser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Berkas CSV (*.csv)", "*.csv"), ("Semua Berkas (*.*)", "*.*")],
            initialfile=default_filename,
            title="Simpan Laporan Riwayat Aktivitas Browser"
        )
        if not filepath:
            return

        try:
            count = export_history_to_csv(
                filepath,
                hostname=selected_pc if selected_pc != "Semua PC" else None,
                is_blocked_only=is_blocked_only,
                search_query=search_q if search_q else None
            )
            messagebox.showinfo(
                "Ekspor Berhasil",
                f"Sebanyak {count} catatan riwayat aktivitas berhasil diekspor ke:\n{filepath}"
            )
            self._append_log(f"Laporan riwayat ({count} entri) diekspor ke CSV: {os.path.basename(filepath)}")
        except Exception as e:
            messagebox.showerror("Gagal Ekspor", f"Terjadi kesalahan saat mengekspor: {e}")

    def _clear_history_action(self):
        """Membersihkan basis data riwayat browser."""
        if messagebox.askyesno(
            "Konfirmasi Hapus Riwayat",
            "Apakah Anda yakin ingin menghapus seluruh riwayat aktivitas browser yang tersimpan di database?\n\nTindakan ini tidak dapat dibatalkan."
        ):
            count = clear_history()
            self._refresh_history_ui()
            messagebox.showinfo("Riwayat Dibersihkan", f"Database berhasil dibersihkan ({count} catatan dihapus).")
            self._append_log("Seluruh riwayat aktivitas browser di database telah dibersihkan oleh Admin.")

    def _append_log_threadsafe(self, message: str):
        self.after(0, lambda: self._append_log(message))

    def _append_log(self, message: str):
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        entry = f"[{now}] {message}\n"
        self.txt_log.insert("end", entry)
        self.txt_log.see("end")

    def _start_background_update_check(self):
        """Memulai pengecekan update GitHub secara senyap di background thread saat startup."""
        threading.Thread(target=lambda: self._check_github_update_action(silent=True), daemon=True).start()

    def _check_github_update_action(self, silent: bool = False):
        """Memeriksa update rilis di GitHub."""
        if not silent:
            self.btn_check_update.configure(text="⏳ Memeriksa...", state="disabled")

        info = check_github_update()

        def _update_ui():
            if not silent:
                self.btn_check_update.configure(text="🔄 Cek Update", state="normal")

            if info.get("has_update"):
                self.latest_release_info = info
                ver = info.get("latest_version")
                self.btn_update_banner.configure(text=f"🚀 Update v{ver} Tersedia!")
                self.btn_update_banner.pack(side="right", padx=(0, 8), pady=12)
                self._append_log(f"⭐ Versi baru v{ver} tersedia di GitHub Releases!")

                if not silent:
                    self._prompt_server_update()
            else:
                self.btn_update_banner.pack_forget()
                if not silent:
                    err = info.get("error")
                    if err:
                        messagebox.showinfo("Status Update", f"Informasi GitHub:\n{err}")
                    else:
                        self._append_log(f"Pengecekan update selesai ({time.strftime('%H:%M:%S')}): Server sudah menggunakan versi terbaru (v{APP_VERSION}).")
                        messagebox.showinfo(
                            "Versi Terbaru",
                            f"Aplikasi Server sudah menggunakan versi terbaru (v{APP_VERSION})."
                        )

        self.after(0, _update_ui)

    def _prompt_server_update(self):
        """Menampilkan dialog konfirmasi dan catatan rilis update server."""
        if not self.latest_release_info:
            return

        ver = self.latest_release_info.get("latest_version")
        notes = self.latest_release_info.get("release_notes", "").strip()
        asset_url = self.latest_release_info.get("server_asset_url")

        msg = f"Versi baru (v{ver}) telah dirilis di GitHub!\nVersi saat ini: v{APP_VERSION}\n\n"
        if notes:
            msg += f"Catatan Perubahan:\n{notes[:300]}\n\n"

        if not asset_url:
            msg += "File executable belum diunggah di rilis ini. Buka halaman GitHub Release di browser?"
            if messagebox.askyesno("Pembaruan Tersedia", msg):
                import webbrowser
                webbrowser.open(self.latest_release_info.get("html_url", ""))
            return

        msg += "Apakah Anda ingin mengunduh dan memasang pembaruan sekarang?\n(Server akan otomatis me-restart ke versi baru)."
        if messagebox.askyesno("Konfirmasi Pembaruan Server", msg):
            self._start_download_server_update(asset_url, ver)

    def _start_download_server_update(self, download_url: str, version: str):
        """Menampilkan modal progres dan menjalankan unduhan update."""
        modal = ctk.CTkToplevel(self)
        modal.title(f"Memperbarui Server ke v{version}")
        modal.geometry("400x160")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()

        lbl_status = ctk.CTkLabel(modal, text=f"Mengunduh file ServerAdmin.exe (v{version})...", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_status.pack(pady=(20, 10))

        prog_bar = ctk.CTkProgressBar(modal, width=320)
        prog_bar.set(0)
        prog_bar.pack(pady=10)

        lbl_pct = ctk.CTkLabel(modal, text="0%", font=ctk.CTkFont(size=12))
        lbl_pct.pack()

        def _on_status(status: str, percent: int):
            def _ui():
                if status == "downloading":
                    prog_bar.set(percent / 100.0)
                    lbl_pct.configure(text=f"{percent}%")
                elif status == "installing":
                    lbl_status.configure(text="Mengalihkan ke Updater... Jendela aplikasi akan menutup.")
                    prog_bar.set(1.0)
                    lbl_pct.configure(text="100%")
                elif status == "failed":
                    messagebox.showerror("Gagal Update", "Terjadi kesalahan saat mengunduh file update.")
                    modal.destroy()
            self.after(0, _ui)

        def _worker():
            self._append_log(f"Mengunduh pembaruan server v{version} dari GitHub...")
            success = perform_server_update(download_url, _on_status)
            if not success:
                self.after(0, lambda: self._append_log("Gagal memperbarui aplikasi server."))

        threading.Thread(target=_worker, daemon=True).start()

    def destroy(self):
        try:
            self.engine.stop()
        except Exception:
            pass
        super().destroy()
        os._exit(0)

def cleanup_old_runtimes():
    """Membersihkan folder cache _MEI lama di AppData runtime agar hemat ruang disk."""
    try:
        local_app = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
        rt_dir = os.path.join(local_app, "RemotePCWebMonitor", "runtime")
        if not os.path.exists(rt_dir):
            return
        current_mei = os.path.abspath(getattr(sys, "_MEIPASS", ""))
        for item in os.listdir(rt_dir):
            full_path = os.path.abspath(os.path.join(rt_dir, item))
            if item.startswith("_MEI") and os.path.isdir(full_path) and full_path != current_mei:
                try:
                    shutil.rmtree(full_path, ignore_errors=True)
                except Exception:
                    pass
    except Exception:
        pass

def run_server_gui():
    app = ServerApp()
    app.mainloop()

if __name__ == "__main__":
    run_server_gui()
