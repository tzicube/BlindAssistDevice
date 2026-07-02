from pathlib import Path
import sqlite3

# Lấy đường dẫn folder Backend hiện tại
BASE_DIR = Path(__file__).resolve().parent

# File database SQLite
DB_PATH = BASE_DIR / "app.db"


def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Bật foreign key cho SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Bảng accounts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        email TEXT UNIQUE NOT NULL,
        user_code TEXT UNIQUE NOT NULL,

        password TEXT NOT NULL,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Bảng saved_locations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        account_id INTEGER NOT NULL,

        name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (account_id) REFERENCES accounts(id)
    );
    """)

    conn.commit()
    conn.close()

    print(f"Database created successfully: {DB_PATH}")


if __name__ == "__main__":
    create_tables()