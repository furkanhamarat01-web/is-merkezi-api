import os
from pathlib import Path


def data_dir() -> Path:
    raw = os.environ.get("IS_MERKEZI_HOME", "").strip().strip('"')
    if raw:
        return Path(raw).expanduser()
    return Path(__file__).resolve().parents[1] / "data"


def db_path() -> Path:
    return data_dir() / "is_merkezi.db"


def api_token() -> str:
    return os.environ.get("API_TOKEN", "").strip()


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]
