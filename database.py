import sqlite3
from datetime import datetime

DB_PATH = "alarms.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                alarm_date TEXT NOT NULL,
                alarm_time TEXT NOT NULL,
                job_id TEXT NOT NULL,
                run_date TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ringing_alarms (
                chat_id INTEGER PRIMARY KEY,
                alarm_date TEXT,
                alarm_time TEXT
            )
        """)
        conn.commit()

def db_add_alarm(chat_id: int, alarm_date: str, alarm_time: str, job_id: str, run_date: datetime) -> int | None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM alarms WHERE chat_id = ? AND is_active = 1",
            (chat_id,)
        )
        count = cursor.fetchone()[0]
        if count >= 100:
            return None

        cursor = conn.execute(
            "SELECT id FROM alarms WHERE chat_id = ? AND alarm_date = ? AND alarm_time = ? AND is_active = 1",
            (chat_id, alarm_date, alarm_time)
        )
        if cursor.fetchone():
            return -1  # дубликат

        cursor = conn.execute(
            "INSERT INTO alarms (chat_id, alarm_date, alarm_time, job_id, run_date) VALUES (?, ?, ?, ?, ?)",
            (chat_id, alarm_date, alarm_time, job_id, run_date.isoformat())
        )
        conn.commit()
        return cursor.lastrowid

def db_get_user_alarms(chat_id: int) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM alarms WHERE chat_id = ? AND is_active = 1 ORDER BY run_date",
            (chat_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

def db_get_all_active_alarms() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM alarms WHERE is_active = 1")
        return [dict(row) for row in cursor.fetchall()]

def db_deactivate_alarm_by_job(job_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE alarms SET is_active = 0 WHERE job_id = ?", (job_id,))
        conn.commit()

def db_deactivate_alarm_by_id(alarm_db_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE alarms SET is_active = 0 WHERE id = ?", (alarm_db_id,))
        conn.commit()

def db_set_ringing(chat_id: int, alarm_date: str, alarm_time: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO ringing_alarms (chat_id, alarm_date, alarm_time) VALUES (?, ?, ?)",
            (chat_id, alarm_date, alarm_time)
        )
        conn.commit()

def db_clear_ringing(chat_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM ringing_alarms WHERE chat_id = ?", (chat_id,))
        conn.commit()

def db_get_ringing(chat_id: int) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM ringing_alarms WHERE chat_id = ?", (chat_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
