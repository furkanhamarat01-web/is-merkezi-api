import json
from datetime import date, datetime

from app.logic import (
    choice,
    clean_amount,
    clean_date,
    clean_text,
    format_amount,
    invoice_events,
    invoice_money,
    project_key,
    sla_breached,
    stamp_task_wait,
)
from app.records import delete_record, get_record, insert_record, list_records, update_record

TASK_STATUS = ("Bekliyor", "Devam ediyor", "Tamamlandı", "İptal")
TASK_PRIORITY = ("Düşük", "Normal", "Yüksek", "Acil")
TASK_TYPE = ("Görev", "Hata", "İyileştirme")
TASK_REPEAT = ("Yok", "Her gün", "Her hafta", "Her ay")
PROJECT_STATUS = ("Planlandı", "Devam ediyor", "Beklemede", "Tamamlandı", "İptal")
INVOICE_STATUS = ("Ödenmedi", "Ödendi", "Kısmi ödendi", "İptal")
INVOICE_KIND = ("Gelen", "Kesilen")
REMINDER_STATUS = ("Aktif", "Tamamlandı")
CONTACT_KIND = ("Firma", "Kişi")
CONTACT_SCOPE = ("Şirket içi", "Dış")
LEDGER_KIND = ("Gelir", "Gider")
PAY_METHOD = ("Nakit", "Banka", "Kredi kartı", "Diğer")
TALEP_STATUS = ("Açık", "Üzerinde", "Beklemede", "Tamamlandı", "Reddedildi")


def _projects(conn, owner_id):
    return list_records(conn, "projects", owner_id, limit=500)["items"]


def _taken_keys(conn, owner_id, skip_id=None):
    taken = set()
    for project in _projects(conn, owner_id):
        if skip_id and project["id"] == int(skip_id):
            continue
        key = "".join(ch for ch in str(project.get("proj_key") or "").upper() if ch.isalnum())
        if key:
            taken.add(key)
    return taken


def general_project_id(conn, owner_id):
    for project in _projects(conn, owner_id):
        if str(project.get("proj_key") or "").upper() == "GEN":
            return project["id"]
    saved = save_project(conn, {"name": "Genel", "proj_key": "GEN", "status": "Devam ediyor", "description": "Bir projeye bağlanmamış kayıtlar."}, owner_id)
    return saved["id"]


def next_issue_no(conn, project_id, owner_id):
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


def issue_key(conn, task, owner_id):
    number = task.get("issue_no") or task["id"]
    prefix = "PRJ"
    if task.get("project_id"):
        try:
            project = get_record(conn, "projects", task["project_id"], owner_id)
        except LookupError:
            project = None
        if project and project.get("proj_key"):
            prefix = project["proj_key"]
    return f"{prefix}-{int(number)}"


def present_task(conn, task, owner_id):
    task = dict(task)
    task["issue_key"] = issue_key(conn, task, owner_id)
    task["sla_breached"] = sla_breached(task)
    return task


def save_project(conn, data, owner_id, row_id=None):
    current = get_record(conn, "projects", row_id, owner_id) if row_id else None
    name = clean_text(data.get("name", current.get("name") if current else ""), 120, required=True, label="Proje adı")
    taken = _taken_keys(conn, owner_id, skip_id=row_id)
    existing = ""
    if current and current.get("proj_key"):
        existing = "".join(ch for ch in current["proj_key"].upper() if ch.isalnum())[:6]
    typed = "".join(ch for ch in str(data.get("proj_key") or "").upper() if ch.isalnum())[:6]
    if "proj_key" in data and typed and typed not in taken:
        key = typed
    elif existing:
        key = existing
    else:
        key = project_key(name, taken)
    payload = {
        "name": name,
        "proj_key": key,
        "description": clean_text(data.get("description", ""), 4000),
        "start_date": clean_date(data.get("start_date", "")),
        "end_date": clean_date(data.get("end_date", "")),
        "status": choice(data.get("status"), PROJECT_STATUS, "Durum", "Devam ediyor"),
        "budget": clean_amount(data.get("budget"), required=False),
        "notes": clean_text(data.get("notes", ""), 4000),
    }
    if row_id and "description" not in data:
        payload["description"] = current.get("description") or ""
    if row_id and "start_date" not in data:
        payload["start_date"] = current.get("start_date") or ""
    if row_id and "end_date" not in data:
        payload["end_date"] = current.get("end_date") or ""
    if row_id and "status" not in data:
        payload["status"] = current.get("status") or "Devam ediyor"
    if row_id and "budget" not in data:
        payload["budget"] = current.get("budget")
    if row_id and "notes" not in data:
        payload["notes"] = current.get("notes") or ""
    if row_id and "name" not in data:
        payload["name"] = current["name"]
    if row_id:
        return update_record(conn, "projects", row_id, payload, owner_id)
    return insert_record(conn, "projects", payload, owner_id)


