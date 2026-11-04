"""Setup Installer Wizard Khusus untuk PC Client (Komputer Target)."""
import os
import sys
import shutil
import json
import uuid
import winreg
import subprocess
import customtkinter as ctk
from tkinter import messagebox

try:
    from uninstall_gui import perform_uninstall
except (ImportError, ModuleNotFoundError):
    try:
        from installer.uninstall_gui import perform_uninstall
    except (ImportError, ModuleNotFoundError):
        import sys
        _cur_dir = os.path.dirname(os.path.abspath(__file__))
        _par_dir = os.path.dirname(_cur_dir)
        for _p in (_cur_dir, _par_dir):
            if _p not in sys.path:
                sys.path.insert(0, _p)
        try:
            from uninstall_gui import perform_uninstall
        except (ImportError, ModuleNotFoundError):
            from installer.uninstall_gui import perform_uninstall

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def get_base_dir():
    """Mendapatkan direktori tempat resource/exe berada."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def create_windows_shortcut(target_exe: str, shortcut_path: str, description: str = ""):
    """Membuat file shortcut .lnk di Windows menggunakan WScript.Shell."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = target_exe
        shortcut.WorkingDirectory = os.path.dirname(target_exe)
        shortcut.Description = description
        shortcut.Save()
        return True
    except Exception:
        ps_cmd = f'$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut("{shortcut_path}"); $Shortcut.TargetPath = "{target_exe}"; $Shortcut.WorkingDirectory = "{os.path.dirname(target_exe)}"; $Shortcut.Description = "{description}"; $Shortcut.Save()'
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, creationflags=0x08000000)
            return True
        except Exception:
            return False

def register_startup(exe_path: str, app_name: str = "RemotePCWebMonitorClient"):
    """Mendaftarkan client ke Windows Startup Registry dengan argumen --minimized."""
    try:
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}" --minimized')
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Gagal mendaftarkan startup: {e}")
        return False

def register_uninstall_entry(install_dir: str, app_title: str = "Remote PC Web Monitor Client"):
    """Mendaftarkan aplikasi ke Windows Settings > Installed Apps (Control Panel)."""
    try:
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\RemotePCWebMonitor"
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
        uninstall_exe = os.path.join(install_dir, "Uninstall.exe")
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, app_title)
        try:
            from shared.protocol import APP_VERSION
        except Exception:
            APP_VERSION = "1.1.0"
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "RemotePCWebMonitor")
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstall_exe}"')
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Gagal mendaftarkan uninstaller ke Windows: {e}")

class ClientInstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Setup Wizard - PC Client Agent")
        self.geometry("540x510")
        self.resizable(False, False)

        self.auto_start_var = ctk.BooleanVar(value=True)
        self.create_desktop_var = ctk.BooleanVar(value=False)

        local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        self.install_dir = os.path.join(local_app_data, "RemotePCWebMonitor")
        self.is_already_installed = os.path.exists(os.path.join(self.install_dir, "ClientAgent.exe"))

        self._build_ui()

    def _build_ui(self):
        # 1. Header Banner
        header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#0f172a")
        header.pack(fill="x")
        header.pack_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="🛡️ Pasang Client Agent (PC Target)",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8"
        )
        title.pack(anchor="w", padx=24, pady=(16, 2))

        sub_title = ctk.CTkLabel(
            header,
            text="Aplikasi pemantau & filter browser otomatis di latar belakang",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        sub_title.pack(anchor="w", padx=24)

        # 2. Main Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=14)

        # Card Pengaturan Server
        card_server = ctk.CTkFrame(body, corner_radius=8, fg_color="#1e293b")
        card_server.pack(fill="x", pady=(0, 10))

        lbl_server_title = ctk.CTkLabel(
            card_server,
            text="📡 Alamat Server Admin:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_server_title.pack(anchor="w", padx=16, pady=(10, 4))

        row_srv = ctk.CTkFrame(card_server, fg_color="transparent")
        row_srv.pack(fill="x", padx=16, pady=(0, 10))

        lbl_ip = ctk.CTkLabel(row_srv, text="IP Server:", font=ctk.CTkFont(size=12))
        lbl_ip.pack(side="left", padx=(0, 6))

        self.entry_ip = ctk.CTkEntry(row_srv, width=170, font=ctk.CTkFont(size=12), placeholder_text="192.168.1.100")
        
        # Load IP yang sudah ada jika pernah dipasang
        default_ip = "127.0.0.1"
        default_port = 8765
        cfg_path = os.path.join(self.install_dir, "client_config.json")
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    c = json.load(f)
                    default_ip = c.get("server_ip", default_ip)
                    default_port = c.get("server_port", default_port)
            except Exception:
                pass

        self.entry_ip.insert(0, default_ip)
        self.entry_ip.pack(side="left", padx=(0, 12))

        lbl_port = ctk.CTkLabel(row_srv, text="Port:", font=ctk.CTkFont(size=12))
        lbl_port.pack(side="left", padx=(0, 6))

        self.entry_port = ctk.CTkEntry(row_srv, width=70, font=ctk.CTkFont(size=12))
        self.entry_port.insert(0, str(default_port))
        self.entry_port.pack(side="left")

        # Card Opsi Instalasi
        card_opt = ctk.CTkFrame(body, corner_radius=8, fg_color="#1e293b")
        card_opt.pack(fill="x", pady=(0, 10))

        lbl_opt_title = ctk.CTkLabel(
            card_opt,
            text="⚙️ Opsi Pemasangan:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_opt_title.pack(anchor="w", padx=16, pady=(10, 4))

        self.chk_autostart = ctk.CTkCheckBox(
            card_opt,
            text="Jalankan otomatis saat PC dinyalakan (Run on Windows Startup)",
            variable=self.auto_start_var,
            font=ctk.CTkFont(size=12)
        )
        self.chk_autostart.pack(anchor="w", padx=16, pady=(2, 2))

        lbl_hint_autostart = ctk.CTkLabel(
            card_opt,
            text="   ↳ Langsung aktif di System Tray tanpa membuka jendela di layar.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        )
        lbl_hint_autostart.pack(anchor="w", padx=16, pady=(0, 6))

        self.chk_desktop = ctk.CTkCheckBox(
            card_opt,
            text="Buat shortcut di Layar Desktop",
            variable=self.create_desktop_var,
            font=ctk.CTkFont(size=12)
        )
        self.chk_desktop.pack(anchor="w", padx=16, pady=(2, 10))

        # Info Box
        card_info = ctk.CTkFrame(body, corner_radius=8, fg_color="#111827")
        card_info.pack(fill="x")

        status_text = "💡 Informasi:\n• Client akan dipasang di AppData pengguna (tanpa perlu hak Admin/UAC).\n• Bekerja secara senyap di latar belakang dan menutup tab web terlarang."
        if self.is_already_installed:
            status_text += "\n• Status: Aplikasi saat ini SUDAH TERPASANG di komputer ini."

        lbl_info = ctk.CTkLabel(
            card_info,
            text=status_text,
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8" if not self.is_already_installed else "#38bdf8",
            justify="left"
        )
        lbl_info.pack(anchor="w", padx=14, pady=10)

        # 3. Footer Bar
        footer = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#0f172a")
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        if self.is_already_installed:
            btn_uninstall = ctk.CTkButton(
                footer,
                text="🗑️ Copot (Uninstall)",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#dc2626",
                hover_color="#b91c1c",
                height=36,
                command=self._do_uninstall_flow
            )
            btn_uninstall.pack(side="left", padx=24, pady=12)

        install_btn_text = "Pasang Ulang / Perbarui  ▶" if self.is_already_installed else "Pasang Sekarang (Install Client)  ▶"
        self.btn_install = ctk.CTkButton(
            footer,
            text=install_btn_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=36,
            command=self._do_install
        )
        self.btn_install.pack(side="right", padx=24, pady=12)

    def _do_uninstall_flow(self):
        if messagebox.askyesno(
            "Konfirmasi Pencopotan",
            "Apakah Anda yakin ingin mencopot pemasangan Client Agent dari komputer ini?\n\nAplikasi dan seluruh pengaturannya akan dihapus."
        ):
            success, msg = perform_uninstall(remove_config=True)
            if success:
                messagebox.showinfo("Pencopotan Berhasil", "Client Agent telah berhasil dicopot dari komputer ini.")
                self.destroy()
            else:
                messagebox.showwarning("Peringatan", f"Sebagian komponen mungkin belum terhapus:\n{msg}")

    def _do_install(self):
        server_ip = self.entry_ip.get().strip()
        server_port_str = self.entry_port.get().strip()

        if not server_ip:
            messagebox.showwarning("Peringatan", "Alamat IP server tidak boleh kosong.")
            return

        try:
            server_port = int(server_port_str)
        except ValueError:
            messagebox.showwarning("Peringatan", "Port server harus berupa angka.")
            return

        app_name = "ClientAgent.exe"
        shortcut_title = "Client Agent - Web Monitor"

        install_dir = self.install_dir
        os.makedirs(install_dir, exist_ok=True)

        target_exe = os.path.join(install_dir, app_name)

        # Cari file master ClientAgent.exe
        base_dir = get_base_dir()
        possible_src = [
            os.path.join(base_dir, app_name),
            os.path.join(base_dir, "dist", app_name),
            os.path.join(os.path.dirname(base_dir), "dist", app_name)
        ]
        src_exe = None
        for p in possible_src:
            if os.path.exists(p):
                src_exe = p
                break

        if not src_exe:
            messagebox.showerror("Eror", f"File '{app_name}' tidak ditemukan.\nPastikan file master instalasi lengkap.")
            return

        try:
            # 1. Salin file exe ke folder instalasi
            shutil.copy2(src_exe, target_exe)

            # 2. Salin Uninstall.exe jika ada
            possible_uninst = [
                os.path.join(base_dir, "Uninstall.exe"),
                os.path.join(base_dir, "dist", "Uninstall.exe"),
                os.path.join(os.path.dirname(base_dir), "dist", "Uninstall.exe")
            ]
            uninst_target = os.path.join(install_dir, "Uninstall.exe")
            for up in possible_uninst:
                if os.path.exists(up):
                    try:
                        shutil.copy2(up, uninst_target)
                    except Exception:
                        pass
                    break

            # 3. Simpan konfigurasi IP server yang dimasukkan
            config_path = os.path.join(install_dir, "client_config.json")
            cfg = {
                "client_id": str(uuid.uuid4())[:12],
                "server_ip": server_ip,
                "server_port": server_port,
                "auto_minimize": True,
                "cached_rules": [
                    "youtube",
                    "facebook",
                    "instagram",
                    "tiktok",
                    "twitter",
                    "roblox",
                    "judi",
                    "slot"
                ]
            }
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        old_cfg = json.load(f)
                        if "client_id" in old_cfg:
                            cfg["client_id"] = old_cfg["client_id"]
                        if "cached_rules" in old_cfg:
                            cfg["cached_rules"] = old_cfg["cached_rules"]
                except Exception:
                    pass

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)

            # 4. Buat shortcut Start Menu
            appdata_roaming = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
            start_menu_programs = os.path.join(appdata_roaming, r"Microsoft\Windows\Start Menu\Programs", "RemotePCWebMonitor")
            os.makedirs(start_menu_programs, exist_ok=True)
            start_shortcut = os.path.join(start_menu_programs, f"{shortcut_title}.lnk")
            create_windows_shortcut(target_exe, start_shortcut, description=shortcut_title)

            # Shortcut uninstaller di Start Menu
            if os.path.exists(uninst_target):
                uninst_sc = os.path.join(start_menu_programs, "Copot Pemasangan (Uninstall).lnk")
                create_windows_shortcut(uninst_target, uninst_sc, description="Copot Pemasangan Client")
                register_uninstall_entry(install_dir, "Remote PC Web Monitor Client")

            # 5. Buat shortcut desktop jika dipilih
            if self.create_desktop_var.get():
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                shortcut_path = os.path.join(desktop, f"{shortcut_title}.lnk")
                create_windows_shortcut(target_exe, shortcut_path, description=shortcut_title)

            # 6. Daftarkan auto-start Windows jika dipilih
            if self.auto_start_var.get():
                register_startup(target_exe)

            # 7. Tampilkan pesan berhasil
            success_msg = f"Instalasi Client Agent Berhasil!\n\nTarget Server: {server_ip}:{server_port}\nLokasi: {target_exe}"
            if self.auto_start_var.get():
                success_msg += "\nAuto-Start: AKTIF (di System Tray saat PC dinyalakan)"

            if messagebox.askyesno("Instalasi Selesai", f"{success_msg}\n\nApakah Anda ingin langsung menjalankan aplikasi sekarang di latar belakang (System Tray)?"):
                subprocess.Popen([target_exe, "--minimized"], cwd=install_dir)

            self.destroy()

        except Exception as e:
            messagebox.showerror("Gagal Memasang", f"Terjadi kesalahan saat instalasi:\n{e}")

def run_client_installer():
    app = ClientInstallerApp()
    app.mainloop()

if __name__ == "__main__":
    run_client_installer()
