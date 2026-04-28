#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库操作模块 (Database operations module)
使用 SQLite，无需安装独立数据库服务。
Uses SQLite – no external database installation required.
"""

import os
import sqlite3

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "videogame.db")

DEFAULT_PRICE_PER_HOUR = 10.0


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and seed default settings on first run."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE,
            status     INTEGER NOT NULL DEFAULT 0,   -- 0=空闲 1=使用中
            start_time REAL    DEFAULT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id          INTEGER NOT NULL,
            room_name        TEXT    NOT NULL,
            start_time       REAL    NOT NULL,
            end_time         REAL    NOT NULL,
            duration_minutes REAL    NOT NULL,
            cost             REAL    NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    cur.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('price_per_hour', ?)",
        (str(DEFAULT_PRICE_PER_HOUR),),
    )

    conn.commit()
    conn.close()


# ── Rooms ──────────────────────────────────────────────────────────────────────

def get_all_rooms() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM rooms ORDER BY name").fetchall()
    conn.close()
    return rows


def add_room(name: str) -> None:
    conn = get_connection()
    conn.execute("INSERT INTO rooms (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


def delete_room(room_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    conn.commit()
    conn.close()


def start_room(room_id: int, start_time: float) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE rooms SET status = 1, start_time = ? WHERE id = ?",
        (start_time, room_id),
    )
    conn.commit()
    conn.close()


def stop_room(
    room_id: int,
    room_name: str,
    start_time: float,
    end_time: float,
    duration_minutes: float,
    cost: float,
) -> None:
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO sessions
            (room_id, room_name, start_time, end_time, duration_minutes, cost)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (room_id, room_name, start_time, end_time, duration_minutes, cost),
    )
    conn.execute(
        "UPDATE rooms SET status = 0, start_time = NULL WHERE id = ?",
        (room_id,),
    )
    conn.commit()
    conn.close()


# ── Sessions ───────────────────────────────────────────────────────────────────

def get_all_sessions() -> list[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sessions ORDER BY end_time DESC"
    ).fetchall()
    conn.close()
    return rows


def clear_sessions() -> None:
    conn = get_connection()
    conn.execute("DELETE FROM sessions")
    conn.commit()
    conn.close()


# ── Settings ───────────────────────────────────────────────────────────────────

def get_price_per_hour() -> float:
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'price_per_hour'"
    ).fetchone()
    conn.close()
    return float(row["value"]) if row else DEFAULT_PRICE_PER_HOUR


def set_price_per_hour(price: float) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE settings SET value = ? WHERE key = 'price_per_hour'",
        (str(price),),
    )
    conn.commit()
    conn.close()
