import os
import re
import sqlite3
import tempfile

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from app.config import db_path
from app.db import TABLES, connect
from app.deps import Auth, Conn, Owner, call
from app.records import delete_record, get_record, insert_record, list_records, update_record
from app.store_ops import claim_owner, ensure_workspace, mark_seen, next_issue_no, seen

router = APIRouter(prefix="/api/store", tags=["Arayüz"], dependencies=Auth)
_KEY = re.compile(r"^[a-z_]{1,40}$")
_STORE_TABLES = TABLES - {"settings", "notify_log", "ignored_sources"}
_SKIP = {"id", "created_at", "owner_id"}


class KeyIn(BaseModel):
    key: str


class ClaimIn(BaseModel):
    is_admin: bool = False


def _table(name: str) -> str:
    if name not in _STORE_TABLES:
        raise ValueError("Geçersiz tablo.")
    return name


def _fields(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Kayıt boş.")
    cleaned = {}
    for key, value in data.items():
        if key in _SKIP or not _KEY.fullmatch(str(key)):
            continue
        cleaned[key] = value
    if not cleaned:
        raise ValueError("Kayıt boş.")
    return cleaned


@router.post("/claim")
def claim(body: ClaimIn, conn=Conn, owner=Owner):
    def run():
        if owner is None:
            raise ValueError("Hesap gerekli.")
        claim_owner(conn, owner, body.is_admin)
        return {"ok": True}

    return call(run)


@router.post("/workspace")
def workspace(conn=Conn, owner=Owner):
    def run():
        ensure_workspace(conn, owner, str(db_path()))
        return {"ok": True}

    return call(run)


@router.get("/backup")
def backup():
    handle = tempfile.NamedTemporaryFile(prefix="is-merkezi-", suffix=".db", delete=False)
    handle.close()
    dest = sqlite3.connect(handle.name)
    src = connect()
    try:
        src.backup(dest)
    finally:
        dest.close()
        src.close()
    return FileResponse(handle.name, filename="is_merkezi.db", background=BackgroundTask(os.unlink, handle.name))


@router.get("/invoices/source")
def invoice_source(key: str, conn=Conn):
    row = conn.execute("SELECT id FROM invoices WHERE source_key=?", (key,)).fetchone()
    return {"id": int(row["id"]) if row else None}


@router.post("/ignored")
def ignore(body: KeyIn, conn=Conn):
    conn.execute("INSERT OR IGNORE INTO ignored_sources(key) VALUES(?)", (body.key,))
    return {"ok": True}


@router.get("/ignored")
def ignored(key: str, conn=Conn):
    row = conn.execute("SELECT 1 FROM ignored_sources WHERE key=?", (key,)).fetchone()
    return {"ignored": row is not None}


@router.post("/seen")
def remember_seen(body: KeyIn, conn=Conn):
    mark_seen(conn, body.key)
    return {"ok": True}


@router.get("/seen")
def read_seen(key: str, conn=Conn):
    return {"seen": seen(conn, key)}


@router.get("/talepler/number")
def talep_number(number: str, conn=Conn):
    row = conn.execute("SELECT * FROM talepler WHERE number=?", (number,)).fetchone()
    return dict(row) if row else None


@router.get("/projects/{project_id}/offers")
def project_offers(
    project_id: int,
    conn=Conn,
    owner=Owner,
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    return list_records(
        conn, "offers", owner, {"project_id": project_id}, limit=limit, offset=offset,
        order="amount IS NULL, amount, id DESC",
    )


@router.get("/projects/{project_id}/offer-count")
def offer_count(project_id: int, conn=Conn, owner=Owner):
    page = list_records(conn, "offers", owner, {"project_id": project_id}, limit=1)
    return {"n": page["count"]}


@router.get("/projects/{project_id}/next-issue")
def issue_no(project_id: int, conn=Conn, owner=Owner):
    return {"n": next_issue_no(conn, project_id, owner)}


@router.delete("/projects/{project_id}/offers")
def clear_offers(project_id: int, conn=Conn, owner=Owner):
    def run():
        if owner is not None:
            try:
                get_record(conn, "projects", project_id, owner)
            except LookupError:
                return {"deleted": 0}
        offers = list_records(conn, "offers", owner, {"project_id": project_id}, limit=5000)["items"]
        for offer in offers:
            delete_record(conn, "offers", offer["id"], owner)
        return {"deleted": len(offers)}

    return call(run)


@router.get("/{table}")
def list_rows(
    table: str,
    conn=Conn,
    owner=Owner,
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    return call(lambda: list_records(conn, _table(table), owner, limit=limit, offset=offset))


@router.post("/{table}", status_code=201)
def create_row(table: str, body: dict, conn=Conn, owner=Owner):
    return call(lambda: insert_record(conn, _table(table), _fields(body), owner))


@router.get("/{table}/{row_id}")
def read_row(table: str, row_id: int, conn=Conn, owner=Owner):
    return call(lambda: get_record(conn, _table(table), row_id, owner))


@router.patch("/{table}/{row_id}")
def update_row(table: str, row_id: int, body: dict, conn=Conn, owner=Owner):
    return call(lambda: update_record(conn, _table(table), row_id, _fields(body), owner))


@router.delete("/{table}/{row_id}", status_code=204)
def remove_row(table: str, row_id: int, conn=Conn, owner=Owner):
    call(lambda: delete_record(conn, _table(table), row_id, owner))
