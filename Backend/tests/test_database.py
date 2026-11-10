import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from Backend.database import BackendDatabase


class BackendDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.db_path = root / "test.db"
        self.legacy_path = root / "savedPlaces.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def database(self):
        return BackendDatabase(self.db_path, self.legacy_path)

    def test_migrates_legacy_json_only_once(self):
        self.legacy_path.write_text(
            json.dumps(
                [
                    {
                        "id": 42,
                        "name": "Home",
                        "lat": 24.99,
                        "lng": 121.34,
                        "xPercent": 0.25,
                        "yPercent": 0.5,
                    }
                ]
            ),
            encoding="utf-8",
        )
        database = self.database()
        database.initialize()
        database.initialize()

        self.assertEqual(
            database.list_places(),
            [
                {
                    "id": 42,
                    "name": "Home",
                    "address": "",
                    "lat": 24.99,
                    "lng": 121.34,
                    "aliases": [],
                    "xPercent": 0.25,
                    "yPercent": 0.5,
                }
            ],
        )

    def test_create_list_and_delete_place(self):
        database = self.database()
        database.initialize()
        place = database.create_place(
            name="School",
            latitude=24.98,
            longitude=121.35,
            x_percent=0.3,
            y_percent=0.7,
            address="1 School Road",
        )

        self.assertIsInstance(place["id"], int)
        self.assertEqual(place["address"], "1 School Road")
        self.assertEqual(database.list_places(), [place])
        self.assertTrue(database.delete_place(place["id"]))
        self.assertFalse(database.delete_place(place["id"]))
        self.assertEqual(database.list_places(), [])

    def test_stores_replaces_and_cascades_place_aliases(self):
        database = self.database()
        database.initialize()
        place = database.create_place(
            name="Home",
            latitude=24.98,
            longitude=121.35,
            x_percent=None,
            y_percent=None,
            address="1 Home Road",
            aliases=["家", "回家", "家"],
        )

        self.assertEqual(["家", "回家"], place["aliases"])

        updated = database.replace_place_aliases(
            place["id"],
            ["my home", "HOME BASE"],
        )
        self.assertEqual(["my home", "HOME BASE"], updated["aliases"])

        self.assertTrue(database.delete_place(place["id"]))
        connection = sqlite3.connect(self.db_path)
        try:
            remaining = connection.execute(
                "SELECT COUNT(*) FROM place_aliases WHERE place_id = ?",
                (place["id"],),
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(0, remaining)

    def test_replace_aliases_returns_none_for_unknown_place(self):
        database = self.database()
        database.initialize()
        self.assertIsNone(database.replace_place_aliases(999, ["missing"]))

    def test_adds_address_column_to_existing_database(self):
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute(
                """
                CREATE TABLE saved_places (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    x_percent REAL,
                    y_percent REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                INSERT INTO saved_places (name, latitude, longitude)
                VALUES ('Existing place', 24.99, 121.34)
                """
            )
            connection.commit()
        finally:
            connection.close()

        database = self.database()
        database.initialize()
        self.assertEqual(database.list_places()[0]["address"], "")

    def test_latest_location_survives_new_database_instance(self):
        database = self.database()
        database.initialize()
        expected = database.set_latest_location(
            latitude=24.990782,
            longitude=121.346525,
            address="桃園市中壢區中大路300號",
            heading=45.0,
            direction="NE",
            battery=82.0,
            source="test",
            updated_at="2026-11-01T10:00:00+08:00",
        )

        reopened = self.database()
        reopened.initialize()
        self.assertEqual(reopened.get_latest_location(), expected)
        reopened.clear_latest_location()
        self.assertIsNone(reopened.get_latest_location())

    def test_migrates_existing_latest_location_table_for_telemetry(self):
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute(
                """
                CREATE TABLE latest_location (
                    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    source TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO latest_location
                    (singleton_id, latitude, longitude, source, updated_at)
                VALUES (1, 24.99, 121.34, 'legacy-esp', '2026-11-01T10:00:00+08:00')
                """
            )
            connection.commit()
        finally:
            connection.close()

        database = self.database()
        database.initialize()
        location = database.get_latest_location()

        self.assertEqual(location["address"], "")
        self.assertIsNone(location["heading"])
        self.assertIsNone(location["direction"])
        self.assertIsNone(location["battery"])


if __name__ == "__main__":
    unittest.main()
