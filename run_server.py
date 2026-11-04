"""Entry point untuk menjalankan aplikasi Server Admin Remote Web Monitor."""
import os
import sys
import traceback
import tkinter as tk
from tkinter import messagebox

# Tambahkan direktori root proyek ke sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def log_fatal_error(err_msg: str):
    try:
        local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        log_dir = os.path.join(local_app_data, "RemotePCWebMonitor")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "server_crash.log"), "a", encoding="utf-8") as f:
            import datetime
            f.write(f"\n[{datetime.datetime.now()}] FATAL CRASH:\n{err_msg}\n" + "=" * 50 + "\n")
    except Exception:
        pass

if __name__ == "__main__":
    try:
        from server.server_gui import run_server_gui
        run_server_gui()
    except Exception as e:
        err_text = traceback.format_exc()
        log_fatal_error(err_text)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Peringatan Startup Server Admin",
                f"Aplikasi Server Admin mengalami kendala saat dimulai:\n\n{e}\n\nDetail kendala tersimpan di:\n%LOCALAPPDATA%\\RemotePCWebMonitor\\server_crash.log"
            )
        except Exception:
            pass