def save_task(conn, data, owner_id, row_id=None):
    previous = get_record(conn, "tasks", row_id, owner_id) if row_id else None
    title = clean_text(
        data.get("title", previous.get("title") if previous else ""),
        200,
        required=True,
        label="Başlık",
    )
    project_id = data.get("project_id", previous.get("project_id") if previous else None)
    if not project_id:
        project_id = general_project_id(conn, owner_id)
    else:
        get_record(conn, "projects", int(project_id), owner_id)
        project_id = int(project_id)
    payload = {
        "title": title,
        "description": clean_text(data.get("description", previous.get("description") if previous else ""), 8000),
        "assignee": clean_text(data.get("assignee", previous.get("assignee") if previous else ""), 120),
        "priority": choice(data.get("priority", previous.get("priority") if previous else None), TASK_PRIORITY, "Öncelik", "Normal"),
        "status": choice(data.get("status", previous.get("status") if previous else None), TASK_STATUS, "Durum", "Bekliyor"),
        "start_date": clean_date(data.get("start_date", previous.get("start_date") if previous else "")),
        "due_date": clean_date(data.get("due_date", previous.get("due_date") if previous else "")),
        "repeat": choice(data.get("repeat", previous.get("repeat") if previous else None), TASK_REPEAT, "Tekrar", "Yok"),
        "tag": clean_text(data.get("tag", previous.get("tag") if previous else ""), 40),
        "issue_type": choice(data.get("issue_type", previous.get("issue_type") if previous else None), TASK_TYPE, "Tür", "Görev"),
        "project_id": project_id,
        "note_json": data.get("note_json", previous.get("note_json") if previous else "") or "",
    }
    previous_no = previous.get("issue_no") if previous else None
    previous_project = previous.get("project_id") if previous else None
    if not previous_no or previous_project != project_id:
        payload["issue_no"] = next_issue_no(conn, project_id, owner_id)
    stamp_task_wait(payload, previous)
    if row_id:
        saved = update_record(conn, "tasks", row_id, payload, owner_id)
    else:
        saved = insert_record(conn, "tasks", payload, owner_id)
    return present_task(conn, saved, owner_id)


def move_task(conn, row_id, project_id, owner_id):
    return save_task(conn, {"project_id": project_id}, owner_id, row_id)


def present_invoice(row):
    total, paid = invoice_money(row)
    row = dict(row)
    row["total"] = total
    row["paid"] = paid
    row["remaining"] = round(max(total - paid, 0), 2)
    row["events"] = invoice_events(row)
    return row


