from fastapi import APIRouter

from app.deps import Auth, Conn, Owner, call
from app.services import (
    CONTACT_KIND,
    CONTACT_SCOPE,
    INVOICE_KIND,
    INVOICE_STATUS,
    LEDGER_KIND,
    PAY_METHOD,
    PROJECT_STATUS,
    REMINDER_STATUS,
    TALEP_STATUS,
    TASK_PRIORITY,
    TASK_REPEAT,
    TASK_STATUS,
    TASK_TYPE,
    dashboard,
)

router = APIRouter(prefix="/api", tags=["Özet"], dependencies=Auth)


@router.get("/dashboard")
def summary(conn=Conn, owner=Owner):
    return call(lambda: dashboard(conn, owner))


@router.get("/meta")
def meta():
    return {
        "task_status": TASK_STATUS,
        "priority": TASK_PRIORITY,
        "issue_type": TASK_TYPE,
        "repeat": TASK_REPEAT,
        "project_status": PROJECT_STATUS,
        "invoice_status": INVOICE_STATUS,
        "invoice_kind": INVOICE_KIND,
        "reminder_status": REMINDER_STATUS,
        "contact_kind": CONTACT_KIND,
        "contact_scope": CONTACT_SCOPE,
        "ledger_kind": LEDGER_KIND,
        "payment_method": PAY_METHOD,
        "talep_status": TALEP_STATUS,
    }
