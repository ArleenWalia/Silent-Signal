"""
database.py — SQLite connection and schema
"""
import sqlite3

DB_PATH = "signals.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            year        TEXT    NOT NULL,
            barriers    TEXT    NOT NULL,
            workload    INTEGER NOT NULL,
            visibility  TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_memory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_patterns (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start  TEXT NOT NULL,
            pattern_key TEXT NOT NULL,
            pattern_val REAL NOT NULL,
            created_at  TEXT NOT NULL,
            UNIQUE(week_start, pattern_key) ON CONFLICT REPLACE
        )
    """)
    conn.commit()
    conn.close()