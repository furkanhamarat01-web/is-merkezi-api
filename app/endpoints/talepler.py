from fastapi import APIRouter, Query

from app.deps import Auth, Conn, call
from app.records import delete_record, get_record, list_records
from app.schemas import AssignIn, StatusIn, TakeIn, TalepIn, TalepPatch, dumped
from app.services import assign_talep, save_talep, set_talep_status, take_talep

router = APIRouter(prefix="/api/talepler", tags=["Talepler"], dependencies=Auth)


@router.get("")
def list_talepler(
    conn=Conn,
    status: str | None = None,
    target_name: str | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    equals = {}
    if status:
        equals["status"] = status
    if target_name:
        equals["target_name"] = target_name
    return call(lambda: list_records(conn, "talepler", None, equals, q, limit, offset))


@router.get("/{row_id}")
def read_talep(row_id: int, conn=Conn):
    return call(lambda: get_record(conn, "talepler", row_id))


@router.post("", status_code=201)
def create_talep(body: TalepIn, conn=Conn):
    return call(lambda: save_talep(conn, dumped(body)))


@router.patch("/{row_id}")
def update_talep(row_id: int, body: TalepPatch, conn=Conn):
    return call(lambda: save_talep(conn, dumped(body), row_id))


@router.post("/{row_id}/take")
def take(row_id: int, body: TakeIn, conn=Conn):
    return call(lambda: take_talep(conn, row_id, body.actor_id, body.actor_name))


@router.post("/{row_id}/assign")
def assign(row_id: int, body: AssignIn, conn=Conn):
    return call(lambda: assign_talep(conn, row_id, body.assignee_id, body.assignee_name, body.actor_name))


@router.post("/{row_id}/status")
def status(row_id: int, body: StatusIn, conn=Conn):
    return call(lambda: set_talep_status(conn, row_id, body.status, body.note, body.actor_name))


@router.delete("/{row_id}", status_code=204)
def remove_talep(row_id: int, conn=Conn):
    call(lambda: delete_record(conn, "talepler", row_id))
