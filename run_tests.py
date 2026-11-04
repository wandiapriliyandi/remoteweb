#!/usr/bin/env python3
"""
Suite Pengujian Otomatis (Automated Test Suite) untuk RemoteWebMonitor.
Dijalankan secara otomatis sebelum kompilasi atau push ke GitHub.
"""
import os
import sys
import unittest
import py_compile
import tempfile
import sqlite3

# Pastikan direktori root masuk sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from shared.protocol import (
    APP_VERSION,
    create_message,
    parse_message,
    is_newer_version,
    TYPE_REGISTER,
    TYPE_URL_ACTIVITY
)
from server.storage import load_blocked_domains, save_blocked_domains, get_config_file
from server.history_db import get_db_path, init_db, add_history_entry, get_history
from client.config import load_client_config, save_client_config
from server.github_updater import check_github_update, get_server_exe_path


class TestSyntax(unittest.TestCase):
    """Memastikan semua file Python dalam proyek bebas dari kesalahan sintaks."""
    def test_all_python_files_compile(self):
        targets = ["client", "server", "shared", "installer"]
        root_scripts = ["run_client.py", "run_server.py", "bump_version.py"]

        files_to_test = []
        for d in targets:
            dp = os.path.join(BASE_DIR, d)
            if os.path.exists(dp):
                for root, _, files in os.walk(dp):
                    for f in files:
                        if f.endswith(".py"):
                            files_to_test.append(os.path.join(root, f))

        for rs in root_scripts:
            rsp = os.path.join(BASE_DIR, rs)
            if os.path.exists(rsp):
                files_to_test.append(rsp)

        self.assertTrue(len(files_to_test) > 5, "Harus menemukan file Python untuk diuji")

        for fpath in files_to_test:
            try:
                py_compile.compile(fpath, doraise=True)
            except py_compile.PyCompileError as e:
                self.fail(f"Kesalahan sintaks pada {fpath}:\n{e}")


class TestProtocol(unittest.TestCase):
    """Pengujian logika protokol komunikasi dan perbandingan versi."""
    def test_semantic_versioning_comparison(self):
        self.assertTrue(is_newer_version("1.2.1", "1.2.0"))
        self.assertTrue(is_newer_version("1.3.0", "1.2.5"))
        self.assertTrue(is_newer_version("2.0.0", "1.9.9"))
        self.assertFalse(is_newer_version("1.2.0", "1.2.1"))
        self.assertFalse(is_newer_version("1.2.0", "1.2.0"))

    def test_message_creation_and_parsing(self):
        msg = create_message(TYPE_REGISTER, {"hostname": "PC-LAB-01", "ip": "192.168.1.50"})
        parsed = parse_message(msg)
        self.assertEqual(parsed["type"], TYPE_REGISTER)
        self.assertEqual(parsed["payload"]["hostname"], "PC-LAB-01")
        self.assertEqual(parsed["payload"]["ip"], "192.168.1.50")

    def test_malformed_message_handling(self):
        bad_msg = "{invalid_json: true"
        parsed = parse_message(bad_msg)
        self.assertEqual(parsed["type"], "UNKNOWN")


class TestStorageAndDatabase(unittest.TestCase):
    """Memastikan izin tulis dan akses database di AppData berjalan lancar."""
    def test_database_path_and_crud(self):
        db_path = get_db_path()
        self.assertTrue("AppData" in db_path or "RemotePCWebMonitor" in db_path)
        init_db()

        # Tambah entri riwayat simulasi
        success = add_history_entry(
            client_id="test_client_001",
            hostname="TEST-PC",
            ip_address="127.0.0.1",
            browser="Google Chrome",
            title="Halaman Pengujian Antigravity",
            url_snippet="https://example.com/test",
            is_blocked=False,
            matched_rule=""
        )
        self.assertTrue(success, "Harus berhasil menyimpan entri riwayat ke SQLite")

        history = get_history(limit=5)
        self.assertTrue(len(history) > 0, "Harus bisa membaca riwayat yang baru disimpan")

    def test_blocked_domains_storage(self):
        cfg_file = get_config_file()
        self.assertTrue("AppData" in cfg_file or "RemotePCWebMonitor" in cfg_file)
        domains = load_blocked_domains()
        self.assertIsInstance(domains, list)
        self.assertTrue(len(domains) > 0)

        # Simpan dan muat kembali
        test_domain = "test-domain-unique-xyz"
        if test_domain not in domains:
            domains.append(test_domain)
        save_blocked_domains(domains)

        reloaded = load_blocked_domains()
        self.assertIn(test_domain, reloaded)

        # Bersihkan test domain
        reloaded.remove(test_domain)
        save_blocked_domains(reloaded)

    def test_client_config_storage(self):
        cfg = load_client_config()
        self.assertIn("client_id", cfg)
        self.assertIn("server_ip", cfg)
        self.assertIn("server_port", cfg)


class TestGitHubUpdaterModule(unittest.TestCase):
    """Pengujian modul update GitHub."""
    def test_check_update_structure(self):
        # Memastikan check_github_update tidak melempar uncaught exception
        res = check_github_update()
        self.assertIn("has_update", res)
        self.assertIn("latest_version", res)
        self.assertIn("current_version", res)
        self.assertEqual(res["current_version"], APP_VERSION)

    def test_get_server_exe_path(self):
        path = get_server_exe_path()
        self.assertTrue(path.endswith(".exe") or "ServerAdmin" in path)


def run_all_tests() -> bool:
    """Menjalankan seluruh suite pengujian dan mengembalikan status keberhasilan."""
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
