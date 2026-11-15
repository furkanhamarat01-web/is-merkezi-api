from app.db import OWNED, TABLES

SEARCH = {
    "tasks": ("title", "description", "assignee", "tag", "issue_type"),
    "invoices": ("party", "invoice_no", "description", "file_name"),
    "reminders": ("title", "description"),
    "contacts": ("name", "contact_person", "phone", "email", "tax_no"),
    "transactions": ("category", "description", "party"),
    "projects": ("name", "proj_key", "description"),
    "offers": ("vendor", "title", "notes", "pros", "cons"),
    "reports": ("title", "invoice_no", "reason"),
    "talepler": ("number", "title", "description", "author_name", "assignee_name", "target_name", "work_code"),
}


def _table(table: str) -> str:
    if table not in TABLES:
        raise ValueError("Geçersiz tablo.")
    return table


def _where(table: str, owner_id, equals: dict | None, q: str | None):
    clauses = []
    params = []
    if table in OWNED and owner_id is not None:
        clauses.append("owner_id=?")
        params.append(owner_id)
    for key, value in (equals or {}).items():
        if not key.replace("_", "").isalpha():
            raise ValueError("Geçersiz alan.")
        clauses.append(f"{key}=?")
        params.append(value)
    needle = " ".join(str(q or "").split())
    if needle:
        parts = [f"{column} LIKE ?" for column in SEARCH.get(table, ())]
        if parts:
            clauses.append("(" + " OR ".join(parts) + ")")
            params.extend([f"%{needle}%"] * len(parts))
    sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    return sql, params


def list_records(conn, table, owner_id=None, equals=None, q=None, limit=200, offset=0, order="id DESC"):
    table = _table(table)
    where, params = _where(table, owner_id, equals, q)
    total = conn.execute(f"SELECT COUNT(*) FROM {table}{where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM {table}{where} ORDER BY {order} LIMIT ? OFFSET ?",
        params + [int(limit), int(offset)],
    ).fetchall()
    return {"items": [dict(row) for row in rows], "count": int(total)}


def get_record(conn, table, row_id, owner_id=None):
    table = _table(table)
    if table in OWNED and owner_id is not None:
        row = conn.execute(
            f"SELECT * FROM {table} WHERE id=? AND owner_id=?",
            (int(row_id), owner_id),
        ).fetchone()
    else:
        row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (int(row_id),)).fetchone()
    if row is None:
        raise LookupError("Kayıt bulunamadı.")
    return dict(row)


def insert_record(conn, table, data, owner_id=None):
    table = _table(table)
    payload = dict(data)
    payload.pop("id", None)
    payload.pop("created_at", None)
    if table in OWNED and owner_id is not None:
        payload["owner_id"] = owner_id
    else:
        payload.pop("owner_id", None)
    if not payload:
        raise ValueError("Kayıt boş.")
    keys = list(payload)
    marks = ",".join("?" for _ in keys)
    columns = ",".join(keys)
    cursor = conn.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({marks})",
        [payload[key] for key in keys],
    )
    return get_record(conn, table, int(cursor.lastrowid), owner_id if table in OWNED else None)


def update_record(conn, table, row_id, data, owner_id=None):
    current = get_record(conn, table, row_id, owner_id)
    payload = dict(data)
    payload.pop("id", None)
    payload.pop("created_at", None)
    payload.pop("owner_id", None)
    if not payload:
        raise ValueError("Güncellenecek alan yok.")
    keys = list(payload)
    assignments = ",".join(f"{key}=?" for key in keys)
    table = _table(table)
    if table in OWNED and owner_id is not None:
        conn.execute(
            f"UPDATE {table} SET {assignments} WHERE id=? AND owner_id=?",
            [payload[key] for key in keys] + [int(row_id), owner_id],
        )
    else:
        conn.execute(
            f"UPDATE {table} SET {assignments} WHERE id=?",
            [payload[key] for key in keys] + [int(row_id)],
        )
    return get_record(conn, table, current["id"], owner_id)


def delete_record(conn, table, row_id, owner_id=None):
    get_record(conn, table, row_id, owner_id)
    table = _table(table)
    if table in OWNED and owner_id is not None:
        conn.execute(f"DELETE FROM {table} WHERE id=? AND owner_id=?", (int(row_id), owner_id))
    else:
        conn.execute(f"DELETE FROM {table} WHERE id=?", (int(row_id),))
