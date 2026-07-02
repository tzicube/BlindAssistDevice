from typing import Any

from Auth import common


def create_account(payload: dict[str, Any]) -> dict[str, Any]:
    email = common.normalize_email(payload.get("email"))
    password = common.normalize_password(payload.get("password"))

    requested_user_code = str(payload.get("user_code") or "").strip()

    conn = common.open_connection()
    try:
        cursor = conn.cursor()

        existing_email = cursor.execute(
            "SELECT 1 FROM accounts WHERE email = ?",
            (email,),
        ).fetchone()
        if existing_email:
            raise ValueError("Email da ton tai.")

        if requested_user_code:
            user_code = common.normalize_user_code(requested_user_code)
            existing_user_code = cursor.execute(
                "SELECT 1 FROM accounts WHERE user_code = ?",
                (user_code,),
            ).fetchone()
            if existing_user_code:
                raise ValueError("Ma nguoi dung da ton tai.")
        else:
            user_code = common.generate_unique_user_code(cursor, email)

        password_hash = common.hash_password(password)

        cursor.execute(
            """
            INSERT INTO accounts (email, user_code, password)
            VALUES (?, ?, ?)
            """,
            (email, user_code, password_hash),
        )
        account_id = cursor.lastrowid
        conn.commit()

        row = cursor.execute(
            """
            SELECT id, email, user_code, created_at, updated_at
            FROM accounts
            WHERE id = ?
            """,
            (account_id,),
        ).fetchone()
        account = common.account_to_dict(row)

        return {
            "status": True,
            "message": "Dang ky thanh cong.",
            "account": account,
        }
    finally:
        conn.close()
