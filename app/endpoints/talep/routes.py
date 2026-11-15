from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from app.deps import Auth, Conn, call
from app.talep.logic import public_user, screens_for
from app.talep import store

router = APIRouter(prefix="/api/talep", tags=["VKV Talep"], dependencies=Auth)


class UserIn(BaseModel):
    name: str = ""
    email: str = ""
    password: str = ""
    secret: str = ""
    is_admin: bool = False
    username: str = ""
    must_change: bool | None = None
    role: str | None = None


class UserUpdate(BaseModel):
    name: str = ""
    email: str = ""
    username: str = ""
    team_id: int | None = None
    role: str | None = None


class PasswordIn(BaseModel):
    password: str
    must_change: bool = False


class LoginIn(BaseModel):
    email: str = ""
    password: str = ""
    code: str = ""


class SessionIn(BaseModel):
    username: str = ""
    password: str = ""
    device: dict | None = None


class ForgotIn(BaseModel):
    username: str = ""


class SetupIn(BaseModel):
    name: str = ""
    username: str = ""
    password: str = ""
    email: str = ""


class LogIn(BaseModel):
    email: str = ""
    event: str
    user: dict | None = None
    device: dict | None = None


class TeamIn(BaseModel):
    name: str = ""
    code: str = ""
    topic: str = ""


class MemberIn(BaseModel):
    user_id: int
    team_id: int


class CodeIn(BaseModel):
    code: str = ""
    team_id: int
    work_code: str = ""
    title: str = ""
    scope: str = "İç"
    all_teams: bool = False


class RequestIn(BaseModel):
    author_id: int
    team_id: int
    target_team_id: int
    work_code: str = ""
    title: str = ""
    description: str = ""
    priority: str = ""
    due_date: str = ""


class StatusIn(BaseModel):
    status: str
    note: str = ""


class VkvIn(BaseModel):
    task_id: int | None = None
    issue_key: str = ""


class FileIn(BaseModel):
    name: str
    data: str


def _session(conn, user):
    if user is None:
        return None
    member = [{"name": team["name"], "code": team["code"]} for team in store.user_teams(conn, user["id"])]
    teams = [{"name": team["name"], "code": team["code"]} for team in store.teams(conn)] if user["is_admin"] else member
    data = public_user(user)
    data.pop("totp_secret", None)
    data["is_admin"] = bool(int(data.get("is_admin") or 0))
    data["must_change"] = bool(int(data.get("must_change") or 0))
    data["role"] = data.get("role") or ("Yönetici" if data["is_admin"] else "Kullanıcı")
    data["screens"] = screens_for(data["role"])
    data["teams"] = teams
    data["member_teams"] = member
    return data


def _actor(conn, user_id):
    row = conn.execute("SELECT * FROM talep_users WHERE id=?", (int(user_id),)).fetchone()
    if row is None:
        raise ValueError("Kullanıcı yok.")
    return dict(row)


@router.get("/users/count")
def count_users(conn=Conn):
    return {"n": store.user_count(conn)}


@router.get("/users/by-email")
def by_email(email: str, conn=Conn):
    return public_user(store.user_by_email(conn, email))


@router.get("/users")
def list_users(conn=Conn):
    return [public_user(row) for row in store.users(conn)]


@router.post("/users", status_code=201)
def create_user(body: UserIn, conn=Conn):
    def run():
        return {
            "id": store.add_user(
                conn, body.name, body.email, body.password, body.secret, body.is_admin,
                body.username, body.must_change, body.role,
            )
        }
    return call(run)


@router.patch("/users/{user_id}")
def patch_user(user_id: int, body: UserUpdate, conn=Conn):
    return call(lambda: store.update_user(conn, user_id, body.name, body.email, body.username, body.team_id, body.role) or {"ok": True})


@router.post("/users/{user_id}/password")
def change_password(user_id: int, body: PasswordIn, conn=Conn):
    return call(lambda: store.set_password(conn, user_id, body.password, body.must_change) or {"ok": True})


@router.get("/users/{user_id}/teams")
def teams_of(user_id: int, conn=Conn):
    return store.user_teams(conn, user_id)


@router.get("/users/{user_id}/team-ids")
def ids_of(user_id: int, conn=Conn):
    return {"ids": store.team_ids(conn, user_id)}


@router.post("/setup", status_code=201)
def setup(body: SetupIn, conn=Conn):
    def run():
        if store.user_count(conn):
            raise ValueError("İlk hesap zaten var.")
        email = body.email or f"{body.username}@vkv.local"
        store.add_user(conn, body.name, email, body.password, "", username=body.username, role="Yönetici")
        user = store.user_by_username(conn, body.username)
        return _session(conn, user)
    return call(run)


