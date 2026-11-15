import os
from urllib.parse import quote_plus


def api_token() -> str:
    return os.environ.get("API_TOKEN", "").strip()


def cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def database_url() -> str:
    explicit = os.environ.get("DATABASE_URL", "").strip()
    if explicit:
        return explicit
    user = os.environ.get("POSTGRES_USER", "postgres").strip() or "postgres"
    password = os.environ.get("POSTGRES_PASSWORD", "")
    host = os.environ.get("POSTGRES_HOST", "185.184.210.52").strip() or "185.184.210.52"
    port = os.environ.get("POSTGRES_PORT", "5433").strip() or "5433"
    name = os.environ.get("POSTGRES_DB", "stage_vkvdb").strip() or "stage_vkvdb"
    return f"postgresql+psycopg://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{name}"
