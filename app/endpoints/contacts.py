from fastapi import APIRouter, Query

from app.deps import Auth, Conn, Owner, call
from app.records import delete_record, get_record, list_records
from app.schemas import ContactIn, ContactPatch, dumped
from app.services import save_contact

router = APIRouter(prefix="/api/contacts", tags=["Rehber"], dependencies=Auth)


@router.get("")
def list_contacts(
    conn=Conn,
    owner=Owner,
    record_kind: str | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    equals = {"record_kind": record_kind} if record_kind else None
    return call(lambda: list_records(conn, "contacts", owner, equals, q, limit, offset, "name COLLATE NOCASE"))


@router.get("/{row_id}")
def read_contact(row_id: int, conn=Conn, owner=Owner):
    return call(lambda: get_record(conn, "contacts", row_id, owner))


@router.post("", status_code=201)
def create_contact(body: ContactIn, conn=Conn, owner=Owner):
    return call(lambda: save_contact(conn, dumped(body), owner))


@router.patch("/{row_id}")
def update_contact(row_id: int, body: ContactPatch, conn=Conn, owner=Owner):
    return call(lambda: save_contact(conn, dumped(body), owner, row_id))


@router.delete("/{row_id}", status_code=204)
def remove_contact(row_id: int, conn=Conn, owner=Owner):
    call(lambda: delete_record(conn, "contacts", row_id, owner))
