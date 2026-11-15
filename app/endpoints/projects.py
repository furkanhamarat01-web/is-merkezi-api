from fastapi import APIRouter, Query

from app.deps import Auth, Conn, Owner, call
from app.records import delete_record, get_record, list_records
from app.schemas import ProjectIn, ProjectPatch, dumped
from app.services import delete_project_offers, save_project

router = APIRouter(prefix="/api/projects", tags=["Projeler"], dependencies=Auth)


@router.get("")
def list_projects(
    conn=Conn,
    owner=Owner,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    equals = {"status": status} if status else None
    return call(lambda: list_records(conn, "projects", owner, equals, q, limit, offset, "name COLLATE NOCASE"))


@router.get("/{row_id}")
def read_project(row_id: int, conn=Conn, owner=Owner):
    return call(lambda: get_record(conn, "projects", row_id, owner))


@router.get("/{row_id}/offers")
def project_offers(row_id: int, conn=Conn, owner=Owner):
    def run():
        get_record(conn, "projects", row_id, owner)
        return list_records(conn, "offers", owner, {"project_id": row_id}, limit=500, order="amount IS NULL, amount, id DESC")

    return call(run)


@router.delete("/{row_id}/offers")
def clear_offers(row_id: int, conn=Conn, owner=Owner):
    return call(lambda: delete_project_offers(conn, row_id, owner))


@router.post("", status_code=201)
def create_project(body: ProjectIn, conn=Conn, owner=Owner):
    return call(lambda: save_project(conn, dumped(body), owner))


@router.patch("/{row_id}")
def update_project(row_id: int, body: ProjectPatch, conn=Conn, owner=Owner):
    return call(lambda: save_project(conn, dumped(body), owner, row_id))


@router.delete("/{row_id}", status_code=204)
def remove_project(row_id: int, conn=Conn, owner=Owner):
    call(lambda: delete_record(conn, "projects", row_id, owner))
