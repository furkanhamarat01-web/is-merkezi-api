from fastapi import APIRouter, Query

from app.deps import Auth, Conn, Owner, call
from app.records import delete_record, get_record, list_records
from app.schemas import MoveTask, TaskIn, TaskPatch, dumped
from app.services import move_task, present_task, save_task

router = APIRouter(prefix="/api/tasks", tags=["Görevler"], dependencies=Auth)


@router.get("")
def list_tasks(
    conn=Conn,
    owner=Owner,
    status: str | None = None,
    project_id: int | None = None,
    q: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    equals = {}
    if status:
        equals["status"] = status
    if project_id:
        equals["project_id"] = project_id

    def run():
        page = list_records(conn, "tasks", owner, equals, q, limit, offset)
        page["items"] = [present_task(conn, item, owner) for item in page["items"]]
        return page

    return call(run)


@router.get("/{row_id}")
def read_task(row_id: int, conn=Conn, owner=Owner):
    return call(lambda: present_task(conn, get_record(conn, "tasks", row_id, owner), owner))


@router.post("", status_code=201)
def create_task(body: TaskIn, conn=Conn, owner=Owner):
    return call(lambda: save_task(conn, dumped(body), owner))


@router.patch("/{row_id}")
def update_task(row_id: int, body: TaskPatch, conn=Conn, owner=Owner):
    return call(lambda: save_task(conn, dumped(body), owner, row_id))


@router.post("/{row_id}/move")
def relocate_task(row_id: int, body: MoveTask, conn=Conn, owner=Owner):
    return call(lambda: move_task(conn, row_id, body.project_id, owner))


@router.delete("/{row_id}", status_code=204)
def remove_task(row_id: int, conn=Conn, owner=Owner):
    call(lambda: delete_record(conn, "tasks", row_id, owner))