def save_invoice(conn, data, owner_id, row_id=None):
    current = get_record(conn, "invoices", row_id, owner_id) if row_id else None
    party = clean_text(data.get("party", current.get("party") if current else ""), 200, required=True, label="Firma / kişi")
    payload = {
        "party": party,
        "kind": choice(data.get("kind", current.get("kind") if current else None), INVOICE_KIND, "Tür", "Gelen"),
        "status": choice(data.get("status", current.get("status") if current else None), INVOICE_STATUS, "Durum", "Ödenmedi"),
        "invoice_no": clean_text(data.get("invoice_no", current.get("invoice_no") if current else ""), 80),
        "description": clean_text(data.get("description", current.get("description") if current else ""), 500),
        "amount": clean_amount(data.get("amount", current.get("amount") if current else None), required=False),
        "invoice_date": clean_date(data.get("invoice_date", current.get("invoice_date") if current else "")),
        "due_date": clean_date(data.get("due_date", current.get("due_date") if current else "")),
        "attachment": str(data.get("attachment", current.get("attachment") if current else "") or "")[:500],
        "currency": clean_text(data.get("currency", current.get("currency") if current else ""), 8) or "TRY",
        "tax_no": clean_text(data.get("tax_no", current.get("tax_no") if current else ""), 20),
        "file_name": clean_text(data.get("file_name", current.get("file_name") if current else ""), 180),
        "source": clean_text(data.get("source", current.get("source") if current else ""), 40),
        "source_key": str(data.get("source_key", current.get("source_key") if current else "") or "")[:180],
    }
    if row_id:
        saved = update_record(conn, "invoices", row_id, payload, owner_id)
    else:
        payload["paid_amount"] = 0
        payload["events_json"] = "[]"
        saved = insert_record(conn, "invoices", payload, owner_id)
    total, paid = invoice_money(saved)
    stored = float(saved.get("paid_amount") or 0)
    if saved["status"] == "Ödendi" and stored < total:
        saved = update_record(conn, "invoices", saved["id"], {"paid_amount": total}, owner_id)
    elif saved["status"] == "Ödenmedi" and stored:
        saved = update_record(conn, "invoices", saved["id"], {"paid_amount": 0}, owner_id)
    return present_invoice(saved)


def _log_invoice(conn, row_id, kind, text, owner_id):
    row = get_record(conn, "invoices", row_id, owner_id)
    events = invoice_events(row)
    events.append({"kind": kind, "at": datetime.now().strftime("%Y-%m-%d %H:%M"), "text": text})
    saved = update_record(conn, "invoices", row_id, {"events_json": json.dumps(events, ensure_ascii=False)}, owner_id)
    return present_invoice(saved)


def collect_invoice(conn, row_id, amount, owner_id):
    row = get_record(conn, "invoices", row_id, owner_id)
    if row["status"] == "İptal":
        raise ValueError("İptal edilmiş faturada tahsilat kaydı açılmaz.")
    total, paid = invoice_money(row)
    remaining = round(total - paid, 2)
    if total <= 0:
        raise ValueError("Önce faturaya tutar yaz.")
    if remaining <= 0:
        raise ValueError("Bu fatura zaten tahsil edilmiş.")
    paid_now = clean_amount(amount, required=True)
    if paid_now <= 0 or paid_now > remaining + 0.001:
        raise ValueError(f"Tutar 0 ile {format_amount(remaining)} arasında olmalı.")
    new_paid = round(paid + paid_now, 2)
    status = "Ödendi" if new_paid >= total - 0.001 else "Kısmi ödendi"
    update_record(conn, "invoices", row_id, {"paid_amount": new_paid, "status": status}, owner_id)
    return _log_invoice(conn, row_id, "payment", f"{format_amount(paid_now)} ₺ tahsil edildi", owner_id)


def cancel_invoice(conn, row_id, owner_id):
    row = get_record(conn, "invoices", row_id, owner_id)
    if row["status"] == "İptal":
        return present_invoice(row)
    update_record(conn, "invoices", row_id, {"status": "İptal"}, owner_id)
    return _log_invoice(conn, row_id, "cancel", "Fatura iptal edildi", owner_id)


def save_offer(conn, data, owner_id, row_id=None):
    current = get_record(conn, "offers", row_id, owner_id) if row_id else None
    project_id = data.get("project_id", current.get("project_id") if current else None)
    if not project_id:
        raise ValueError("Teklif bir projeye bağlanmalı.")
    get_record(conn, "projects", int(project_id), owner_id)
    payload = {
        "project_id": int(project_id),
        "vendor": clean_text(data.get("vendor", current.get("vendor") if current else ""), 160, required=True, label="Satıcı"),
        "title": clean_text(data.get("title", current.get("title") if current else ""), 200),
        "amount": clean_amount(data.get("amount", current.get("amount") if current else None)),
        "offer_date": clean_date(data.get("offer_date", current.get("offer_date") if current else "")),
        "file_path": str(data.get("file_path", current.get("file_path") if current else "") or "")[:500],
        "url": str(data.get("url", current.get("url") if current else "") or "")[:500],
        "pros": clean_text(data.get("pros", current.get("pros") if current else ""), 4000),
        "cons": clean_text(data.get("cons", current.get("cons") if current else ""), 4000),
        "notes": clean_text(data.get("notes", current.get("notes") if current else ""), 4000),
        "source_text": str(data.get("source_text", current.get("source_text") if current else "") or "")[:20000],
    }
    if row_id:
        return update_record(conn, "offers", row_id, payload, owner_id)
    return insert_record(conn, "offers", payload, owner_id)


