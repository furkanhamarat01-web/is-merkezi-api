import os
import sqlite3

from app.config import data_dir, db_path

TABLES = {
    "tasks",
    "invoices",
    "reminders",
    "contacts",
    "transactions",
    "projects",
    "reports",
    "offers",
    "talepler",
    "settings",
    "notify_log",
    "ignored_sources",
}
OWNED = {"invoices", "reminders", "reports", "tasks", "contacts", "transactions", "projects", "offers"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT, assignee TEXT,
  priority TEXT, status TEXT, start_date TEXT, due_date TEXT, repeat TEXT, tag TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS invoices (
  id INTEGER PRIMARY KEY, kind TEXT, party TEXT NOT NULL, invoice_no TEXT,
  description TEXT, amount REAL, invoice_date TEXT, due_date TEXT, status TEXT,
  attachment TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS reminders (
  id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT, remind_date TEXT,
  remind_time TEXT, repeat TEXT, status TEXT, last_notified TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, contact_person TEXT, phone TEXT,
  email TEXT, tax_no TEXT, address TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY, kind TEXT, category TEXT, description TEXT, amount REAL,
  trans_date TEXT, party TEXT, payment_method TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT, start_date TEXT,
  end_date TEXT, status TEXT, budget REAL, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS notify_log (key TEXT PRIMARY KEY, last_on TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS ignored_sources (key TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY, invoice_id INTEGER, title TEXT, invoice_no TEXT,
  amount REAL, reason TEXT, saved_path TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS offers (
  id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL, vendor TEXT NOT NULL,
  title TEXT, amount REAL, offer_date TEXT, file_path TEXT, pros TEXT, cons TEXT,
  notes TEXT, source_text TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS talepler (
  id INTEGER PRIMARY KEY, number TEXT NOT NULL, title TEXT NOT NULL, description TEXT,
  work_code TEXT, source_name TEXT, target_name TEXT, author_name TEXT, author_email TEXT,
  priority TEXT, due_date TEXT, status TEXT, file_name TEXT, notes_json TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

_COLUMNS = {
    "talepler": (
        ("notes_json", "TEXT"),
        ("files_json", "TEXT"),
        ("request_code", "TEXT"),
        ("scope", "TEXT"),
        ("author_id", "INTEGER"),
        ("assignee_id", "INTEGER"),
        ("assignee_name", "TEXT"),
    ),
    "invoices": (
        ("source", "TEXT"),
        ("source_key", "TEXT"),
        ("currency", "TEXT"),
        ("tax_no", "TEXT"),
        ("excel_status", "TEXT"),
        ("file_name", "TEXT"),
        ("report_reason", "TEXT"),
        ("report_files", "TEXT"),
        ("paid_amount", "REAL"),
        ("events_json", "TEXT"),
        ("owner_id", "INTEGER"),
    ),
    "reminders": (("owner_id", "INTEGER"),),
    "reports": (("owner_id", "INTEGER"),),
    "tasks": (
        ("owner_id", "INTEGER"),
        ("waiting_since", "TEXT"),
        ("sla_next", "TEXT"),
        ("note_json", "TEXT"),
        ("project_id", "INTEGER"),
        ("issue_no", "INTEGER"),
        ("issue_type", "TEXT"),
    ),
    "contacts": (
        ("owner_id", "INTEGER"),
        ("record_kind", "TEXT"),
        ("scope", "TEXT"),
        ("extension", "TEXT"),
    ),
    "offers": (
        ("owner_id", "INTEGER"),
        ("source_text", "TEXT"),
        ("url", "TEXT"),
    ),
    "projects": (("owner_id", "INTEGER"), ("proj_key", "TEXT")),
    "transactions": (("owner_id", "INTEGER"), ("docs_json", "TEXT")),
}


_ready: set[str] = set()


def _open() -> sqlite3.Connection:
    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(root, 0o700)
    except OSError:
        pass
    conn = sqlite3.connect(db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_talepler_number ON talepler(number)")
    for table, columns in _COLUMNS.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, declaration in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
    for table in OWNED:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_owner ON {table}(owner_id)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_source ON invoices(source_key) "
        "WHERE source_key IS NOT NULL AND source_key != ''"
    )


def init_db() -> None:
    path = str(db_path().resolve())
    conn = _open()
    try:
        _apply_schema(conn)
        conn.commit()
    finally:
        conn.close()
    try:
        os.chmod(db_path(), 0o600)
    except OSError:
        pass
    _ready.add(path)


def connect() -> sqlite3.Connection:
    path = str(db_path().resolve())
    if path not in _ready:
        init_db()
    return _open()
