import sqlite3
import tempfile
import unittest
from pathlib import Path

from database import db_manager as db
from config import DeviceStatus


class DeviceOrderingDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "ordering.db")

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.tmp.cleanup()

    def _create_old_schema_database(self):
        conn = sqlite3.connect(db.DB_PATH)
        try:
            conn.executescript(
                """
                CREATE TABLE device_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT (datetime('now', 'localtime'))
                );
                CREATE TABLE devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    device_type_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'idle',
                    created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (device_type_id) REFERENCES device_types(id)
                );
                CREATE TABLE sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    timer_mode TEXT NOT NULL DEFAULT 'freeplay',
                    countdown_seconds INTEGER NOT NULL DEFAULT 0,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    pause_duration INTEGER NOT NULL DEFAULT 0,
                    total_seconds INTEGER,
                    paid INTEGER NOT NULL DEFAULT 0,
                    payment_method TEXT NOT NULL DEFAULT '',
                    note TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at DATETIME DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (device_id) REFERENCES devices(id)
                );
                CREATE TABLE pause_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    pause_start DATETIME NOT NULL,
                    pause_end DATETIME,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );
                INSERT INTO device_types (id, name) VALUES (1, '小包'), (2, '大包');
                INSERT INTO devices (id, name, device_type_id, status) VALUES
                    (1, '奥特曼包厢', 2, 'active'),
                    (2, '小包1', 1, 'active'),
                    (3, '小包2', 1, 'active');
                """
            )
            conn.commit()
        finally:
            conn.close()

    def test_migration_adds_sort_order_and_preserves_current_display_order(self):
        self._create_old_schema_database()

        db.migrate_db()

        conn = sqlite3.connect(db.DB_PATH)
        try:
            columns = [row[1] for row in conn.execute("PRAGMA table_info(devices)")]
            rows = conn.execute(
                "SELECT name, sort_order FROM devices ORDER BY sort_order, id"
            ).fetchall()
        finally:
            conn.close()

        self.assertIn("sort_order", columns)
        self.assertEqual(
            rows,
            [
                ("奥特曼包厢", 0),
                ("小包1", 1),
                ("小包2", 2),
            ],
        )

    def test_get_all_devices_and_update_sort_order_use_manual_order(self):
        db.init_db()
        db.migrate_db()
        type_id = db.get_all_device_types()[0]["id"]
        first = db.add_device("一号包厢", type_id)
        second = db.add_device("二号包厢", type_id)
        third = db.add_device("三号包厢", type_id)

        self.assertTrue(db.update_device_sort_order([third, first, second]))

        devices = db.get_all_devices()
        self.assertEqual([row["id"] for row in devices], [third, first, second])
        self.assertEqual([row["sort_order"] for row in devices], [0, 1, 2])

    def test_add_device_appends_after_existing_manual_order(self):
        db.init_db()
        db.migrate_db()
        type_id = db.get_all_device_types()[0]["id"]
        first = db.add_device("一号包厢", type_id)
        second = db.add_device("二号包厢", type_id)
        self.assertTrue(db.update_device_sort_order([second, first]))

        third = db.add_device("三号包厢", type_id)

        devices = db.get_all_devices()
        self.assertEqual([row["id"] for row in devices], [second, first, third])
        self.assertEqual(devices[-1]["sort_order"], 2)
        self.assertEqual(devices[-1]["status"], DeviceStatus.IDLE)


if __name__ == "__main__":
    unittest.main()
