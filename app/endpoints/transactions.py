from fastapi import APIRouter, Query

from app.deps import Auth, Conn, Owner, call
from app.logic import forget_ledger_category, ledger_category_names
from app.records import delete_record, get_record, list_records
from app.schemas import CategoryIn, TransactionIn, TransactionPatch, dumped
from app.services import save_transaction

router = APIRouter(prefix="/api/transactions", tags=["Gelir-Gider"], dependencies=Auth)


@router.get("")
def list_transactions(
    conn=Conn,
    owner=Owner,
    kind: str | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    equals = {"kind": kind} if kind else None
    return call(lambda: list_records(conn, "transactions", owner, equals, q, limit, offset, "trans_date DESC, id DESC"))


@router.get("/categories")
def categories(kind: str = "Gider", conn=Conn, owner=Owner):
    return call(lambda: {"kind": kind if kind in ("Gelir", "Gider") else "Gider", "items": ledger_category_names(conn, kind, owner)})


@router.post("/categories", status_code=201)
def add_category(body: CategoryIn, conn=Conn, owner=Owner):
    def run():
        from app.logic import remember_ledger_category
        if body.kind not in ("Gelir", "Gider"):
            raise ValueError("Tür geçersiz.")
        remember_ledger_category(conn, body.kind, body.name)
        return {"items": ledger_category_names(conn, body.kind, owner)}

    return call(run)


@router.delete("/categories")
def remove_category(body: CategoryIn, conn=Conn, owner=Owner):
    def run():
        if body.kind not in ("Gelir", "Gider"):
            raise ValueError("Tür geçersiz.")
        forget_ledger_category(conn, body.kind, body.name)
        return {"items": ledger_category_names(conn, body.kind, owner)}

    return call(run)


@router.get("/{row_id}")
def read_transaction(row_id: int, conn=Conn, owner=Owner):
    return call(lambda: get_record(conn, "transactions", row_id, owner))


@router.post("", status_code=201)
def create_transaction(body: TransactionIn, conn=Conn, owner=Owner):
    return call(lambda: save_transaction(conn, dumped(body), owner))


@router.patch("/{row_id}")
def update_transaction(row_id: int, body: TransactionPatch, conn=Conn, owner=Owner):
    return call(lambda: save_transaction(conn, dumped(body), owner, row_id))


@router.delete("/{row_id}", status_code=204)
def remove_transaction(row_id: int, conn=Conn, owner=Owner):
    call(lambda: delete_record(conn, "transactions", row_id, owner))
