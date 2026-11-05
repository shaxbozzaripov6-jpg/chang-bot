"""SQLite: foydalanuvchilar, obunalar va bo'ron xabarlari."""
import math
import os
import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tashkent")

DB_PATH = os.getenv("DB_PATH", "chang_bot.db")
if os.path.dirname(DB_PATH):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.executescript("""
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    city       TEXT,
    lat        REAL,
    lon        REAL,
    alerts     INTEGER DEFAULT 1,
    daily      INTEGER DEFAULT 0,
    last_alert TEXT,
    created    TEXT
);
CREATE TABLE IF NOT EXISTS reports (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER,
    city     TEXT,
    lat      REAL,
    lon      REAL,
    file_id  TEXT,
    caption  TEXT,
    status   TEXT,            -- pending / approved / rejected
    created  TEXT
);
""")
# Eski bazaga yangi ustun qo'shish (migratsiya)
if "lang" not in {r["name"] for r in conn.execute("PRAGMA table_info(users)")}:
    conn.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'uz'")
conn.commit()


def now_local() -> datetime:
    """Toshkent vaqti (server UTC da ishlasa ham)."""
    return datetime.now(TZ).replace(tzinfo=None)


def _now() -> str:
    return now_local().isoformat(timespec="seconds")


# ---------------- Foydalanuvchilar ----------------
def get_user(uid: int):
    return conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()


def ensure_user(uid: int, lang: str = "uz"):
    conn.execute("INSERT OR IGNORE INTO users(user_id, lang, created) VALUES(?, ?, ?)",
                 (uid, lang, _now()))
    conn.commit()


def get_lang(uid: int) -> str:
    u = get_user(uid)
    return (u["lang"] if u and u["lang"] else None) or "uz"


def set_lang(uid: int, lang: str):
    ensure_user(uid, lang)
    conn.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, uid))
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
    q = lambda s: conn.execute(s).fetchone()[0]  # noqa: E731
    return {
        "jami": q("SELECT COUNT(*) FROM users"),
        "ru": q("SELECT COUNT(*) FROM users WHERE lang='ru'"),
        "ogohlantirish": q("SELECT COUNT(*) FROM users WHERE alerts=1"),
        "kunlik": q("SELECT COUNT(*) FROM users WHERE daily=1"),
        "xabarlar": q("SELECT COUNT(*) FROM reports"),
        "kutilmoqda": q("SELECT COUNT(*) FROM reports WHERE status='pending'"),
    }


# ---------------- Bo'ron xabarlari ----------------
def distance_km(lat1, lon1, lat2, lon2) -> float:
    """Ikki nuqta orasidagi masofa (haversine formulasi)."""
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def reports_today(uid: int) -> int:
    since = (now_local() - timedelta(hours=24)).isoformat(timespec="seconds")
    return conn.execute("SELECT COUNT(*) FROM reports WHERE user_id=? AND created>=?",
                        (uid, since)).fetchone()[0]


def add_report(uid: int, city: str, lat: float, lon: float, file_id: str,
               caption: str, status: str) -> int:
    cur = conn.execute(
        "INSERT INTO reports(user_id, city, lat, lon, file_id, caption, status, created) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
        (uid, city, lat, lon, file_id, caption, status, _now()))
    conn.commit()
    return cur.lastrowid


def get_report(rid: int):
    return conn.execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()


def set_report_status(rid: int, status: str):
    conn.execute("UPDATE reports SET status=? WHERE id=?", (status, rid))
    conn.commit()


def nearby_reports(lat: float, lon: float, km: float = 150, hours: int = 24, limit: int = 5):
    """So'nggi N soatdagi tasdiqlangan xabarlar, yaqinidan boshlab."""
    since = (now_local() - timedelta(hours=hours)).isoformat(timespec="seconds")
    rows = conn.execute("SELECT * FROM reports WHERE status='approved' AND created>=? "
                        "ORDER BY created DESC", (since,)).fetchall()
    found = [(distance_km(lat, lon, r["lat"], r["lon"]), r) for r in rows]
    found = [(d, r) for d, r in found if d <= km]
    found.sort(key=lambda x: x[0])
    return found[:limit]


def users_near(lat: float, lon: float, km: float, exclude: int):
    """Ogohlantirish yoqilgan va yaqin atrofda turgan foydalanuvchilar."""
    out = []
    for u in users_with("alerts"):
        if u["user_id"] == exclude:
            continue
        d = distance_km(lat, lon, u["lat"], u["lon"])
        if d <= km:
            out.append((d, u))
    return out
