"""Entry point untuk menjalankan aplikasi Server Admin Remote Web Monitor."""
import os
import sys

# Tambahkan direktori root proyek ke sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server.server_gui import run_server_gui

if __name__ == "__main__":
    run_server_gui()

