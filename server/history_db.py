"""Modul basis data lokal (SQLite) untuk menyimpan dan menelusuri riwayat aktivitas browser PC Client."""
import os
import sys
import sqlite3
import threading
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

_db_lock = threading.Lock()
_last_activity_cache: Dict[str, Tuple[str, str, int, float]] = {}  # client_id -> (browser, title, is_blocked, timestamp)

def get_db_path() -> str:
    """Mendapatkan path penyimpanan database SQLite server_history.db di AppData Local yang aman."""
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
    app_dir = os.path.join(local_app_data, "RemotePCWebMonitor")
    try:
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, "server_history.db")
    except Exception:
        base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "server_history.db")

def init_db():
    """Inisialisasi tabel dan indeks database jika belum ada."""
    with _db_lock:
        try:
            db_path = get_db_path()
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS browser_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        client_id TEXT,
                        hostname TEXT,
                        ip_address TEXT,
                        browser TEXT,
                        title TEXT,
                        url_snippet TEXT,
                        is_blocked INTEGER DEFAULT 0,
                        matched_rule TEXT
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_time ON browser_history(timestamp);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_hostname ON browser_history(hostname);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_hist_blocked ON browser_history(is_blocked);")
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            print(f"[DB] Peringatan: Inisialisasi database ditunda/gagal: {e}")

def add_history_entry(
    client_id: str,
    hostname: str,
    ip_address: str,
    browser: str,
    title: str,
    url_snippet: str = "",
    is_blocked: bool = False,
    matched_rule: str = ""
) -> bool:
    """
    Menyimpan satu entri riwayat aktivitas browser ke database.
    Memiliki proteksi deduplikasi otomatis agar tidak mencatat spam baris yang sama persis berturut-turut.
    """
    if not title and not url_snippet:
        return False

    clean_title = (title or "").strip()
    clean_browser = (browser or "Browser").strip()
    blocked_int = 1 if is_blocked else 0
    now = datetime.now()
    now_epoch = now.timestamp()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # Cek deduplikasi per client: abaikan jika browser, title, dan is_blocked sama persis dalam rentang waktu singkat
    cached = _last_activity_cache.get(client_id)
    if cached:
        last_b, last_t, last_block, last_time = cached
        if last_b == clean_browser and last_t == clean_title and last_block == blocked_int:
            # Jika identik dan selisih kurang dari 10 detik, jangan simpan ganda
            if (now_epoch - last_time) < 10.0:
                return False

    _last_activity_cache[client_id] = (clean_browser, clean_title, blocked_int, now_epoch)

    with _db_lock:
        try:
            conn = sqlite3.connect(get_db_path())
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO browser_history (
                        timestamp, client_id, hostname, ip_address, browser, title, url_snippet, is_blocked, matched_rule
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp_str,
                    client_id,
                    hostname,
                    ip_address,
                    clean_browser,
                    clean_title,
                    url_snippet or "",
                    blocked_int,
                    matched_rule or ""
                ))
                conn.commit()
                return True
            finally:
                conn.close()
        except Exception as e:
            print(f"Error menyimpan riwayat ke database: {e}")
            return False

def get_history(
    hostname: Optional[str] = None,
    is_blocked_only: bool = False,
    search_query: Optional[str] = None,
    limit: int = 500,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Mengambil daftar riwayat aktivitas browser dengan opsi filter dan pencarian."""
    with _db_lock:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return []

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            conditions = []
            params = []

            if hostname and hostname != "Semua PC":
                conditions.append("hostname = ?")
                params.append(hostname)

            if is_blocked_only:
                conditions.append("is_blocked = 1")

            if search_query and search_query.strip():
                q = f"%{search_query.strip().lower()}%"
                conditions.append("(LOWER(title) LIKE ? OR LOWER(url_snippet) LIKE ? OR LOWER(matched_rule) LIKE ?)")
                params.extend([q, q, q])

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT id, timestamp, client_id, hostname, ip_address, browser, title, url_snippet, is_blocked, matched_rule
                FROM browser_history
                {where_clause}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "client_id": r["client_id"],
                    "hostname": r["hostname"],
                    "ip_address": r["ip_address"],
                    "browser": r["browser"],
                    "title": r["title"],
                    "url_snippet": r["url_snippet"],
                    "is_blocked": bool(r["is_blocked"]),
                    "matched_rule": r["matched_rule"]
                })
            return results
        finally:
            conn.close()

def get_distinct_hostnames() -> List[str]:
    """Mengambil daftar semua nama komputer (hostname) yang pernah tercatat di database."""
    with _db_lock:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return []

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT hostname FROM browser_history WHERE hostname IS NOT NULL AND hostname != '' ORDER BY hostname ASC")
            rows = cursor.fetchall()
            return [r[0] for r in rows if r[0]]
        finally:
            conn.close()

def export_history_to_csv(
    filepath: str,
    hostname: Optional[str] = None,
    is_blocked_only: bool = False,
    search_query: Optional[str] = None
) -> int:
    """Mengekspor seluruh riwayat yang sesuai filter ke file format CSV (Excel-compatible)."""
    records = get_history(
        hostname=hostname,
        is_blocked_only=is_blocked_only,
        search_query=search_query,
        limit=100000,
        offset=0
    )

    with open(filepath, "w", newline="", encoding="utf-8-sig") as csvfile:
        fieldnames = ["No", "Waktu", "Nama Komputer (PC)", "IP Address", "Browser", "Judul Tab / Halaman", "URL / Link", "Status", "Aturan Terlanggar"]
        writer = csv.writer(csvfile)
        writer.writerow(fieldnames)

        for idx, item in enumerate(records, 1):
            status = "DIBLOKIR" if item["is_blocked"] else "Normal"
            writer.writerow([
                idx,
                item["timestamp"],
                item["hostname"],
                item["ip_address"],
                item["browser"],
                item["title"],
                item["url_snippet"],
                status,
                item["matched_rule"]
            ])

    return len(records)

def clear_history(days_older_than: Optional[int] = None) -> int:
    """Membersihkan riwayat database (semua atau yang lebih tua dari X hari)."""
    with _db_lock:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return 0

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            if days_older_than is not None and days_older_than > 0:
                cursor.execute("""
                    DELETE FROM browser_history
                    WHERE julianday('now', 'localtime') - julianday(timestamp) > ?
                """, (days_older_than,))
            else:
                cursor.execute("DELETE FROM browser_history;")

            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
        finally:
            conn.close()

# Otomatis inisialisasi tabel saat modul diimpor
init_db()
