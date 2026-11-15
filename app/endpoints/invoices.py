from fastapi import APIRouter, Query

from app.deps import Auth, Conn, Owner, call
from app.records import delete_record, get_record, list_records
from app.schemas import InvoiceIn, InvoicePatch, PaymentIn, dumped
from app.services import cancel_invoice, collect_invoice, present_invoice, save_invoice

router = APIRouter(prefix="/api/invoices", tags=["Faturalar"], dependencies=Auth)


@router.get("")
def list_invoices(
    conn=Conn,
    owner=Owner,
    status: str | None = None,
    kind: str | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    equals = {}
    if status:
        equals["status"] = status
    if kind:
        equals["kind"] = kind

    def run():
        page = list_records(conn, "invoices", owner, equals, q, limit, offset)
        page["items"] = [present_invoice(item) for item in page["items"]]
        return page

    return call(run)


@router.get("/{row_id}")
def read_invoice(row_id: int, conn=Conn, owner=Owner):
    return call(lambda: present_invoice(get_record(conn, "invoices", row_id, owner)))


@router.post("", status_code=201)
def create_invoice(body: InvoiceIn, conn=Conn, owner=Owner):
    return call(lambda: save_invoice(conn, dumped(body), owner))


@router.patch("/{row_id}")
def update_invoice(row_id: int, body: InvoicePatch, conn=Conn, owner=Owner):
    return call(lambda: save_invoice(conn, dumped(body), owner, row_id))


@router.post("/{row_id}/payments")
def pay_invoice(row_id: int, body: PaymentIn, conn=Conn, owner=Owner):
    return call(lambda: collect_invoice(conn, row_id, body.amount, owner))


@router.post("/{row_id}/cancel")
def cancel(row_id: int, conn=Conn, owner=Owner):
    return call(lambda: cancel_invoice(conn, row_id, owner))


@router.delete("/{row_id}", status_code=204)
def remove_invoice(row_id: int, conn=Conn, owner=Owner):
    call(lambda: delete_record(conn, "invoices", row_id, owner))
