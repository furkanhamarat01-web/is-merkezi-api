from fastapi import APIRouter, Query

from app.deps import Auth, Conn, Owner, call
from app.records import delete_record, get_record, list_records
from app.schemas import ReportIn, ReportPatch, dumped
from app.services import save_report

router = APIRouter(prefix="/api/reports", tags=["Raporlar"], dependencies=Auth)


@router.get("")
def list_reports(
    conn=Conn,
    owner=Owner,
    invoice_id: int | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    equals = {"invoice_id": invoice_id} if invoice_id else None
    return call(lambda: list_records(conn, "reports", owner, equals, q, limit, offset))


@router.get("/{row_id}")
def read_report(row_id: int, conn=Conn, owner=Owner):
    return call(lambda: get_record(conn, "reports", row_id, owner))


@router.post("", status_code=201)
def create_report(body: ReportIn, conn=Conn, owner=Owner):
    return call(lambda: save_report(conn, dumped(body), owner))


@router.patch("/{row_id}")
def update_report(row_id: int, body: ReportPatch, conn=Conn, owner=Owner):
    return call(lambda: save_report(conn, dumped(body), owner, row_id))


@router.delete("/{row_id}", status_code=204)
def remove_report(row_id: int, conn=Conn, owner=Owner):
    call(lambda: delete_record(conn, "reports", row_id, owner))
