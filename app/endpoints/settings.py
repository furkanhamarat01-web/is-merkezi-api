import re

from fastapi import APIRouter

from app.deps import Auth, Conn, call
from app.logic import get_setting, set_setting
from app.schemas import SettingIn

router = APIRouter(prefix="/api/settings", tags=["Ayarlar"], dependencies=Auth)
_KEY = re.compile(r"^[a-z0-9_]{1,40}$")


def _check(key: str) -> str:
    if not _KEY.fullmatch(key):
        raise ValueError("Geçersiz ayar.")
    return key


@router.get("")
def list_settings(conn=Conn):
    rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
    return {"items": [{"key": row["key"], "value": row["value"]} for row in rows]}


@router.get("/{key}")
def read_setting(key: str, conn=Conn):
    return call(lambda: {"key": _check(key), "value": get_setting(conn, _check(key), "")})


@router.put("/{key}")
def write_setting(key: str, body: SettingIn, conn=Conn):
    def run():
        checked = _check(key)
        set_setting(conn, checked, body.value)
        return {"key": checked, "value": body.value}

    return call(run)
