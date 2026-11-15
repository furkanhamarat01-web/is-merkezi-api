import json
from datetime import date, datetime, timedelta, timezone

LEDGER_PRESETS = {
    "Gelir": ["Satış", "Hizmet", "Tahsilat", "Kira geliri", "Faiz", "Diğer gelir"],
    "Gider": ["Kira", "Maaş", "Fatura", "Vergi", "Market", "Ulaşım", "Ofis", "Bakım", "Diğer gider"],
}


def fold(value):
    text = str(value or "").replace("\u0307", "")
    text = text.translate(str.maketrans({
        "İ": "i", "I": "i", "ı": "i",
        "Ş": "s", "ş": "s",
        "Ğ": "g", "ğ": "g",
        "Ü": "u", "ü": "u",
        "Ö": "o", "ö": "o",
        "Ç": "c", "ç": "c",
    }))
    return text.casefold()


def parse_day(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def parse_stamp(value, utc=False):
    text = str(value or "").strip()
    if not text:
        return None
    parsed = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(text[:19], fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        day = parse_day(text[:10])
        return datetime(day.year, day.month, day.day) if day else None
    if utc:
        return parsed.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
    return parsed


def project_key(name, taken):
    letters = "".join(ch for ch in str(name or "").upper() if ch.isalnum())
    base = (letters[:4] or "PRJ")[:4]
    candidate = base
    number = 2
    while candidate in taken:
        candidate = f"{base[:3]}{number}"
        number += 1
    return candidate


def clean_text(value, limit=500, required=False, label="Alan"):
    text = " ".join(str(value or "").split())
    if required and not text:
        raise ValueError(f"{label} gerekli.")
    return text[:limit]


def clean_date(value, required=False, label="Tarih"):
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValueError(f"{label} gerekli.")
        return ""
    if parse_day(text) is None or len(text) < 10:
        raise ValueError("Tarih YYYY-AA-GG biçiminde olmalı.")
    return text[:10]


def clean_amount(value, required=False):
    if value is None or value == "":
        if required:
            raise ValueError("Tutar gerekli.")
        return None
    try:
        amount = round(float(value), 2)
    except (TypeError, ValueError) as exc:
        raise ValueError("Tutar sayı olmalı.") from exc
    if amount < 0:
        raise ValueError("Tutar negatif olamaz.")
    return amount


def choice(value, allowed, label, default=None):
    text = str(value or "").strip()
    if not text:
        if default is not None:
            return default
        raise ValueError(f"{label} gerekli.")
    if text not in allowed:
        raise ValueError(f"{label} geçersiz.")
    return text


def invoice_money(row):
    try:
        total = float(row.get("amount") or 0)
    except (TypeError, ValueError):
        total = 0.0
    try:
        paid = float(row.get("paid_amount") or 0)
    except (TypeError, ValueError):
        paid = 0.0
    status = row.get("status") or ""
    if status == "Ödendi":
        paid = max(paid, total)
    elif status in ("Ödenmedi", "İptal"):
        paid = 0.0
    if total:
        paid = min(max(paid, 0.0), total)
    return round(total, 2), round(max(paid, 0.0), 2)


def invoice_events(row):
    try:
        data = json.loads(row.get("events_json") or "[]")
    except json.JSONDecodeError:
        return []
    return [item for item in data if isinstance(item, dict)]


def format_amount(value):
    whole, _, frac = f"{float(value):.2f}".partition(".")
    parts = []
    while whole:
        parts.append(whole[-3:])
        whole = whole[:-3]
    return ".".join(reversed(parts)) + "," + frac


def task_waiting_since(row):
    if not row:
        return None
    if row.get("waiting_since"):
        return parse_stamp(row["waiting_since"])
    if row.get("created_at"):
        return parse_stamp(row["created_at"], utc=True)
    return None


def stamp_task_wait(data, previous):
    status = data.get("status") or "Bekliyor"
    now = datetime.now().replace(microsecond=0)
    if status in ("Tamamlandı", "İptal"):
        data["waiting_since"] = ""
        data["sla_next"] = ""
        return
    if status != "Bekliyor":
        start = task_waiting_since(previous) if previous is not None else None
        if start is not None and now >= start + timedelta(hours=24):
            data["waiting_since"] = start.strftime("%Y-%m-%d %H:%M:%S")
            previous_next = previous.get("sla_next") if previous else ""
            data["sla_next"] = previous_next or (start + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            return
        data["waiting_since"] = ""
        data["sla_next"] = ""
        return
    if previous is not None and (previous.get("status") or "Bekliyor") == "Bekliyor":
        if previous.get("waiting_since"):
            data["waiting_since"] = previous["waiting_since"]
        if previous.get("sla_next"):
            data["sla_next"] = previous["sla_next"]
        return
    data["waiting_since"] = now.strftime("%Y-%m-%d %H:%M:%S")
    data["sla_next"] = (now + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")


def sla_breached(row):
    if (row.get("status") or "") in ("Tamamlandı", "İptal"):
        return False
    start = task_waiting_since(row)
    return start is not None and datetime.now() >= start + timedelta(hours=24)


def get_setting(conn, key, default=""):
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if row is None or row["value"] is None:
        return default
    return row["value"]


def set_setting(conn, key, value):
    conn.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _ledger_hidden(conn, kind):
    chosen = kind if kind in LEDGER_PRESETS else "Gider"
    try:
        hidden = json.loads(get_setting(conn, "ledger_hidden_categories", "") or "{}")
    except json.JSONDecodeError:
        hidden = {}
    if not isinstance(hidden, dict):
        hidden = {}
    blocked = {fold(item) for item in hidden.get(chosen, []) if isinstance(item, str)}
    return chosen, blocked, hidden


def ledger_category_names(conn, kind, owner_id=None):
    chosen, blocked, _hidden = _ledger_hidden(conn, kind)
    names = []
    seen = set()

    def add(name):
        text = " ".join(str(name or "").split())[:40]
        key = fold(text)
        if not text or key in seen or key in blocked:
            return
        seen.add(key)
        names.append(text)

    for name in LEDGER_PRESETS[chosen]:
        add(name)
    try:
        saved = json.loads(get_setting(conn, "ledger_categories", "") or "{}")
    except json.JSONDecodeError:
        saved = {}
    if isinstance(saved, dict):
        for name in saved.get(chosen, []):
            add(name)
    if owner_id is None:
        rows = conn.execute("SELECT category, kind FROM transactions").fetchall()
    else:
        rows = conn.execute(
            "SELECT category, kind FROM transactions WHERE owner_id=?",
            (owner_id,),
        ).fetchall()
    for row in rows:
        if (row["kind"] or "") == chosen:
            add(row["category"])
    return names


def remember_ledger_category(conn, kind, name):
    chosen, _blocked, hidden = _ledger_hidden(conn, kind)
    text = " ".join(str(name or "").split())[:40]
    if not text:
        return
    hidden[chosen] = [item for item in hidden.get(chosen, []) if isinstance(item, str) and fold(item) != fold(text)]
    set_setting(conn, "ledger_hidden_categories", json.dumps(hidden, ensure_ascii=False))
    if fold(text) in {fold(item) for item in LEDGER_PRESETS[chosen]}:
        return
    try:
        saved = json.loads(get_setting(conn, "ledger_categories", "") or "{}")
    except json.JSONDecodeError:
        saved = {}
    if not isinstance(saved, dict):
        saved = {}
    current = [item for item in saved.get(chosen, []) if isinstance(item, str)]
    if fold(text) not in {fold(item) for item in current}:
        current.append(text)
    saved[chosen] = current[:40]
    set_setting(conn, "ledger_categories", json.dumps(saved, ensure_ascii=False))


def forget_ledger_category(conn, kind, name):
    chosen, _blocked, hidden = _ledger_hidden(conn, kind)
    text = " ".join(str(name or "").split())[:40]
    if not text:
        return
    try:
        saved = json.loads(get_setting(conn, "ledger_categories", "") or "{}")
    except json.JSONDecodeError:
        saved = {}
    if not isinstance(saved, dict):
        saved = {}
    saved[chosen] = [item for item in saved.get(chosen, []) if isinstance(item, str) and fold(item) != fold(text)][:40]
    set_setting(conn, "ledger_categories", json.dumps(saved, ensure_ascii=False))
    blocked = [item for item in hidden.get(chosen, []) if isinstance(item, str) and fold(item) != fold(text)]
    blocked.append(text)
    hidden[chosen] = blocked[:80]
    set_setting(conn, "ledger_hidden_categories", json.dumps(hidden, ensure_ascii=False))
