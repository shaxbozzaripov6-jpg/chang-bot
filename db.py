"""SQLite: foydalanuvchilar va obunalar."""
import os
import sqlite3
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "chang_bot.db")
if os.path.dirname(DB_PATH):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    city       TEXT,
    lat        REAL,
    lon        REAL,
    alerts     INTEGER DEFAULT 1,
    daily      INTEGER DEFAULT 0,
    last_alert TEXT,
    created    TEXT
)""")
conn.commit()


def get_user(uid: int):
    return conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()


def ensure_user(uid: int):
    conn.execute("INSERT OR IGNORE INTO users(user_id, created) VALUES(?, ?)",
                 (uid, datetime.now().isoformat(timespec="seconds")))
    conn.commit()


def set_location(uid: int, city: str, lat: float, lon: float):
    ensure_user(uid)
    conn.execute("UPDATE users SET city=?, lat=?, lon=? WHERE user_id=?", (city, lat, lon, uid))
    conn.commit()


def toggle(uid: int, field: str) -> int:
    assert field in ("alerts", "daily")
    ensure_user(uid)
    conn.execute(f"UPDATE users SET {field} = 1 - {field} WHERE user_id=?", (uid,))
    conn.commit()
    return get_user(uid)[field]


def set_last_alert(uid: int, ts: str):
    conn.execute("UPDATE users SET last_alert=? WHERE user_id=?", (ts, uid))
    conn.commit()


def users_with(field: str):
    assert field in ("alerts", "daily")
    return conn.execute(f"SELECT * FROM users WHERE {field}=1 AND lat IS NOT NULL").fetchall()


def delete_user(uid: int):
    conn.execute("DELETE FROM users WHERE user_id=?", (uid,))
    conn.commit()


def stats() -> dict:
    q = lambda s: conn.execute(s).fetchone()[0]
    return {
        "jami": q("SELECT COUNT(*) FROM users"),
        "ogohlantirish": q("SELECT COUNT(*) FROM users WHERE alerts=1"),
        "kunlik": q("SELECT COUNT(*) FROM users WHERE daily=1"),
    }