def delete_project_offers(conn, project_id, owner_id):
    get_record(conn, "projects", project_id, owner_id)
    offers = list_records(conn, "offers", owner_id, equals={"project_id": int(project_id)}, limit=500)["items"]
    for offer in offers:
        delete_record(conn, "offers", offer["id"], owner_id)
    return {"deleted": len(offers)}


def next_talep_number(conn, code):
    prefix = f"{code}-"
    highest = 0
    rows = conn.execute("SELECT number FROM talepler").fetchall()
    for row in rows:
        number = str(row["number"] or "")
        if number.startswith(prefix) and number[len(prefix):].isdigit():
            highest = max(highest, int(number[len(prefix):]))
    return f"{prefix}{highest + 1}"


def _append_talep_note(raw, status, note):
    try:
        notes = json.loads(raw or "[]")
    except json.JSONDecodeError:
        notes = []
    if not isinstance(notes, list):
        notes = []
    notes.append({"status": status, "note": note, "at": datetime.now().strftime("%Y-%m-%d %H:%M")})
    return json.dumps(notes, ensure_ascii=False)


def save_talep(conn, data, row_id=None):
    current = get_record(conn, "talepler", row_id) if row_id else None
    title = clean_text(data.get("title", current.get("title") if current else ""), 200, required=True, label="Başlık")
    code = "".join(ch for ch in str(data.get("target_code") or "TLP").upper() if ch.isalnum())[:12] or "TLP"
    number = clean_text(data.get("number", ""), 40)
    if not number:
        number = current["number"] if current else next_talep_number(conn, code)
    payload = {
        "number": number,
        "title": title,
        "description": clean_text(data.get("description", current.get("description") if current else ""), 8000),
        "work_code": clean_text(data.get("work_code", current.get("work_code") if current else ""), 40),
        "request_code": clean_text(data.get("request_code", current.get("request_code") if current else ""), 16),
        "source_name": clean_text(data.get("source_name", current.get("source_name") if current else ""), 120),
        "target_name": clean_text(data.get("target_name", current.get("target_name") if current else ""), 120),
        "author_name": clean_text(data.get("author_name", current.get("author_name") if current else ""), 120),
        "author_email": clean_text(data.get("author_email", current.get("author_email") if current else ""), 160),
        "author_id": data.get("author_id", current.get("author_id") if current else None),
        "assignee_id": data.get("assignee_id", current.get("assignee_id") if current else None),
        "assignee_name": clean_text(data.get("assignee_name", current.get("assignee_name") if current else ""), 120),
        "priority": choice(data.get("priority", current.get("priority") if current else None), TASK_PRIORITY, "Öncelik", "Normal"),
        "due_date": clean_date(data.get("due_date", current.get("due_date") if current else "")),
        "status": choice(data.get("status", current.get("status") if current else None), TALEP_STATUS, "Durum", "Açık"),
        "scope": choice(data.get("scope") or (current.get("scope") if current else "") or "İç", ("İç", "Dış"), "Kapsam", "İç"),
        "file_name": clean_text(data.get("file_name", current.get("file_name") if current else ""), 180),
        "notes_json": data.get("notes_json", current.get("notes_json") if current else "[]") or "[]",
        "files_json": data.get("files_json", current.get("files_json") if current else "[]") or "[]",
    }
    if row_id:
        return update_record(conn, "talepler", row_id, payload)
    return insert_record(conn, "talepler", payload)


