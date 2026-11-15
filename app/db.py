import re
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from app.config import database_url
from app.models import Base

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
_NO_ID = {"settings", "notify_log", "ignored_sources"}
_QMARK = re.compile(r"\?")
_INSERT = re.compile(r"insert\s+into\s+([a-z_]+)", re.IGNORECASE)

_engine: Engine | None = None
_ready = False


class ResultRow(dict):
    def keys(self):
        return list(super().keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class Cursor:
    def __init__(self, result, lastrowid=None):
        self._result = result
        self.lastrowid = lastrowid

    def fetchone(self):
        if self._result is None:
            return None
        row = self._result.mappings().fetchone()
        if row is None:
            return None
        return ResultRow({key: _plain(value) for key, value in row.items()})

    def fetchall(self):
        if self._result is None:
            return []
        return [ResultRow({key: _plain(value) for key, value in row.items()}) for row in self._result.mappings()]


class Connection:
    def __init__(self, raw):
        self.raw = raw
        self.trans = raw.begin()

    def execute(self, sql, params=()):
        statement, binds, returning = _prepare(sql, params)
        result = self.raw.execute(text(statement), binds)
        lastrowid = None
        if returning:
            row = result.mappings().fetchone()
            lastrowid = None if row is None else row.get("id")
            return Cursor(None, lastrowid)
        return Cursor(result)

    def commit(self):
        self.trans.commit()

    def rollback(self):
        if self.trans.is_active:
            self.trans.rollback()

    def close(self):
        self.raw.close()


def _plain(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _prepare(sql, params):
    values = list(params or [])
    binds = {}
    index = 0

    def replace(_match):
        nonlocal index
        if index >= len(values):
            raise ValueError("Parametre sayısı uyuşmuyor.")
        name = f"p{index}"
        binds[name] = values[index]
        index += 1
        return f":{name}"

    statement = _QMARK.sub(replace, str(sql))
    if index != len(values):
        raise ValueError("Parametre sayısı uyuşmuyor.")
    match = _INSERT.search(statement)
    returning = bool(match) and match.group(1) not in _NO_ID and "returning" not in statement.lower()
    if returning:
        statement = statement.rstrip().rstrip(";") + " RETURNING id"
    return statement, binds, returning


def engine() -> Engine:
    global _engine
    if _engine is None:
        url = database_url()
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, **kwargs)
    return _engine


def _ensure_postgres_database() -> None:
    url = make_url(database_url())
    if url.get_backend_name() != "postgresql":
        return
    name = url.database or "stage_vkvdb"
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError("Veritabanı adı geçersiz.")
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        with admin.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin.dispose()


def init_db() -> None:
    global _ready
    if _ready:
        return
    _ensure_postgres_database()
    Base.metadata.create_all(engine())
    _ready = True


def connect() -> Connection:
    init_db()
    return Connection(engine().connect())


__all__ = ["TABLES", "OWNED", "connect", "init_db"]
