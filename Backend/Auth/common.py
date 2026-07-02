import hashlib
import hmac
import re
import secrets
import sqlite3
from typing import Any

import db

EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)
USER_CODE_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
MIN_PASSWORD_LENGTH = 8
PBKDF2_ITERATIONS = 120_000


def open_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def normalize_email(raw_email: Any) -> str:
    email = str(raw_email or "").strip().lower()
    if not email:
        raise ValueError("Email khong duoc de trong.")
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Email khong dung dinh dang.")
    return email


def normalize_user_code(raw_user_code: Any) -> str:
    user_code = str(raw_user_code or "").strip().lower()
    if not user_code:
        raise ValueError("Ma nguoi dung khong duoc de trong.")
    if not USER_CODE_PATTERN.fullmatch(user_code):
        raise ValueError("Ma nguoi dung chi duoc gom 3-32 ky tu: chu, so, gach ngang hoac underscore.")
    return user_code


def normalize_password(raw_password: Any) -> str:
    password = str(raw_password or "")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Mat khau phai co it nhat {MIN_PASSWORD_LENGTH} ky tu.")
    return password


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_value: str) -> bool:
    try:
        salt, expected_digest = stored_value.split("$", 1)
    except ValueError:
        return hmac.compare_digest(password, stored_value)

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return hmac.compare_digest(candidate_digest.hex(), expected_digest)


def make_user_code_seed(email: str) -> str:
    local_part = email.split("@", 1)[0].lower()
    cleaned = re.sub(r"[^a-z0-9]+", "", local_part)
    return cleaned[:12] or "user"


def generate_unique_user_code(cursor: sqlite3.Cursor, email: str) -> str:
    seed = make_user_code_seed(email)
    while True:
        candidate = f"{seed}-{secrets.token_hex(3)}"
        exists = cursor.execute(
            "SELECT 1 FROM accounts WHERE user_code = ?",
            (candidate,),
        ).fetchone()
        if not exists:
            return candidate


def account_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "user_code": row["user_code"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
