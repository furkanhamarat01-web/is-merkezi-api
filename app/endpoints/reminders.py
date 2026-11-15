from fastapi import APIRouter, Query

from app.deps import Auth, Conn, Owner, call
from app.records import delete_record, get_record, list_records
from app.schemas import ReminderIn, ReminderPatch, dumped
from app.services import save_reminder

router = APIRouter(prefix="/api/reminders", tags=["Hatırlatmalar"], dependencies=Auth)


@router.get("")
def list_reminders(
    conn=Conn,
    owner=Owner,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    equals = {"status": status} if status else None
    return call(lambda: list_records(conn, "reminders", owner, equals, q, limit, offset, "remind_date, id DESC"))


@router.get("/{row_id}")
def read_reminder(row_id: int, conn=Conn, owner=Owner):
    return call(lambda: get_record(conn, "reminders", row_id, owner))


@router.post("", status_code=201)
def create_reminder(body: ReminderIn, conn=Conn, owner=Owner):
    return call(lambda: save_reminder(conn, dumped(body), owner))


@router.patch("/{row_id}")
def update_reminder(row_id: int, body: ReminderPatch, conn=Conn, owner=Owner):
    return call(lambda: save_reminder(conn, dumped(body), owner, row_id))


@router.delete("/{row_id}", status_code=204)
def remove_reminder(row_id: int, conn=Conn, owner=Owner):
    call(lambda: delete_record(conn, "reminders", row_id, owner))
