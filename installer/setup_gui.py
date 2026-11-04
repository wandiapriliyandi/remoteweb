"""Setup Installer Wizard untuk Remote PC Web Monitor & Filter (Server & Client)."""
import os
import sys
import shutil
import winreg
import customtkinter as ctk
from PIL import Image
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

def get_installer_asset_path(filename: str) -> str:
    """Mendapatkan path aset icon untuk installer."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, "assets", filename)
        if os.path.exists(p):
            return p
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    par_dir = os.path.dirname(cur_dir)
    for base in (cur_dir, par_dir):
        p = os.path.join(base, "assets", filename)
        if os.path.exists(p):
            return p
    return ""


def get_base_dir():
    """Mendapatkan direktori tempat resource/exe berada."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def kill_process_by_name(exe_names):
    """Menutup proses lama secara paksa agar file tidak terkunci saat ditimpa."""
    if isinstance(exe_names, str):
        exe_names = [exe_names]
    for name in exe_names:
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", name, "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000
            )
        except Exception:
            pass

def safe_copy_file(src: str, dest: str, related_processes=None, retries: int = 5, delay: float = 0.8) -> bool:
    """
    Menyalin file dengan aman ke target.
    Jika target terkunci oleh proses yang berjalan, tutup proses tersebut,
    coba teknik rename fallback, dan lakukan retry loop.
    """
    if not os.path.exists(src):
        return False

    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)

    if related_processes:
        kill_process_by_name(related_processes)
        time.sleep(0.5)

    for attempt in range(retries):
        try:
            shutil.copy2(src, dest)
            return True
        except PermissionError:
            if related_processes:
                kill_process_by_name(related_processes)
            time.sleep(delay)
            try:
                old_temp = dest + f".old_{int(time.time())}"
                if os.path.exists(dest):
                    os.rename(dest, old_temp)
                    shutil.copy2(src, dest)
                    try:
                        os.remove(old_temp)
                    except Exception:
                        pass
                    return True
            except Exception:
                pass
        except Exception:
            time.sleep(delay)

    shutil.copy2(src, dest)
    return True

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
        # Fallback via PowerShell
        import subprocess
        ps_cmd = f'$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut("{shortcut_path}"); $Shortcut.TargetPath = "{target_exe}"; $Shortcut.WorkingDirectory = "{os.path.dirname(target_exe)}"; $Shortcut.Description = "{description}"; $Shortcut.Save()'
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True, creationflags=0x08000000)
            return True
        except Exception:
            return False

def register_startup(exe_path: str, app_name: str = "RemotePCWebMonitorClient"):
    """Mendaftarkan client ke Windows Startup Registry."""
    try:
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}" --minimized')
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Gagal mendaftarkan startup: {e}")
        return False

def register_uninstall_entry(install_dir: str, app_title: str = "Remote PC Web Monitor"):
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

class InstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Setup Wizard - Remote PC Web Monitor & Filter")
        self.geometry("580x480")
        self.resizable(False, False)

        ico_file = get_installer_asset_path('icon.ico')
        if ico_file and os.path.exists(ico_file):
            try:
                self.iconbitmap(default=ico_file)
            except Exception:
                self.iconbitmap(ico_file)
            except Exception:
                pass

        self.install_role = ctk.StringVar(value="client")
        self.auto_start_var = ctk.BooleanVar(value=True)
        self.create_desktop_var = ctk.BooleanVar(value=True)

        local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        self.install_dir = os.path.join(local_app_data, "RemotePCWebMonitor")
        self.is_already_installed = os.path.exists(os.path.join(self.install_dir, "ClientAgent.exe")) or os.path.exists(os.path.join(self.install_dir, "ServerAdmin.exe"))

        self._build_ui()

    def _build_ui(self):
        # 1. Header Banner
        header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#0f172a")
        header.pack(fill="x")
        header.pack_propagate(False)

        banner_box = ctk.CTkFrame(header, fg_color="transparent")
        banner_box.pack(anchor="w", padx=24, pady=(12, 2))

        logo_file = get_installer_asset_path("logo.png")
        if logo_file and os.path.exists(logo_file):
            try:
                pil_logo = Image.open(logo_file).convert("RGBA")
                self.header_logo = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(46, 46))
                lbl_icon = ctk.CTkLabel(banner_box, image=self.header_logo, text="")
                lbl_icon.pack(side="left", padx=(0, 12))
            except Exception:
                pass

        text_col = ctk.CTkFrame(banner_box, fg_color="transparent")
        text_col.pack(side="left")

        title = ctk.CTkLabel(
            text_col,
            text="Panduan Instalasi Aplikasi",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8"
        )
        title.pack(anchor="w")

        sub_title = ctk.CTkLabel(
            header,
            text="Pilih jenis instalasi untuk komputer ini (Server Admin atau Client Target)",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        sub_title.pack(anchor="w", padx=24)

        # 2. Main Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        lbl_choice = ctk.CTkLabel(
            body,
            text="Komputer ini akan difungsikan sebagai:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_choice.pack(anchor="w", pady=(0, 8))

        # Pilihan 1: Client
        card_client = ctk.CTkFrame(body, corner_radius=8, fg_color="#1e293b")
        card_client.pack(fill="x", pady=6)

        rb_client = ctk.CTkRadioButton(
            card_client,
            text="PC Client (Komputer Target yang Diawasi)",
            variable=self.install_role,
            value="client",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_role_change
        )
        rb_client.pack(anchor="w", padx=16, pady=(10, 2))

        lbl_desc_client = ctk.CTkLabel(
            card_client,
            text="Memantau browser, otomatis menutup tab web terlarang, dan jalan otomatis saat PC dinyalakan.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        )
        lbl_desc_client.pack(anchor="w", padx=42, pady=(0, 10))

        # Pilihan 2: Server
        card_server = ctk.CTkFrame(body, corner_radius=8, fg_color="#1e293b")
        card_server.pack(fill="x", pady=6)

        rb_server = ctk.CTkRadioButton(
            card_server,
            text="PC Server (Komputer Admin Pemantau)",
            variable=self.install_role,
            value="server",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_role_change
        )
        rb_server.pack(anchor="w", padx=16, pady=(10, 2))

        lbl_desc_server = ctk.CTkLabel(
            card_server,
            text="Dashboard untuk melihat apa yang sedang dibuka oleh PC client dan mengatur daftar blokir.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        )
        lbl_desc_server.pack(anchor="w", padx=42, pady=(0, 10))

        # Opsi Tambahan
        lbl_opt = ctk.CTkLabel(body, text="Opsi Tambahan:", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_opt.pack(anchor="w", pady=(12, 4))

        self.chk_desktop = ctk.CTkCheckBox(
            body,
            text="Buat Shortcut di Layar Desktop",
            variable=self.create_desktop_var,
            font=ctk.CTkFont(size=12)
        )
        self.chk_desktop.pack(anchor="w", padx=8, pady=2)

        self.chk_autostart = ctk.CTkCheckBox(
            body,
            text="Jalankan otomatis saat komputer dinyalakan (Windows Startup)",
            variable=self.auto_start_var,
            font=ctk.CTkFont(size=12)
        )
        self.chk_autostart.pack(anchor="w", padx=8, pady=2)

        # 3. Footer Bar
        footer = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#0f172a")
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        if self.is_already_installed:
            btn_uninst = ctk.CTkButton(
                footer,
                text="🗑️ Copot (Uninstall)",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#dc2626",
                hover_color="#b91c1c",
                height=36,
                command=self._do_uninstall_flow
            )
            btn_uninst.pack(side="left", padx=24, pady=12)

        install_text = "Pasang Ulang / Perbarui  ▶" if self.is_already_installed else "Pasang Sekarang (Install)  ▶"
        self.btn_install = ctk.CTkButton(
            footer,
            text=install_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=36,
            command=self._do_install
        )
        self.btn_install.pack(side="right", padx=24, pady=12)

    def _on_role_change(self):
        if self.install_role.get() == "server":
            self.chk_autostart.deselect()
            self.chk_autostart.configure(state="disabled")
        else:
            self.chk_autostart.configure(state="normal")
            self.chk_autostart.select()

    def _do_uninstall_flow(self):
        if messagebox.askyesno(
            "Konfirmasi Pencopotan",
            "Apakah Anda yakin ingin mencopot pemasangan aplikasi dari komputer ini?"
        ):
            success, msg = perform_uninstall(remove_config=True)
            if success:
                messagebox.showinfo("Berhasil", "Aplikasi berhasil dicopot.")
                self.destroy()
            else:
                messagebox.showwarning("Peringatan", f"Sebagian komponen belum terhapus:\n{msg}")

    def _do_install(self):
        role = self.install_role.get()
        is_client = (role == "client")
        app_name = "ClientAgent.exe" if is_client else "ServerAdmin.exe"
        shortcut_title = "Client Agent - Web Monitor" if is_client else "Server Admin - Web Monitor"

        install_dir = self.install_dir
        os.makedirs(install_dir, exist_ok=True)

        target_exe = os.path.join(install_dir, app_name)

        # Cari file sumber exe
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
            # Tutup proses lama & salin file ke folder instalasi
            safe_copy_file(src_exe, target_exe, related_processes=["ServerAdmin.exe", "ClientAgent.exe", app_name])

            # Salin Updater.exe jika tersedia
            possible_updater = [
                os.path.join(base_dir, "assets", "Updater.exe"),
                os.path.join(base_dir, "Updater.exe"),
                os.path.join(os.path.dirname(base_dir), "assets", "Updater.exe"),
                os.path.join(os.path.dirname(base_dir), "dist", "assets", "Updater.exe")
            ]
            updater_target = os.path.join(install_dir, "Updater.exe")
            for up in possible_updater:
                if os.path.exists(up):
                    try:
                        safe_copy_file(up, updater_target, related_processes=["Updater.exe"])
                    except Exception:
                        pass
                    break

            # Salin Uninstall.exe jika tersedia
            possible_uninst = [
                os.path.join(base_dir, "Uninstall.exe"),
                os.path.join(base_dir, "dist", "Uninstall.exe"),
                os.path.join(os.path.dirname(base_dir), "dist", "Uninstall.exe")
            ]
            uninst_target = os.path.join(install_dir, "Uninstall.exe")
            for up in possible_uninst:
                if os.path.exists(up):
                    try:
                        safe_copy_file(up, uninst_target, related_processes=["Uninstall.exe"])
                    except Exception:
                        pass
                    break

            # Buat shortcut Start Menu
            appdata_roaming = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
            start_menu_programs = os.path.join(appdata_roaming, r"Microsoft\Windows\Start Menu\Programs", "RemotePCWebMonitor")
            os.makedirs(start_menu_programs, exist_ok=True)
            start_shortcut = os.path.join(start_menu_programs, f"{shortcut_title}.lnk")
            create_windows_shortcut(target_exe, start_shortcut, description=shortcut_title)

            # Buat shortcut uninstaller di Start Menu
            if os.path.exists(uninst_target):
                uninst_sc = os.path.join(start_menu_programs, "Copot Pemasangan (Uninstall).lnk")
                create_windows_shortcut(uninst_target, uninst_sc, description="Copot Pemasangan")
                register_uninstall_entry(install_dir, f"Remote PC Web Monitor ({shortcut_title})")

            # Buat shortcut desktop jika dipilih
            if self.create_desktop_var.get():
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                shortcut_path = os.path.join(desktop, f"{shortcut_title}.lnk")
                create_windows_shortcut(target_exe, shortcut_path, description=shortcut_title)

            # Aktifkan startup jika dipilih
            if is_client and self.auto_start_var.get():
                register_startup(target_exe)

            # Selesai
            success_msg = f"Instalasi Berhasil!\n\nAplikasi telah dipasang di:\n{target_exe}\n\nShortcut telah dibuat di Desktop dan Start Menu."
            if is_client and self.auto_start_var.get():
                success_msg += "\n\nOtomatis berjalan saat PC dinyalakan: AKTIF (di System Tray)."

            if messagebox.askyesno("Instalasi Selesai", f"{success_msg}\n\nApakah Anda ingin langsung menjalankan aplikasi sekarang?"):
                import subprocess
                subprocess.Popen([target_exe], cwd=install_dir)

            self.destroy()

        except Exception as e:
            messagebox.showerror("Gagal Memasang", f"Terjadi kesalahan saat instalasi:\n{e}")

def run_installer():
    app = InstallerApp()
    app.mainloop()

if __name__ == "__main__":
    run_installer()
