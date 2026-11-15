import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from app.talep.logic import (
    ADMIN_EMAIL,
    ADMIN_ROLE,
    FILE_EXT,
    LOG_EVENTS,
    MAX_FILE,
    NOTE_STATUSES,
    PRIORITIES,
    ROLES,
    STATUSES,
    check_password,
    clean_code,
    clean_email,
    clean_request_code,
    clean_username,
    code_from_topic,
    hash_password,
    note_list,
    totp_ok,
)


def _row(row):
    return None if row is None else dict(row)


def ensure_roles(conn):
    admin = conn.execute("SELECT id FROM talep_users WHERE email=?", (ADMIN_EMAIL,)).fetchone()
    if admin is not None:
        conn.execute(
            "UPDATE talep_users SET is_admin=1, role=? WHERE email=?",
            (ADMIN_ROLE, ADMIN_EMAIL),
        )
        conn.execute("UPDATE talep_users SET is_admin=0 WHERE email!=?", (ADMIN_EMAIL,))
        conn.execute(
            "UPDATE talep_users SET role=? WHERE email!=? AND (role IS NULL OR role='' OR role=?)",
            ("Kullanıcı", ADMIN_EMAIL, ADMIN_ROLE),
        )
        return
    conn.execute(
        "UPDATE talep_users SET role=? WHERE is_admin=1 AND (role IS NULL OR role='')",
        (ADMIN_ROLE,),
    )
    conn.execute(
        "UPDATE talep_users SET role=? WHERE is_admin=0 AND (role IS NULL OR role='')",
        ("Kullanıcı",),
    )


def user_count(conn):
    return int(conn.execute("SELECT COUNT(*) AS n FROM talep_users").fetchone()["n"])


