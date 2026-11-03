"""Entry point untuk menjalankan aplikasi PC Client Agent."""
import os
import sys

# Tambahkan direktori root proyek ke sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from client.client_gui import run_client_gui

if __name__ == "__main__":
    run_client_gui()

