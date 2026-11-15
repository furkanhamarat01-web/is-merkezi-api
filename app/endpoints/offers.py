from fastapi import APIRouter, Query

from app.deps import Auth, Conn, Owner, call
from app.records import delete_record, get_record, list_records
from app.schemas import OfferIn, OfferPatch, dumped
from app.services import save_offer

router = APIRouter(prefix="/api/offers", tags=["Teklifler"], dependencies=Auth)


@router.get("")
def list_offers(
    conn=Conn,
    owner=Owner,
    project_id: int | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    equals = {"project_id": project_id} if project_id else None
    return call(lambda: list_records(conn, "offers", owner, equals, q, limit, offset, "amount IS NULL, amount, id DESC"))


@router.get("/{row_id}")
def read_offer(row_id: int, conn=Conn, owner=Owner):
    return call(lambda: get_record(conn, "offers", row_id, owner))


@router.post("", status_code=201)
def create_offer(body: OfferIn, conn=Conn, owner=Owner):
    return call(lambda: save_offer(conn, dumped(body), owner))


@router.patch("/{row_id}")
def update_offer(row_id: int, body: OfferPatch, conn=Conn, owner=Owner):
    return call(lambda: save_offer(conn, dumped(body), owner, row_id))


@router.delete("/{row_id}", status_code=204)
def remove_offer(row_id: int, conn=Conn, owner=Owner):
    call(lambda: delete_record(conn, "offers", row_id, owner))
