import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError

from app.config import api_token
from app.db import connect


def require_token(authorization: str | None = Header(default=None)) -> None:
    expected = api_token()
    if not expected:
        raise HTTPException(status_code=503, detail="API_TOKEN tanımlı değil.")
    if not authorization:
        raise HTTPException(status_code=401, detail="Yetkisiz.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Yetkisiz.")


def owner_id(x_owner_id: str | None = Header(default=None)) -> int | None:
    if x_owner_id is None or not str(x_owner_id).strip():
        return None
    try:
        value = int(str(x_owner_id).strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="X-Owner-Id sayı olmalı.") from exc
    if value <= 0:
        raise HTTPException(status_code=400, detail="X-Owner-Id sayı olmalı.")
    return value


def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def call(fn):
    try:
        return fn()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Bu kayıt zaten var.") from exc


Conn = Depends(get_conn)
Owner = Depends(owner_id)
Auth = [Depends(require_token)]