def take_talep(conn, row_id, actor_id, actor_name):
    row = get_record(conn, "talepler", row_id)
    if row["status"] in ("Tamamlandı", "Reddedildi"):
        raise ValueError("Kapanmış talep üzerine alınamaz.")
    name = clean_text(actor_name, 120, required=True, label="Ad")
    data = {"assignee_id": int(actor_id), "assignee_name": name}
    if row["status"] == "Açık":
        data["status"] = "Üzerinde"
    data["notes_json"] = _append_talep_note(row.get("notes_json"), "Atama", f"{name} talebi üzerine aldı.")
    return update_record(conn, "talepler", row_id, data)


def assign_talep(conn, row_id, assignee_id, assignee_name, actor_name):
    row = get_record(conn, "talepler", row_id)
    if row["status"] in ("Tamamlandı", "Reddedildi"):
        raise ValueError("Kapanmış talep atanamaz.")
    name = clean_text(assignee_name, 120, required=True, label="Kişi")
    actor = clean_text(actor_name, 120) or "Bir kullanıcı"
    return update_record(conn, "talepler", row_id, {
        "assignee_id": int(assignee_id),
        "assignee_name": name,
        "notes_json": _append_talep_note(row.get("notes_json"), "Atama", f"{actor} talebi {name} kişisine atadı."),
    })


def set_talep_status(conn, row_id, status, note, actor_name):
    row = get_record(conn, "talepler", row_id)
    status = choice(status, TALEP_STATUS, "Durum")
    actor = clean_text(actor_name, 120)
    text = clean_text(note, 500) or f"Durum {status} oldu."
    if actor:
        text = f"{actor}: {text}"
    return update_record(conn, "talepler", row_id, {
        "status": status,
        "notes_json": _append_talep_note(row.get("notes_json"), status, text),
    })


def save_contact(conn, data, owner_id, row_id=None):
    current = get_record(conn, "contacts", row_id, owner_id) if row_id else None
    payload = {
        "name": clean_text(data.get("name", current.get("name") if current else ""), 160, required=True, label="Ad"),
        "contact_person": clean_text(data.get("contact_person", current.get("contact_person") if current else ""), 160),
        "phone": clean_text(data.get("phone", current.get("phone") if current else ""), 40),
        "email": clean_text(data.get("email", current.get("email") if current else ""), 160),
        "tax_no": clean_text(data.get("tax_no", current.get("tax_no") if current else ""), 20),
        "address": clean_text(data.get("address", current.get("address") if current else ""), 500),
        "notes": clean_text(data.get("notes", current.get("notes") if current else ""), 2000),
        "record_kind": choice(data.get("record_kind", current.get("record_kind") if current else None), CONTACT_KIND, "Kayıt", "Firma"),
        "scope": choice(data.get("scope", current.get("scope") if current else None) or "Dış", CONTACT_SCOPE, "Kapsam", "Dış"),
        "extension": clean_text(data.get("extension", current.get("extension") if current else ""), 20),
    }
    if row_id:
        return update_record(conn, "contacts", row_id, payload, owner_id)
    return insert_record(conn, "contacts", payload, owner_id)


def save_reminder(conn, data, owner_id, row_id=None):
    current = get_record(conn, "reminders", row_id, owner_id) if row_id else None
    payload = {
        "title": clean_text(data.get("title", current.get("title") if current else ""), 200, required=True, label="Başlık"),
        "description": clean_text(data.get("description", current.get("description") if current else ""), 2000),
        "remind_date": clean_date(data.get("remind_date", current.get("remind_date") if current else ""), required=not row_id, label="Tarih"),
        "remind_time": clean_text(data.get("remind_time", current.get("remind_time") if current else ""), 5),
        "repeat": choice(data.get("repeat", current.get("repeat") if current else None), TASK_REPEAT, "Tekrar", "Yok"),
        "status": choice(data.get("status", current.get("status") if current else None), REMINDER_STATUS, "Durum", "Aktif"),
    }
    clock = payload["remind_time"]
    if clock and not (len(clock) == 5 and clock[2] == ":" and clock[:2].isdigit() and clock[3:].isdigit()):
        raise ValueError("Saat HH:MM biçiminde olmalı.")
    if row_id and "remind_date" not in data:
        payload["remind_date"] = current.get("remind_date") or ""
    if row_id:
        return update_record(conn, "reminders", row_id, payload, owner_id)
    return insert_record(conn, "reminders", payload, owner_id)


