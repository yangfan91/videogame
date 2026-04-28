"""
数据库管理器 - 负责数据库连接、初始化和所有 CRUD 操作
新版本：移除单价字段，增加计时模式（countdown/freeplay）和付款状态
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from config import DB_PATH, DEFAULT_DEVICE_TYPES, DeviceStatus, SessionStatus, TimerMode


def get_connection() -> sqlite3.Connection:
    """获取数据库连接，启用外键约束和行工厂"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化数据库，创建所有表并插入默认数据"""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 创建包厢类型表（移除 hourly_rate）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_types (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL UNIQUE,
                created_at DATETIME DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 创建包厢表（移除 hourly_rate）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT    NOT NULL UNIQUE,
                device_type_id INTEGER NOT NULL,
                status         TEXT    NOT NULL DEFAULT 'idle',
                sort_order     INTEGER NOT NULL DEFAULT 0,
                created_at     DATETIME DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (device_type_id) REFERENCES device_types(id)
            )
        """)

        # 创建使用记录表
        # timer_mode: countdown（美团套餐）| freeplay（自由计时）
        # countdown_seconds: 套餐总秒数（仅 countdown 模式有效）
        # paid: 0=未付款, 1=已付款
        # payment_method: 收款方式，逗号分隔，如 "美团,现金"
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id         INTEGER NOT NULL,
                timer_mode        TEXT    NOT NULL DEFAULT 'freeplay',
                countdown_seconds INTEGER NOT NULL DEFAULT 0,
                start_time        DATETIME NOT NULL,
                end_time          DATETIME,
                pause_duration    INTEGER NOT NULL DEFAULT 0,
                total_seconds     INTEGER,
                paid              INTEGER NOT NULL DEFAULT 0,
                payment_method    TEXT    NOT NULL DEFAULT '',
                note              TEXT    DEFAULT '',
                status            TEXT    NOT NULL DEFAULT 'active',
                created_at        DATETIME DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )
        """)

        # 创建暂停记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pause_records (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL,
                pause_start DATETIME NOT NULL,
                pause_end   DATETIME,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        # 插入默认包厢类型（如果不存在）
        for dt in DEFAULT_DEVICE_TYPES:
            cursor.execute("""
                INSERT OR IGNORE INTO device_types (name)
                VALUES (?)
            """, (dt["name"],))

        conn.commit()
    finally:
        conn.close()


