from fastapi import APIRouter

router = APIRouter(tags=["Sağlık"])


@router.get("/health")
def health():
    return {"status": "ok", "name": "VKV İş Takip Merkezi API"}
