"""Wizard Pencopotan Aplikasi (Uninstaller) untuk Remote PC Web Monitor (Client & Server)."""
import os
import sys
import shutil
import winreg
import subprocess
import customtkinter as ctk
from tkinter import messagebox

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_UNINSTALL_PATH = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\RemotePCWebMonitor"
APP_CLIENT_NAME = "RemotePCWebMonitorClient"
APP_SERVER_NAME = "RemotePCWebMonitorServer"

def get_install_dir() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    return os.path.join(local_app_data, "RemotePCWebMonitor")

def is_client_installed() -> bool:
    return os.path.exists(os.path.join(get_install_dir(), "ClientAgent.exe"))

def is_server_installed() -> bool:
    return os.path.exists(os.path.join(get_install_dir(), "ServerAdmin.exe"))

def is_autostart_active() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_CLIENT_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass
    return False

def perform_uninstall(remove_config: bool = True) -> tuple[bool, str]:
    """Menjalankan proses pencopotan aplikasi secara menyeluruh."""
    errors = []
    install_dir = get_install_dir()

    # 1. Hentikan proses yang sedang berjalan
    for proc in ["ClientAgent.exe", "ServerAdmin.exe"]:
        try:
            subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True, creationflags=0x08000000)
        except Exception:
            pass

    # 2. Hapus pendaftaran Windows Startup (Run Registry)
    for app_name in [APP_CLIENT_NAME, APP_SERVER_NAME]:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, app_name)
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass
        except Exception as e:
            errors.append(f"Gagal menghapus startup registry: {e}")

    # 3. Hapus pendaftaran Windows Apps & Features (Uninstall Registry)
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_UNINSTALL_PATH)
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # 4. Hapus shortcut Desktop
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    for name in ["Client Agent - Web Monitor.lnk", "Server Admin - Web Monitor.lnk"]:
        sc_path = os.path.join(desktop, name)
        if os.path.exists(sc_path):
            try:
                os.remove(sc_path)
            except Exception as e:
                errors.append(f"Gagal menghapus shortcut desktop: {e}")

    # 5. Hapus shortcut Start Menu
    appdata_roaming = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
    start_menu = os.path.join(appdata_roaming, r"Microsoft\Windows\Start Menu\Programs", "RemotePCWebMonitor")
    if os.path.exists(start_menu):
        try:
            shutil.rmtree(start_menu, ignore_errors=True)
        except Exception as e:
            errors.append(f"Gagal menghapus Start Menu: {e}")

    # 6. Hapus folder instalasi di Local AppData
    if os.path.exists(install_dir):
        # Cek apakah uninstaller dijalankan dari dalam install_dir itu sendiri
        current_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        is_running_from_install_dir = os.path.commonpath([current_exe, install_dir]) == install_dir

        if is_running_from_install_dir:
            # Gunakan self-deleting batch script agar file uninstaller yang sedang berjalan bisa terhapus
            temp_dir = os.environ.get("TEMP", os.path.expanduser("~\\AppData\\Local\\Temp"))
            bat_path = os.path.join(temp_dir, "cleanup_remoteweb.bat")
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(f'''@echo off
timeout /t 1 /nobreak > nul
rd /s /q "{install_dir}" > nul 2>&1
del "%~f0" > nul 2>&1
''')
            subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=0x08000000)
        else:
            try:
                shutil.rmtree(install_dir, ignore_errors=True)
            except Exception as e:
                errors.append(f"Gagal menghapus folder program: {e}")

    if errors:
        return False, "\n".join(errors)
    return True, "Semua komponen aplikasi berhasil dihapus sepenuhnya."

class UninstallerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Uninstaller - Remote PC Web Monitor & Filter")
        self.geometry("520x460")
        self.resizable(False, False)

        self.delete_config_var = ctk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        # 1. Header Banner
        header = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#1e1b4b")
        header.pack(fill="x")
        header.pack_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="🗑️ Pencopotan Aplikasi (Uninstaller)",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#f87171"
        )
        title.pack(anchor="w", padx=24, pady=(16, 2))

        sub_title = ctk.CTkLabel(
            header,
            text="Menghapus Remote PC Web Monitor & Filter dari komputer ini",
            font=ctk.CTkFont(size=12),
            text_color="#cbd5e1"
        )
        sub_title.pack(anchor="w", padx=24)

        # 2. Main Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        # Status Terpasang
        card_status = ctk.CTkFrame(body, corner_radius=8, fg_color="#1e293b")
        card_status.pack(fill="x", pady=(0, 12))

        lbl_status_title = ctk.CTkLabel(
            card_status,
            text="🔍 Komponen Terdeteksi di Komputer Ini:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_status_title.pack(anchor="w", padx=16, pady=(10, 4))

        client_status = "✅ Terpasang" if is_client_installed() else "❌ Tidak terpasang"
        server_status = "✅ Terpasang" if is_server_installed() else "❌ Tidak terpasang"
        autostart_status = "✅ Aktif" if is_autostart_active() else "❌ Tidak aktif"

        lbl_details = ctk.CTkLabel(
            card_status,
            text=f"• PC Client Agent: {client_status}\n• PC Server Admin: {server_status}\n• Windows Startup: {autostart_status}\n• Lokasi: {get_install_dir()}",
            font=ctk.CTkFont(size=12),
            text_color="#cbd5e1",
            justify="left"
        )
        lbl_details.pack(anchor="w", padx=16, pady=(0, 10))

        # Opsi Penghapusan
        card_opts = ctk.CTkFrame(body, corner_radius=8, fg_color="#1e293b")
        card_opts.pack(fill="x", pady=(0, 10))

        lbl_opts_title = ctk.CTkLabel(
            card_opts,
            text="📋 Yang Akan Dihapus:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_opts_title.pack(anchor="w", padx=16, pady=(10, 4))

        lbl_items = ctk.CTkLabel(
            card_opts,
            text="✓ Menghentikan proses aplikasi yang aktif di latar belakang\n✓ Menghapus pendaftaran otomatis saat PC dinyalakan (Registry)\n✓ Menghapus shortcut di Desktop dan Start Menu\n✓ Menghapus seluruh file program di AppData",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        )
        lbl_items.pack(anchor="w", padx=16, pady=(0, 8))

        self.chk_config = ctk.CTkCheckBox(
            card_opts,
            text="Hapus juga file konfigurasi lokal & cache aturan",
            variable=self.delete_config_var,
            font=ctk.CTkFont(size=12)
        )
        self.chk_config.pack(anchor="w", padx=16, pady=(2, 12))

        # 3. Footer Bar
        footer = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#0f172a")
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        btn_cancel = ctk.CTkButton(
            footer,
            text="Batal",
            font=ctk.CTkFont(size=13),
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            width=80,
            command=self.destroy
        )
        btn_cancel.pack(side="left", padx=24, pady=12)

        self.btn_uninstall = ctk.CTkButton(
            footer,
            text="🗑️ Copot Pemasangan Sekarang",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=36,
            command=self._do_uninstall
        )
        self.btn_uninstall.pack(side="right", padx=24, pady=12)

    def _do_uninstall(self):
        if not messagebox.askyesno(
            "Konfirmasi Pencopotan",
            "Apakah Anda yakin ingin mencopot pemasangan Remote PC Web Monitor dari komputer ini?\n\nSemua fitur pemantauan dan blokir akan dihentikan."
        ):
            return

        success, msg = perform_uninstall(remove_config=self.delete_config_var.get())
        if success:
            messagebox.showinfo("Pencopotan Selesai", f"Sukses!\n\n{msg}")
            self.destroy()
        else:
            messagebox.showwarning("Peringatan", f"Sebagian komponen mungkin belum terhapus:\n\n{msg}")
            self.destroy()

def run_uninstaller():
    app = UninstallerApp()
    app.mainloop()

if __name__ == "__main__":
    run_uninstaller()