def migrate_db():
    """
    数据库迁移：将旧版本（含 hourly_rate）升级到新版本。
    安全地添加新列、删除旧列（SQLite 不支持 DROP COLUMN，用重建表方式）。
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 检查 device_types 是否有 hourly_rate 列
        cols = [row[1] for row in cursor.execute("PRAGMA table_info(device_types)").fetchall()]
        if "hourly_rate" in cols:
            # 重建 device_types 表（去掉 hourly_rate）
            cursor.executescript("""
                ALTER TABLE device_types RENAME TO device_types_old;
                CREATE TABLE device_types (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT    NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT (datetime('now', 'localtime'))
                );
                INSERT INTO device_types (id, name, created_at)
                SELECT id, name, created_at FROM device_types_old;
                DROP TABLE device_types_old;
            """)

        # 检查 devices 是否缺少手动排序列
        device_cols = [row[1] for row in cursor.execute("PRAGMA table_info(devices)").fetchall()]
        if "sort_order" not in device_cols:
            cursor.execute("ALTER TABLE devices ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
            existing_devices = cursor.execute("""
                SELECT d.id
                FROM devices d
                JOIN device_types dt ON d.device_type_id = dt.id
                ORDER BY dt.name, d.name, d.id
            """).fetchall()
            for order, row in enumerate(existing_devices):
                cursor.execute(
                    "UPDATE devices SET sort_order=? WHERE id=?",
                    (order, row["id"]),
                )

        # 检查 sessions 是否缺少新列
        sess_cols = [row[1] for row in cursor.execute("PRAGMA table_info(sessions)").fetchall()]
        if "timer_mode" not in sess_cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN timer_mode TEXT NOT NULL DEFAULT 'freeplay'")
        if "countdown_seconds" not in sess_cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN countdown_seconds INTEGER NOT NULL DEFAULT 0")
        if "paid" not in sess_cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN paid INTEGER NOT NULL DEFAULT 0")
        if "payment_method" not in sess_cols:
            cursor.execute("ALTER TABLE sessions ADD COLUMN payment_method TEXT NOT NULL DEFAULT ''")

        # 移除 sessions 中的 hourly_rate / total_amount / paid_amount（重建）
        if "hourly_rate" in sess_cols:
            cursor.executescript("""
                ALTER TABLE sessions RENAME TO sessions_old;
                CREATE TABLE sessions (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id         INTEGER NOT NULL,
                    timer_mode        TEXT    NOT NULL DEFAULT 'freeplay',
                    countdown_seconds INTEGER NOT NULL DEFAULT 0,
                    start_time        DATETIME NOT NULL,
                    end_time          DATETIME,
                    pause_duration    INTEGER NOT NULL DEFAULT 0,
                    total_seconds     INTEGER,
                    paid              INTEGER NOT NULL DEFAULT 0,
                    note              TEXT    DEFAULT '',
                    status            TEXT    NOT NULL DEFAULT 'active',
                    created_at        DATETIME DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (device_id) REFERENCES devices(id)
                );
                INSERT INTO sessions
                    (id, device_id, timer_mode, countdown_seconds, start_time, end_time,
                     pause_duration, total_seconds, paid, note, status, created_at)
                SELECT
                    id, device_id, 'freeplay', 0, start_time, end_time,
                    pause_duration, total_seconds, 0, note, status, created_at
                FROM sessions_old;
                DROP TABLE sessions_old;
            """)

        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 包厢类型 CRUD
# ─────────────────────────────────────────────

def get_all_device_types() -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM device_types ORDER BY name"
        ).fetchall()
    finally:
        conn.close()


def add_device_type(name: str) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO device_types (name) VALUES (?)",
            (name,)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_device_type(type_id: int, name: str):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE device_types SET name=? WHERE id=?",
            (name, type_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_device_type(type_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM device_types WHERE id=?", (type_id,))
        conn.commit()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 包厢 CRUD
# ─────────────────────────────────────────────

def get_all_devices() -> List[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute("""
            SELECT d.*, dt.name AS type_name
            FROM devices d
            JOIN device_types dt ON d.device_type_id = dt.id
            ORDER BY d.sort_order, d.id
        """).fetchall()
    finally:
        conn.close()


def get_device_by_id(device_id: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute("""
            SELECT d.*, dt.name AS type_name
            FROM devices d
            JOIN device_types dt ON d.device_type_id = dt.id
            WHERE d.id = ?
        """, (device_id,)).fetchone()
    finally:
        conn.close()


def add_device(name: str, device_type_id: int) -> int:
    conn = get_connection()
    try:
        next_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM devices"
        ).fetchone()[0]
        cursor = conn.execute(
            "INSERT INTO devices (name, device_type_id, status, sort_order) VALUES (?, ?, ?, ?)",
            (name, device_type_id, DeviceStatus.IDLE, next_order)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_device(device_id: int, name: str, device_type_id: int):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE devices SET name=?, device_type_id=? WHERE id=?",
            (name, device_type_id, device_id)
        )
        conn.commit()
    finally:
        conn.close()


def update_device_status(device_id: int, status: str):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE devices SET status=? WHERE id=?",
            (status, device_id)
        )
        conn.commit()
    finally:
        conn.close()


def delete_device(device_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM devices WHERE id=?", (device_id,))
        conn.commit()
    finally:
        conn.close()


def update_device_sort_order(device_ids: List[int]) -> bool:
    """按传入的设备 ID 顺序保存包厢卡片排序。"""
    conn = get_connection()
    try:
        for order, device_id in enumerate(device_ids):
            conn.execute(
                "UPDATE devices SET sort_order=? WHERE id=?",
                (order, int(device_id)),
            )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 会话 CRUD
# ─────────────────────────────────────────────

def start_session(device_id: int, timer_mode: str,
                  countdown_seconds: int = 0,
                  note: str = "") -> int:
    """
    开始一个新的计时会话。

    Args:
        device_id:          包厢 ID
        timer_mode:         'countdown' 或 'freeplay'
        countdown_seconds:  套餐总秒数（countdown 模式）
        note:               开始计时备注
    """
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.execute("""
            INSERT INTO sessions
                (device_id, timer_mode, countdown_seconds, start_time, note, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (device_id, timer_mode, countdown_seconds, now, note, SessionStatus.ACTIVE))
        session_id = cursor.lastrowid
        conn.execute(
            "UPDATE devices SET status=? WHERE id=?",
            (DeviceStatus.ACTIVE, device_id)
        )
        conn.commit()
        return session_id
    finally:
        conn.close()


def pause_session(session_id: int, device_id: int) -> int:
    """暂停会话，记录暂停开始时间"""
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.execute("""
            INSERT INTO pause_records (session_id, pause_start)
            VALUES (?, ?)
        """, (session_id, now))
        pause_id = cursor.lastrowid
        conn.execute(
            "UPDATE sessions SET status=? WHERE id=?",
            (SessionStatus.PAUSED, session_id)
        )
        conn.execute(
            "UPDATE devices SET status=? WHERE id=?",
            (DeviceStatus.PAUSED, device_id)
        )
        conn.commit()
        return pause_id
    finally:
        conn.close()


def resume_session(session_id: int, device_id: int):
    """恢复会话，记录暂停结束时间并累加暂停时长"""
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pause_record = conn.execute("""
            SELECT * FROM pause_records
            WHERE session_id=? AND pause_end IS NULL
            ORDER BY id DESC LIMIT 1
        """, (session_id,)).fetchone()

        if pause_record:
            pause_start = datetime.strptime(pause_record["pause_start"], "%Y-%m-%d %H:%M:%S")
            pause_end = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
            pause_seconds = int((pause_end - pause_start).total_seconds())

            conn.execute(
                "UPDATE pause_records SET pause_end=? WHERE id=?",
                (now, pause_record["id"])
            )
            conn.execute("""
                UPDATE sessions
                SET pause_duration = pause_duration + ?, status=?
                WHERE id=?
            """, (pause_seconds, SessionStatus.ACTIVE, session_id))

        conn.execute(
            "UPDATE devices SET status=? WHERE id=?",
            (DeviceStatus.ACTIVE, device_id)
        )
        conn.commit()
    finally:
        conn.close()