def add_user(conn, name, email, password, secret, is_admin=False, username="", must_change=None, role=None):
    email = clean_email(email)
    name = " ".join(str(name or "").split())
    username = clean_username(username) or clean_username(email.split("@", 1)[0])
    if len(username) < 3:
        username = (username + "kullanici")[:32]
    if not name or "@" not in email or len(password) < 6 or len(username) < 3:
        raise ValueError("Ad, kullanıcı adı, e-posta ve en az 6 karakterlik parola gerekli.")
    if email == ADMIN_EMAIL:
        is_admin = True
        role = ADMIN_ROLE
    elif is_admin:
        raise ValueError("Yönetici hesabı yalnızca furkan.hamarat01@gmail.com olabilir.")
    elif role not in ROLES:
        raise ValueError("Rol seç.")
    if must_change is None:
        must_change = 0 if is_admin else 1
    try:
        cursor = conn.execute(
            """
            INSERT INTO talep_users (name, email, password, totp_secret, is_admin, username, must_change, role)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (name, email, hash_password(password), secret, 1 if is_admin else 0, username, 1 if must_change else 0, role),
        )
        conn.commit()
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("Bu e-posta veya kullanıcı adı zaten kayıtlı.") from exc
    return int(cursor.lastrowid)


def set_password(conn, user_id, password, must_change=False):
    if len(password) < 6:
        raise ValueError("Parola en az 6 karakter olmalı.")
    conn.execute(
        "UPDATE talep_users SET password=?, must_change=? WHERE id=?",
        (hash_password(password), 1 if must_change else 0, int(user_id)),
    )
    conn.commit()


def update_user(conn, user_id, name, email, username, team_id=None, role=None):
    current = conn.execute("SELECT * FROM talep_users WHERE id=?", (int(user_id),)).fetchone()
    if current is None:
        raise ValueError("Kullanıcı yok.")
    email = clean_email(email)
    name = " ".join(str(name or "").split())
    username = clean_username(username)
    if not name or "@" not in email or len(username) < 3:
        raise ValueError("Ad, kullanıcı adı ve e-posta gerekli.")
    if clean_email(current["email"]) == ADMIN_EMAIL:
        email = ADMIN_EMAIL
        role = ADMIN_ROLE
        is_admin = 1
    else:
        if email == ADMIN_EMAIL:
            raise ValueError("Bu e-posta yönetici hesabına ayrılmıştır.")
        if role not in ROLES:
            raise ValueError("Rol seç.")
        is_admin = 0
    try:
        conn.execute(
            "UPDATE talep_users SET name=?, email=?, username=?, role=?, is_admin=? WHERE id=?",
            (name, email, username, role, is_admin, int(user_id)),
        )
        if team_id:
            conn.execute("DELETE FROM talep_members WHERE user_id=?", (int(user_id),))
            conn.execute(
                "INSERT INTO talep_members (user_id, team_id) VALUES (?,?) ON CONFLICT(user_id, team_id) DO NOTHING",
                (int(user_id), int(team_id)),
            )
        conn.commit()
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("Bu e-posta veya kullanıcı adı zaten kayıtlı.") from exc


def add_login_log(conn, email, event, user=None, device=None):
    if event not in LOG_EVENTS:
        raise ValueError("Kayıt türü yok.")
    device = device or {}
    name = ""
    user_id = None
    if user is not None:
        user_id = int(user["id"])
        name = " ".join(str(user["name"] or "").split())[:80]
    conn.execute(
        """
        INSERT INTO talep_login_logs (user_id, name, email, event, device, os_name, ip, created_at)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            user_id,
            name,
            clean_email(email)[:120],
            event,
            str(device.get("device") or "")[:80],
            str(device.get("os") or "")[:80],
            str(device.get("ip") or "")[:64],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()


def login_logs(conn, limit=400):
    rows = conn.execute(
        "SELECT * FROM talep_login_logs ORDER BY id DESC LIMIT ?",
        (int(limit),),
    ).fetchall()
    return [dict(row) for row in rows]


def user_by_email(conn, email):
    return _row(conn.execute("SELECT * FROM talep_users WHERE email=?", (clean_email(email),)).fetchone())


def users(conn):
    return [dict(row) for row in conn.execute("SELECT * FROM talep_users ORDER BY name").fetchall()]


def add_team(conn, name, code, topic=""):
    name = " ".join(str(name or "").split())
    topic = " ".join(str(topic or "").split())
    code = clean_code(code) or code_from_topic(topic)
    if len(name) < 2 or len(code) < 2:
        raise ValueError("Ekip adı ve konu gerekli. Dış talep kodu konudan üretilir.")
    try:
        cursor = conn.execute(
            "INSERT INTO talep_teams (name, code, topic) VALUES (?,?,?)",
            (name, code, topic),
        )
        conn.commit()
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("Bu dış talep kodu kullanılıyor.") from exc
    return int(cursor.lastrowid)


def update_team(conn, team_id, name, topic, code):
    name = " ".join(str(name or "").split())
    topic = " ".join(str(topic or "").split())
    code = clean_code(code) or code_from_topic(topic)
    if len(name) < 2 or len(code) < 2:
        raise ValueError("Ekip adı ve konu gerekli.")
    try:
        conn.execute(
            "UPDATE talep_teams SET name=?, topic=?, code=? WHERE id=?",
            (name, topic, code, int(team_id)),
        )
        conn.commit()
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("Bu dış talep kodu kullanılıyor.") from exc


def teams(conn):
    return [dict(row) for row in conn.execute("SELECT * FROM talep_teams ORDER BY name").fetchall()]


def _code_team_id(conn, team_id, all_teams):
    if conn.execute("SELECT id FROM talep_teams WHERE id=?", (int(team_id),)).fetchone() is None:
        raise ValueError("Hedef ekip seç." if all_teams else "Ekip seç.")
    return int(team_id)


def add_request_code(conn, code, team_id, work_code, title="", scope="İç", all_teams=False):
    code = clean_request_code(code)
    work_code = " ".join(str(work_code or "").split())[:40] or code
    title = " ".join(str(title or "").split())[:120]
    scope = scope if scope in ("İç", "Dış") else "İç"
    shared = 1 if all_teams else 0
    if len(code) < 2 or not str(work_code).strip() or len(title) < 2:
        raise ValueError("Talep kodu, başlık ve iş kodu gerekli.")
    team_id = _code_team_id(conn, team_id, shared)
    try:
        cursor = conn.execute(
            """
            INSERT INTO talep_request_codes (code, team_id, work_code, title, scope, all_teams)
            VALUES (?,?,?,?,?,?)
            """,
            (code, team_id, work_code, title, scope, shared),
        )
        conn.commit()
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("Bu talep kodu kullanılıyor.") from exc
    return int(cursor.lastrowid)


def update_request_code(conn, code_id, code, team_id, work_code, title="", scope="İç", all_teams=False):
    code = clean_request_code(code)
    work_code = " ".join(str(work_code or "").split())[:40] or code
    title = " ".join(str(title or "").split())[:120]
    scope = scope if scope in ("İç", "Dış") else "İç"
    shared = 1 if all_teams else 0
    if len(code) < 2 or not str(work_code).strip() or len(title) < 2:
        raise ValueError("Talep kodu, başlık ve iş kodu gerekli.")
    team_id = _code_team_id(conn, team_id, shared)
    try:
        conn.execute(
            """
            UPDATE talep_request_codes
            SET code=?, team_id=?, work_code=?, title=?, scope=?, all_teams=?
            WHERE id=?
            """,
            (code, team_id, work_code, title, scope, shared, int(code_id)),
        )
        conn.commit()
    except IntegrityError as exc:
        conn.rollback()
        raise ValueError("Bu talep kodu kullanılıyor.") from exc


def request_codes(conn):
    rows = conn.execute(
        """
        SELECT c.*, t.name AS team_name, t.code AS team_code
        FROM talep_request_codes c
        LEFT JOIN talep_teams t ON t.id = c.team_id
        ORDER BY COALESCE(c.all_teams, 0) DESC, t.name, c.code
        """
    ).fetchall()
    return [dict(row) for row in rows]


def team_by_code(conn, code):
    return _row(conn.execute("SELECT * FROM talep_teams WHERE code=?", (clean_code(code),)).fetchone())


def add_member(conn, user_id, team_id):
    conn.execute(
        "INSERT INTO talep_members (user_id, team_id) VALUES (?,?) ON CONFLICT(user_id, team_id) DO NOTHING",
        (int(user_id), int(team_id)),
    )
    conn.commit()


def team_ids(conn, user_id):
    rows = conn.execute("SELECT team_id FROM talep_members WHERE user_id=?", (int(user_id),)).fetchall()
    return [int(row["team_id"]) for row in rows]


def user_teams(conn, user_id):
    rows = conn.execute(
        """
        SELECT t.* FROM talep_teams t
        JOIN talep_members m ON m.team_id = t.id
        WHERE m.user_id=?
        ORDER BY t.name
        """,
        (int(user_id),),
    ).fetchall()
    return [dict(row) for row in rows]


def member_count(conn, team_id):
    return int(conn.execute(
        "SELECT COUNT(*) AS n FROM talep_members WHERE team_id=?",
        (int(team_id),),
    ).fetchone()["n"])


def login(conn, email, password, code):
    user = user_by_email(conn, email)
    if user is None or not check_password(password, user["password"]) or not totp_ok(user["totp_secret"], code):
        return None
    return user


def _select_sql():
    return """
        SELECT r.*, s.name AS source_name, t.name AS target_name, t.code AS target_code,
               u.name AS author_name, u.email AS author_email
        FROM talep_requests r
        JOIN talep_teams s ON s.id = r.team_id
        JOIN talep_teams t ON t.id = r.target_team_id
        JOIN talep_users u ON u.id = r.author_id
    """


def create_request(conn, author_id, team_id, target_team_id, work_code, title, description, priority, due_date):
    title = " ".join(str(title or "").split())
    work_code = " ".join(str(work_code or "").split())[:40]
    if not title:
        raise ValueError("Başlık gerekli.")
    if not work_code:
        raise ValueError("İş kodu gerekli.")
    if priority not in PRIORITIES:
        raise ValueError("Öncelik seç.")
    due = str(due_date or "").strip()
    if due:
        try:
            datetime.strptime(due, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Tarih YYYY-AA-GG biçiminde olmalı.") from exc
    try:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM talep_requests WHERE target_team_id=?",
            (int(target_team_id),),
        ).fetchone()["n"]
        target = conn.execute("SELECT * FROM talep_teams WHERE id=?", (int(target_team_id),)).fetchone()
        if target is None:
            raise ValueError("Hedef ekip yok.")
        number = f"{target['code']}-{int(count) + 1}"
        cursor = conn.execute(
            """
            INSERT INTO talep_requests (
              number, team_id, target_team_id, author_id, work_code, title,
              description, priority, due_date, status
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                number, int(team_id), int(target_team_id), int(author_id), work_code, title[:180],
                str(description or "").strip()[:4000], priority, due, "Açık",
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return request(conn, cursor.lastrowid)


def save_file(conn, request_id, name, payload):
    source = Path(str(name or "dosya"))
    if source.suffix.lower() not in FILE_EXT:
        raise ValueError("PDF, PNG veya JPG eklenebilir.")
    data = bytes(payload or b"")
    if len(data) > MAX_FILE:
        raise ValueError("Dosya 20 MB sınırını aşıyor.")
    if request(conn, request_id) is None:
        raise ValueError("Talep yok.")
    filename = source.name[:180]
    existing = conn.execute(
        "SELECT id FROM talep_files WHERE request_id=?",
        (int(request_id),),
    ).fetchone()
    if existing is None:
        conn.execute(
            "INSERT INTO talep_files (request_id, name, content) VALUES (?,?,?)",
            (int(request_id), filename, data),
        )
    else:
        conn.execute(
            "UPDATE talep_files SET name=?, content=? WHERE request_id=?",
            (filename, data, int(request_id)),
        )
    conn.execute(
        "UPDATE talep_requests SET file_path=? WHERE id=?",
        (filename, int(request_id)),
    )
    conn.commit()
    return request(conn, request_id)


def file_bytes(conn, request_id):
    row = conn.execute(
        "SELECT name, content FROM talep_files WHERE request_id=?",
        (int(request_id),),
    ).fetchone()
    if row is None:
        raise LookupError("Dosya yok.")
    return row["name"], bytes(row["content"])


def pending_vkv(conn):
    rows = conn.execute(_select_sql() + " WHERE r.vkv_task_id IS NULL ORDER BY r.id").fetchall()
    return [dict(row) for row in rows]


def mark_vkv(conn, request_id, task_id, issue_key):
    conn.execute(
        "UPDATE talep_requests SET vkv_task_id=?, vkv_key=? WHERE id=?",
        (int(task_id) if task_id else None, issue_key or "", int(request_id)),
    )
    conn.commit()


def set_status(conn, request_id, status, note=""):
    if status not in STATUSES:
        raise ValueError("Durum yok.")
    text = " ".join(str(note or "").split())
    if status in NOTE_STATUSES and not text:
        raise ValueError("Not gerekli.")
    current = conn.execute(
        "SELECT notes_json FROM talep_requests WHERE id=?",
        (int(request_id),),
    ).fetchone()
    if current is None:
        raise ValueError("Talep yok.")
    notes = note_list(current["notes_json"])
    if text:
        notes.append({"status": status, "note": text[:1000], "at": datetime.now().strftime("%Y-%m-%d %H:%M")})
    conn.execute(
        "UPDATE talep_requests SET status=?, notes_json=? WHERE id=?",
        (status, json.dumps(notes, ensure_ascii=False), int(request_id)),
    )
    conn.commit()


def request(conn, request_id):
    return _row(conn.execute(_select_sql() + " WHERE r.id=?", (int(request_id),)).fetchone())


def visible_requests(conn, user):
    if user["is_admin"]:
        rows = conn.execute(_select_sql() + " ORDER BY r.id DESC").fetchall()
    else:
        rows = conn.execute(
            _select_sql() + """
            WHERE r.team_id IN (SELECT team_id FROM talep_members WHERE user_id=?)
               OR r.target_team_id IN (SELECT team_id FROM talep_members WHERE user_id=?)
            ORDER BY r.id DESC
            """,
            (int(user["id"]), int(user["id"])),
        ).fetchall()
    return [dict(row) for row in rows]
