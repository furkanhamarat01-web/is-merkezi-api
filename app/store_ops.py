"""Masaüstü arayüzünün kullandığı düz kayıt işlemleri."""

from datetime import date

from app.db import OWNED
from app.logic import project_key
from app.records import get_record, insert_record, list_records, update_record

_ready: set[tuple[str, int]] = set()


def _projects(conn, owner_id):
    return list_records(conn, "projects", owner_id, limit=5000)["items"]


def ensure_workspace(conn, owner_id, db_key: str):
    key = (db_key, owner_id or 0)
    if key in _ready:
        return
    owner = owner_id
    taken = set()
    for project in sorted(_projects(conn, owner), key=lambda item: item["id"]):
        current = "".join(ch for ch in str(project.get("proj_key") or "").upper() if ch.isalnum())[:6]
        if not current or current in taken:
            current = project_key(project.get("name"), taken)
            update_record(conn, "projects", project["id"], {"proj_key": current}, owner)
        taken.add(current)
    projects = _projects(conn, owner)
    genel = next((project for project in projects if str(project.get("proj_key") or "").upper() == "GEN"), None)
    if owner is None:
        homeless = conn.execute(
            "SELECT 1 FROM tasks WHERE project_id IS NULL OR project_id = 0 OR project_id NOT IN (SELECT id FROM projects) LIMIT 1"
        ).fetchone()
    else:
        homeless = conn.execute(
            """
            SELECT 1 FROM tasks
            WHERE owner_id=? AND (project_id IS NULL OR project_id = 0 OR project_id NOT IN (SELECT id FROM projects WHERE owner_id=?))
            LIMIT 1
            """,
            (owner, owner),
        ).fetchone()
    if genel is None and (homeless or not projects):
        created = insert_record(conn, "projects", {
            "name": "Genel",
            "proj_key": "GEN",
            "status": "Devam ediyor",
            "description": "Bir projeye bağlanmamış kayıtlar.",
        }, owner)
        genel_id = created["id"]
    elif genel is not None:
        genel_id = genel["id"]
    else:
        genel_id = projects[0]["id"]
    projects = {project["id"]: project for project in _projects(conn, owner)}
    counters = {}
    for project_id in projects:
        if owner is None:
            row = conn.execute(
                "SELECT COALESCE(MAX(issue_no), 0) AS n FROM tasks WHERE project_id=?",
                (project_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COALESCE(MAX(issue_no), 0) AS n FROM tasks WHERE project_id=? AND owner_id=?",
                (project_id, owner),
            ).fetchone()
        counters[project_id] = int(row["n"] or 0)
    if owner is None:
        orphans = conn.execute(
            """
            SELECT * FROM tasks
            WHERE project_id IS NULL OR project_id = 0 OR project_id NOT IN (SELECT id FROM projects)
               OR issue_no IS NULL OR issue_no = 0
               OR issue_type IS NULL OR issue_type = ''
            ORDER BY id
            """
        ).fetchall()
    else:
        orphans = conn.execute(
            """
            SELECT * FROM tasks
            WHERE owner_id=? AND (
                project_id IS NULL OR project_id = 0 OR project_id NOT IN (SELECT id FROM projects WHERE owner_id=?)
                OR issue_no IS NULL OR issue_no = 0
                OR issue_type IS NULL OR issue_type = ''
            )
            ORDER BY id
            """,
            (owner, owner),
        ).fetchall()
    for task in orphans:
        task = dict(task)
        project_id = task["project_id"] if task["project_id"] in projects else genel_id
        updates = {}
        if task["project_id"] != project_id:
            updates["project_id"] = project_id
        if not task["issue_no"]:
            counters[project_id] = counters.get(project_id, 0) + 1
            updates["issue_no"] = counters[project_id]
        if not (task["issue_type"] or "").strip():
            updates["issue_type"] = "Görev"
        if updates:
            update_record(conn, "tasks", task["id"], updates, owner)
    _ready.add(key)


def claim_owner(conn, owner_id: int, is_admin: bool):
    if not is_admin:
        return
    for table in OWNED:
        has_own = conn.execute(f"SELECT 1 FROM {table} WHERE owner_id=? LIMIT 1", (owner_id,)).fetchone()
        if has_own:
            continue
        orphans = conn.execute(
            f"SELECT 1 FROM {table} WHERE owner_id IS NULL OR owner_id!=? LIMIT 1",
            (owner_id,),
        ).fetchone()
        if orphans:
            conn.execute(
                f"UPDATE {table} SET owner_id=? WHERE owner_id IS NULL OR owner_id!=?",
                (owner_id, owner_id),
            )
    for table in OWNED:
        conn.execute(f"UPDATE {table} SET owner_id=? WHERE owner_id IS NULL", (owner_id,))


def next_issue_no(conn, project_id: int, owner_id):
    if owner_id is None:
        row = conn.execute(
            "SELECT COALESCE(MAX(issue_no), 0) + 1 AS n FROM tasks WHERE project_id=?",
            (int(project_id),),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT COALESCE(MAX(issue_no), 0) + 1 AS n FROM tasks WHERE project_id=? AND owner_id=?",
            (int(project_id), owner_id),
        ).fetchone()
    return int(row["n"]) if row else 1


def mark_seen(conn, key: str):
    conn.execute(
        "INSERT INTO notify_log(key, last_on) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET last_on=excluded.last_on",
        (key, date.today().isoformat()),
    )


def seen(conn, key: str) -> bool:
    return conn.execute("SELECT 1 FROM notify_log WHERE key=?", (key,)).fetchone() is not None