def end_session(session_id: int, device_id: int,
                total_seconds: int, paid: bool,
                note: str = "", payment_method: str = "") -> bool:
    """
    结束会话，记录时长、付款状态和收款方式。

    Args:
        session_id:      会话 ID
        device_id:       包厢 ID
        total_seconds:   实际使用秒数
        paid:            是否已付款
        note:            备注
        payment_method:  收款方式（逗号分隔，如 "美团,现金"）
    """
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            UPDATE sessions
            SET end_time=?, total_seconds=?, paid=?, payment_method=?, note=?, status=?
            WHERE id=?
        """, (now, total_seconds, 1 if paid else 0,
              payment_method, note, SessionStatus.COMPLETED, session_id))
        conn.execute(
            "UPDATE devices SET status=? WHERE id=?",
            (DeviceStatus.IDLE, device_id)
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def extend_session_countdown(session_id: int, new_countdown_seconds: int) -> bool:
    """更新会话的套餐总时长（加时后同步数据库）"""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE sessions SET countdown_seconds=? WHERE id=?",
            (new_countdown_seconds, session_id)
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def mark_session_paid(session_id: int) -> bool:
    """单独标记会话为已付款"""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE sessions SET paid=1 WHERE id=?",
            (session_id,)
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def update_session_note(session_id: int, note: str) -> bool:
    """更新会话备注。"""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE sessions SET note=? WHERE id=?",
            (note, session_id)
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        conn.close()


def get_active_session(device_id: int) -> Optional[sqlite3.Row]:
    """获取包厢当前进行中或暂停中的会话"""
    conn = get_connection()
    try:
        return conn.execute("""
            SELECT * FROM sessions
            WHERE device_id=? AND status IN ('active', 'paused')
            ORDER BY id DESC LIMIT 1
        """, (device_id,)).fetchone()
    finally:
        conn.close()


def get_all_active_sessions() -> List[sqlite3.Row]:
    """获取所有进行中的会话（用于程序启动时恢复）"""
    conn = get_connection()
    try:
        return conn.execute("""
            SELECT s.*, d.name AS device_name, d.device_type_id
            FROM sessions s
            JOIN devices d ON s.device_id = d.id
            WHERE s.status IN ('active', 'paused')
        """).fetchall()
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 统计查询（不含金额）
# ─────────────────────────────────────────────

def get_stats_by_date(date_from: str, date_to: str) -> Dict[str, Any]:
    """按日期范围查询统计数据（仅时长，不含金额）"""
    conn = get_connection()
    try:
        # 总次数和总时长
        summary = conn.execute("""
            SELECT
                COUNT(*) AS total_count,
                COALESCE(SUM(total_seconds), 0) AS total_seconds,
                SUM(CASE WHEN timer_mode='countdown' THEN 1 ELSE 0 END) AS countdown_count,
                SUM(CASE WHEN timer_mode='freeplay'  THEN 1 ELSE 0 END) AS freeplay_count,
                SUM(CASE WHEN paid=1 THEN 1 ELSE 0 END) AS paid_count
            FROM sessions
            WHERE status='completed'
              AND date(start_time) BETWEEN ? AND ?
        """, (date_from, date_to)).fetchone()

        # 按包厢统计
        by_device = conn.execute("""
            SELECT
                d.name AS device_name,
                dt.name AS type_name,
                COUNT(*) AS session_count,
                COALESCE(SUM(s.total_seconds), 0) AS total_seconds,
                SUM(CASE WHEN s.timer_mode='countdown' THEN 1 ELSE 0 END) AS countdown_count,
                SUM(CASE WHEN s.timer_mode='freeplay'  THEN 1 ELSE 0 END) AS freeplay_count
            FROM sessions s
            JOIN devices d ON s.device_id = d.id
            JOIN device_types dt ON d.device_type_id = dt.id
            WHERE s.status='completed'
              AND date(s.start_time) BETWEEN ? AND ?
            GROUP BY d.id
            ORDER BY total_seconds DESC
        """, (date_from, date_to)).fetchall()

        # 历史记录列表
        records = conn.execute("""
            SELECT
                s.id,
                d.name AS device_name,
                dt.name AS type_name,
                s.timer_mode,
                s.countdown_seconds,
                s.start_time,
                s.end_time,
                s.total_seconds,
                s.paid,
                s.payment_method,
                s.note
            FROM sessions s
            JOIN devices d ON s.device_id = d.id
            JOIN device_types dt ON d.device_type_id = dt.id
            WHERE s.status='completed'
              AND date(s.start_time) BETWEEN ? AND ?
            ORDER BY s.start_time DESC
        """, (date_from, date_to)).fetchall()

        return {
            "summary": summary,
            "by_device": by_device,
            "records": records,
        }
    finally:
        conn.close()
