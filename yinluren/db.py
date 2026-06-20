import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "lumora.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        id TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        name TEXT NOT NULL,
        gender TEXT NOT NULL,
        birth_date TEXT NOT NULL,
        birth_time_slot TEXT NOT NULL,
        branch TEXT NOT NULL,
        zodiac TEXT NOT NULL,
        country TEXT NOT NULL,
        province TEXT NOT NULL,
        city TEXT NOT NULL,
        occupation TEXT NOT NULL,
        consent INTEGER NOT NULL,
        is_self INTEGER NOT NULL,
        updated_at TEXT NOT NULL,
        timezone_calibration TEXT
    )
    """)

    # Migration: add timezone_calibration column to existing databases
    try:
        cur.execute("ALTER TABLE profiles ADD COLUMN timezone_calibration TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists

    cur.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def purge_delivery_demo_profiles() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM profiles
        WHERE label = '測試他者'
           OR label = 'Demo Profile'
           OR label LIKE 'CRUD Smoke Test %'
           OR label LIKE 'CRUD Updated %'
           OR label = 'SmokeTest'
           OR label LIKE 'Demo %'
           OR (
                label = '我的命單'
                AND name = ''
                AND gender = '女'
                AND country = 'Taiwan'
                AND province = 'Taipei'
                AND city = 'Taipei'
                AND occupation = 'Engineer'
                AND is_self = 1
           )
           OR (
                label = '我的命局資料'
                AND name = ''
                AND gender = '男'
                AND country = 'Taiwan'
                AND province = 'Tainan City'
                AND city = '台南市'
                AND occupation = '建築 / 地產'
                AND is_self = 0
           )
        """
    )
    deleted = cur.rowcount or 0
    conn.commit()
    conn.close()
    return deleted


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    keys = row.keys()
    return {
        "id": row["id"],
        "label": row["label"],
        "name": row["name"],
        "gender": row["gender"],
        "birth_date": row["birth_date"],
        "birth_time_slot": row["birth_time_slot"],
        "branch": row["branch"],
        "zodiac": row["zodiac"],
        "country": row["country"],
        "province": row["province"],
        "city": row["city"],
        "occupation": row["occupation"],
        "consent": bool(row["consent"]),
        "is_self": bool(row["is_self"]),
        "updated_at": row["updated_at"],
        "timezone_calibration": row["timezone_calibration"] if "timezone_calibration" in keys else None,
    }


def list_profiles() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles ORDER BY is_self DESC, updated_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    row = cur.fetchone()
    conn.close()
    return row_to_dict(row) if row else None


def create_profile(item: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO profiles (
        id, label, name, gender, birth_date, birth_time_slot,
        branch, zodiac, country, province, city, occupation,
        consent, is_self, updated_at, timezone_calibration
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item["id"],
        item["label"],
        item["name"],
        item["gender"],
        item["birth_date"],
        item["birth_time_slot"],
        item["branch"],
        item["zodiac"],
        item["country"],
        item["province"],
        item["city"],
        item["occupation"],
        1 if item["consent"] else 0,
        1 if item["is_self"] else 0,
        item["updated_at"],
        item.get("timezone_calibration"),
    ))
    conn.commit()
    conn.close()
    return item


def update_profile(profile_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    existing = get_profile(profile_id)
    if not existing:
        return None

    existing.update(updates)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    UPDATE profiles
    SET label = ?, name = ?, gender = ?, birth_date = ?, birth_time_slot = ?,
        branch = ?, zodiac = ?, country = ?, province = ?, city = ?,
        occupation = ?, consent = ?, is_self = ?, updated_at = ?,
        timezone_calibration = ?
    WHERE id = ?
    """, (
        existing["label"],
        existing["name"],
        existing["gender"],
        existing["birth_date"],
        existing["birth_time_slot"],
        existing["branch"],
        existing["zodiac"],
        existing["country"],
        existing["province"],
        existing["city"],
        existing["occupation"],
        1 if existing["consent"] else 0,
        1 if existing["is_self"] else 0,
        existing["updated_at"],
        existing.get("timezone_calibration"),
        profile_id,
    ))
    conn.commit()
    conn.close()
    return existing


def delete_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    existing = get_profile(profile_id)
    if not existing:
        return None

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    conn.commit()
    conn.close()
    return existing


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return default
    return row["value"]


def set_setting(key: str, value: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO app_settings (key, value)
    VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()
    conn.close()
