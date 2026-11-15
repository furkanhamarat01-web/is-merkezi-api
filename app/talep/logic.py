import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime

ADMIN_EMAIL = "furkan.hamarat01@gmail.com"
ADMIN_ROLE = "Yönetici"
ROLES = ("Kullanıcı", "Sorumlu", "İzleyici")
PRIORITIES = ("Düşük", "Normal", "Yüksek", "Acil")
STATUSES = ("Açık", "Üzerinde", "Beklemede", "Tamamlandı", "Reddedildi")
NOTE_STATUSES = ("Beklemede", "Tamamlandı", "Reddedildi")
LOG_EVENTS = ("Giriş", "Çıkış", "Başarısız")
FILE_EXT = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE = 20 * 1024 * 1024


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return salt.hex() + ":" + digest.hex()


def check_password(password, stored):
    try:
        salt_hex, digest_hex = str(stored).split(":", 1)
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    except (ValueError, TypeError):
        return False
    return secrets.compare_digest(digest.hex(), digest_hex)


def new_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def totp_codes(secret, moment=None, window=1):
    key = base64.b32decode(secret.upper() + "=" * ((8 - len(secret) % 8) % 8), casefold=True)
    counter = int((time.time() if moment is None else moment) // 30)
    codes = []
    for offset in range(-window, window + 1):
        digest = hmac.new(key, (counter + offset).to_bytes(8, "big"), hashlib.sha1).digest()
        start = digest[-1] & 0x0F
        number = int.from_bytes(digest[start:start + 4], "big") & 0x7FFFFFFF
        codes.append(f"{number % 1_000_000:06d}")
    return codes


def totp_ok(secret, code):
    typed = "".join(ch for ch in str(code or "") if ch.isdigit())
    if len(typed) != 6:
        return False
    return typed in totp_codes(secret)


def clean_code(value):
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())[:8]


def clean_request_code(value):
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum() or ch == "-")[:16]


def clean_email(value):
    return " ".join(str(value or "").split()).casefold()


def clean_username(value):
    return "".join(ch for ch in str(value or "").casefold() if ch.isalnum() or ch in "._-")[:32]


def fold_ascii(value):
    return str(value or "").translate(str.maketrans("çğıöşüÇĞİÖŞÜıI", "cgiosuCGIOSUiI"))


def code_from_topic(topic, taken=()):
    words = []
    for word in fold_ascii(topic).split():
        letters = "".join(ch for ch in word if ch.isalnum())
        if letters:
            words.append(letters)
    if not words:
        return ""
    if len(words) == 1:
        base = words[0][:4].upper()
    else:
        base = "".join(word[0] for word in words)[:8].upper()
    if len(base) < 2:
        base = words[0][:4].upper()
    code = base[:8]
    number = 2
    used = {str(item).upper() for item in taken}
    while code in used:
        code = f"{base[:6]}{number}"[:8]
        number += 1
    return code


def note_list(raw):
    try:
        data = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    notes = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = " ".join(str(item.get("note") or "").split())
        if text:
            notes.append({
                "status": str(item.get("status") or ""),
                "note": text[:1000],
                "at": str(item.get("at") or ""),
            })
    return notes[-30:]


def public_user(row):
    if row is None:
        return None
    data = dict(row)
    data.pop("password", None)
    return data