def save_transaction(conn, data, owner_id, row_id=None):
    current = get_record(conn, "transactions", row_id, owner_id) if row_id else None
    payload = {
        "kind": choice(data.get("kind", current.get("kind") if current else None), LEDGER_KIND, "Tür"),
        "category": clean_text(data.get("category", current.get("category") if current else ""), 40, required=True, label="Kategori"),
        "description": clean_text(data.get("description", current.get("description") if current else ""), 300),
        "amount": clean_amount(data.get("amount", current.get("amount") if current else None), required=True),
        "trans_date": clean_date(data.get("trans_date", current.get("trans_date") if current else ""), required=not row_id, label="Tarih"),
        "party": clean_text(data.get("party", current.get("party") if current else ""), 160),
        "payment_method": choice(data.get("payment_method", current.get("payment_method") if current else None), PAY_METHOD, "Ödeme", "Diğer"),
        "docs_json": data.get("docs_json", current.get("docs_json") if current else "[]") or "[]",
    }
    if payload["amount"] <= 0:
        raise ValueError("Tutar gerekli.")
    if row_id and "trans_date" not in data:
        payload["trans_date"] = current.get("trans_date") or ""
    if row_id:
        saved = update_record(conn, "transactions", row_id, payload, owner_id)
    else:
        saved = insert_record(conn, "transactions", payload, owner_id)
    from app.logic import remember_ledger_category
    remember_ledger_category(conn, payload["kind"], payload["category"])
    return saved


def save_report(conn, data, owner_id, row_id=None):
    current = get_record(conn, "reports", row_id, owner_id) if row_id else None
    payload = {
        "invoice_id": data.get("invoice_id", current.get("invoice_id") if current else None),
        "title": clean_text(data.get("title", current.get("title") if current else ""), 200, required=True, label="Başlık"),
        "invoice_no": clean_text(data.get("invoice_no", current.get("invoice_no") if current else ""), 80),
        "amount": clean_amount(data.get("amount", current.get("amount") if current else None)),
        "reason": clean_text(data.get("reason", current.get("reason") if current else ""), 4000),
        "saved_path": str(data.get("saved_path", current.get("saved_path") if current else "") or "")[:500],
    }
    if row_id:
        return update_record(conn, "reports", row_id, payload, owner_id)
    return insert_record(conn, "reports", payload, owner_id)


def dashboard(conn, owner_id):
    def grouped(table, column):
        where = ""
        params = []
        if table != "talepler" and owner_id is not None:
            where = " WHERE owner_id=?"
            params.append(owner_id)
        rows = conn.execute(
            f"SELECT COALESCE({column}, '') AS key, COUNT(*) AS n FROM {table}{where} GROUP BY 1",
            params,
        ).fetchall()
        return {row["key"] or "(boş)": int(row["n"]) for row in rows}

    today = date.today().isoformat()
    month = today[:7]
    owner_sql = " AND owner_id=?" if owner_id is not None else ""
    owner_params = [owner_id] if owner_id is not None else []
    money = {}
    for kind in LEDGER_KIND:
        row = conn.execute(
            f"SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE kind=? AND trans_date LIKE ?{owner_sql}",
            [kind, month + "%", *owner_params],
        ).fetchone()
        money[kind] = round(float(row["total"] or 0), 2)
    open_invoices = conn.execute(
        f"SELECT COUNT(*) AS n FROM invoices WHERE status IN ('Ödenmedi', 'Kısmi ödendi'){owner_sql}",
        owner_params,
    ).fetchone()["n"]
    reminders = conn.execute(
        f"SELECT COUNT(*) AS n FROM reminders WHERE status='Aktif' AND remind_date=?{owner_sql}",
        [today, *owner_params],
    ).fetchone()["n"]
    return {
        "tasks": grouped("tasks", "status"),
        "projects": grouped("projects", "status"),
        "invoices": grouped("invoices", "status"),
        "open_invoices": int(open_invoices),
        "reminders_today": int(reminders),
        "talepler": grouped("talepler", "status"),
        "month": month,
        "cash": money,
    }