@router.post("/session")
def session(body: SessionIn, conn=Conn):
    user = store.open_session(conn, body.username, body.password, body.device)
    return {"user": _session(conn, user)}


@router.post("/forgot")
def forgot(body: ForgotIn, conn=Conn):
    store.request_reset(conn, body.username)
    return {"ok": True}


@router.get("/resets")
def resets(conn=Conn):
    return store.reset_requests(conn)


@router.post("/resets/{reset_id}/password")
def give_password(reset_id: int, body: PasswordIn, conn=Conn):
    return call(lambda: store.grant_reset(conn, reset_id, body.password) or {"ok": True})


@router.get("/users/{user_id}/account")
def account(user_id: int, conn=Conn):
    return _session(conn, store.account(conn, user_id))


@router.get("/teams/members")
def team_members(name: str, conn=Conn):
    return store.members_of_team(conn, name)


@router.post("/login")
def sign_in(body: LoginIn, conn=Conn):
    return {"user": public_user(store.login(conn, body.email, body.password, body.code))}


@router.post("/login-logs", status_code=201)
def write_log(body: LogIn, conn=Conn):
    return call(lambda: store.add_login_log(conn, body.email, body.event, body.user, body.device) or {"ok": True})


@router.get("/login-logs")
def read_logs(conn=Conn, limit: int = 400):
    return store.login_logs(conn, limit)


@router.get("/teams")
def list_teams(conn=Conn):
    return store.teams(conn)


@router.get("/teams/by-code")
def team_code(code: str, conn=Conn):
    return store.team_by_code(conn, code)


@router.post("/teams", status_code=201)
def create_team(body: TeamIn, conn=Conn):
    return call(lambda: {"id": store.add_team(conn, body.name, body.code, body.topic)})


@router.patch("/teams/{team_id}")
def patch_team(team_id: int, body: TeamIn, conn=Conn):
    return call(lambda: store.update_team(conn, team_id, body.name, body.topic, body.code) or {"ok": True})


@router.get("/teams/{team_id}/member-count")
def members(team_id: int, conn=Conn):
    return {"n": store.member_count(conn, team_id)}


@router.post("/members", status_code=201)
def join(body: MemberIn, conn=Conn):
    store.add_member(conn, body.user_id, body.team_id)
    return {"ok": True}


@router.get("/request-codes")
def list_codes(conn=Conn):
    return store.request_codes(conn)


@router.post("/request-codes", status_code=201)
def create_code(body: CodeIn, conn=Conn):
    def run():
        return {
            "id": store.add_request_code(
                conn, body.code, body.team_id, body.work_code, body.title, body.scope, body.all_teams,
            )
        }
    return call(run)


@router.patch("/request-codes/{code_id}")
def patch_code(code_id: int, body: CodeIn, conn=Conn):
    def run():
        store.update_request_code(
            conn, code_id, body.code, body.team_id, body.work_code, body.title, body.scope, body.all_teams,
        )
        return {"ok": True}
    return call(run)


@router.get("/requests/pending-vkv")
def pending(conn=Conn):
    return store.pending_vkv(conn)


@router.get("/requests")
def list_requests(user_id: int, conn=Conn):
    return call(lambda: store.visible_requests(conn, _actor(conn, user_id)))


@router.get("/requests/{request_id}")
def read_request(request_id: int, conn=Conn):
    return store.request(conn, request_id)


@router.post("/requests", status_code=201)
def create_request(body: RequestIn, conn=Conn):
    def run():
        return store.create_request(
            conn, body.author_id, body.team_id, body.target_team_id, body.work_code,
            body.title, body.description, body.priority, body.due_date,
        )
    return call(run)


@router.post("/requests/{request_id}/status")
def status(request_id: int, body: StatusIn, conn=Conn):
    return call(lambda: store.set_status(conn, request_id, body.status, body.note) or {"ok": True})


@router.post("/requests/{request_id}/vkv")
def vkv(request_id: int, body: VkvIn, conn=Conn):
    store.mark_vkv(conn, request_id, body.task_id, body.issue_key)
    return {"ok": True}


@router.post("/requests/{request_id}/file")
def upload(request_id: int, body: FileIn, conn=Conn):
    import base64

    def run():
        try:
            payload = base64.b64decode(body.data, validate=True)
        except Exception as exc:
            raise ValueError("Dosya okunamadı.") from exc
        return store.save_file(conn, request_id, body.name, payload)

    return call(run)


@router.get("/requests/{request_id}/file")
def download(request_id: int, conn=Conn):
    def run():
        name, payload = store.file_bytes(conn, request_id)
        return Response(
            content=payload,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
        )
    return call(run)
