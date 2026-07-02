from typing import Any

from Auth import common


def authenticate_account(payload: dict[str, Any]) -> dict[str, Any]:
    identifier = str(payload.get("identifier") or "").strip()
    password = str(payload.get("password") or "")

    if not identifier:
        raise ValueError("Email hoac ma nguoi dung khong duoc de trong.")
    if not password:
        raise ValueError("Mat khau khong duoc de trong.")

    conn = common.open_connection()
    try:
        cursor = conn.cursor()
        normalized_identifier = identifier.lower()

        row = cursor.execute(
            """
            SELECT id, email, user_code, password, created_at, updated_at
            FROM accounts
            WHERE lower(email) = ? OR lower(user_code) = ?
            LIMIT 1
            """,
            (normalized_identifier, normalized_identifier),
        ).fetchone()

        if row is None or not common.verify_password(password, row["password"]):
            raise ValueError("Thong tin dang nhap khong chinh xac.")

        account = common.account_to_dict(row)
        return {
            "status": True,
            "message": "Dang nhap thanh cong.",
            "account": account,
        }
    finally:
        conn.close()
