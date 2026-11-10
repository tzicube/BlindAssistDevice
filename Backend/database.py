import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "app.db"
DEFAULT_LEGACY_PLACES_PATH = BASE_DIR / "data" / "savedPlaces.json"


class BackendDatabase:
    """SQLite persistence for the BlindAssist backend."""

    def __init__(
        self,
        db_path: Path = DEFAULT_DB_PATH,
        legacy_places_path: Path | None = DEFAULT_LEGACY_PLACES_PATH,
    ):
        self.db_path = Path(db_path)
        self.legacy_places_path = (
            Path(legacy_places_path) if legacy_places_path is not None else None
        )

    @contextmanager
    def connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self):
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS saved_places (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    address TEXT NOT NULL DEFAULT '',
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    x_percent REAL,
                    y_percent REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS latest_location (
                    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    address TEXT NOT NULL DEFAULT '',
                    heading REAL,
                    direction TEXT,
                    battery REAL,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            saved_place_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(saved_places)")
            }
            if "address" not in saved_place_columns:
                connection.execute(
                    "ALTER TABLE saved_places "
                    "ADD COLUMN address TEXT NOT NULL DEFAULT ''"
                )

            latest_location_columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(latest_location)")
            }
            telemetry_columns = {
                "address": "TEXT NOT NULL DEFAULT ''",
                "heading": "REAL",
                "direction": "TEXT",
                "battery": "REAL",
            }
            for column, definition in telemetry_columns.items():
                if column not in latest_location_columns:
                    connection.execute(
                        f"ALTER TABLE latest_location ADD COLUMN {column} {definition}"
                    )
        self._migrate_legacy_places_once()

    def _migrate_legacy_places_once(self):
        migration_key = "saved_places_json_migrated_v1"
        with self.connect() as connection:
            migrated = connection.execute(
                "SELECT 1 FROM app_meta WHERE key = ?",
                (migration_key,),
            ).fetchone()
            if migrated:
                return

            legacy_places = []
            path = self.legacy_places_path
            if path is not None and path.exists():
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    parsed = json.loads(content)
                    if not isinstance(parsed, list):
                        raise ValueError("Legacy savedPlaces.json must contain a list")
                    legacy_places = parsed

            for place in legacy_places:
                if not isinstance(place, dict):
                    continue
                name = str(place.get("name") or "").strip()
                if not name:
                    continue
                try:
                    latitude = float(place.get("lat", place.get("latitude")))
                    longitude = float(place.get("lng", place.get("longitude")))
                except (TypeError, ValueError):
                    continue

                legacy_id = place.get("id")
                address = str(place.get("address") or "").strip()
                x_percent = _optional_float(place.get("xPercent"))
                y_percent = _optional_float(place.get("yPercent"))
                if isinstance(legacy_id, int):
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO saved_places
                            (id, name, address, latitude, longitude, x_percent, y_percent)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            legacy_id,
                            name,
                            address,
                            latitude,
                            longitude,
                            x_percent,
                            y_percent,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        INSERT INTO saved_places
                            (name, address, latitude, longitude, x_percent, y_percent)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (name, address, latitude, longitude, x_percent, y_percent),
                    )

            connection.execute(
                "INSERT INTO app_meta (key, value) VALUES (?, ?)",
                (migration_key, "done"),
            )

    def list_places(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, name, address, latitude, longitude, x_percent, y_percent
                FROM saved_places
                ORDER BY id
                """
            ).fetchall()
        return [_place_from_row(row) for row in rows]

    def create_place(
        self,
        *,
        name: str,
        latitude: float,
        longitude: float,
        x_percent: float | None,
        y_percent: float | None,
        address: str = "",
    ) -> dict:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO saved_places
                    (name, address, latitude, longitude, x_percent, y_percent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, address, latitude, longitude, x_percent, y_percent),
            )
            row = connection.execute(
                """
                SELECT id, name, address, latitude, longitude, x_percent, y_percent
                FROM saved_places
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
        return _place_from_row(row)

    def delete_place(self, place_id: int) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM saved_places WHERE id = ?",
                (place_id,),
            )
        return cursor.rowcount > 0

    def get_latest_location(self) -> dict | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT latitude, longitude, address, heading, direction,
                       battery, source, updated_at
                FROM latest_location
                WHERE singleton_id = 1
                """
            ).fetchone()
        if row is None:
            return None
        return {
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "address": row["address"] or "",
            "heading": row["heading"],
            "direction": row["direction"],
            "battery": row["battery"],
            "source": row["source"],
            "updatedAt": row["updated_at"],
        }

    def set_latest_location(
        self,
        *,
        latitude: float,
        longitude: float,
        source: str,
        updated_at: str,
        address: str = "",
        heading: float | None = None,
        direction: str | None = None,
        battery: float | None = None,
    ) -> dict:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO latest_location
                    (singleton_id, latitude, longitude, address, heading,
                     direction, battery, source, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(singleton_id) DO UPDATE SET
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    address = excluded.address,
                    heading = excluded.heading,
                    direction = excluded.direction,
                    battery = excluded.battery,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (
                    latitude,
                    longitude,
                    address,
                    heading,
                    direction,
                    battery,
                    source,
                    updated_at,
                ),
            )
        return {
            "latitude": latitude,
            "longitude": longitude,
            "address": address,
            "heading": heading,
            "direction": direction,
            "battery": battery,
            "source": source,
            "updatedAt": updated_at,
        }

    def clear_latest_location(self):
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM latest_location WHERE singleton_id = 1"
            )


def _optional_float(value) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _place_from_row(row: sqlite3.Row) -> dict:
    place = {
        "id": row["id"],
        "name": row["name"],
        "address": row["address"] or "",
        "lat": row["latitude"],
        "lng": row["longitude"],
    }
    if row["x_percent"] is not None:
        place["xPercent"] = row["x_percent"]
    if row["y_percent"] is not None:
        place["yPercent"] = row["y_percent"]
    return place

