import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DB_PATH = Path(__file__).resolve().parent / "baymax.sqlite3"
LOCAL_TZ = ZoneInfo("Asia/Novosibirsk")


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                age INTEGER,
                height REAL,
                weight REAL,
                sex TEXT,
                activity_level INTEGER,
                avg_sleep REAL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS bmi_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                entry_date TEXT,
                age INTEGER,
                height REAL NOT NULL,
                weight REAL NOT NULL,
                bmi REAL NOT NULL,
                grade TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS water_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                entry_date TEXT,
                weight REAL NOT NULL,
                sport TEXT NOT NULL,
                water_ml REAL NOT NULL,
                norm_ml REAL NOT NULL,
                percent REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sleep_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                entry_date TEXT,
                sleep_time TEXT NOT NULL,
                wake_time TEXT NOT NULL,
                state_sleep INTEGER NOT NULL,
                avg_sleep REAL NOT NULL,
                grade_sleep INTEGER NOT NULL,
                score REAL NOT NULL,
                duration_hours INTEGER NOT NULL,
                duration_minutes INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS kbzhu_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                entry_date TEXT,
                sex TEXT NOT NULL,
                age INTEGER NOT NULL,
                height REAL NOT NULL,
                weight REAL NOT NULL,
                level INTEGER NOT NULL,
                goal INTEGER NOT NULL,
                calories INTEGER NOT NULL,
                proteins INTEGER NOT NULL,
                fats INTEGER NOT NULL,
                carbs INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        _ensure_column(connection, "bmi_entries", "entry_date", "TEXT")
        _ensure_column(connection, "water_entries", "entry_date", "TEXT")
        _ensure_column(connection, "sleep_entries", "entry_date", "TEXT")
        _ensure_column(connection, "kbzhu_entries", "entry_date", "TEXT")
        _ensure_column(connection, "user_profiles", "activity_level", "INTEGER")
        for table_name in ("bmi_entries", "water_entries", "sleep_entries", "kbzhu_entries"):
            connection.execute(
                f"""
                UPDATE {table_name}
                SET entry_date = date(created_at)
                WHERE entry_date IS NULL
                """
            )


def _ensure_column(connection, table_name, column_name, column_type):
    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    if column_name not in {column["name"] for column in columns}:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def current_entry_date():
    return datetime.now(LOCAL_TZ).date().isoformat()


def ensure_user(telegram_id):
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (telegram_id, created_at, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (telegram_id, now, now),
        )
        row = connection.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
        connection.execute(
            "INSERT OR IGNORE INTO user_profiles (user_id, updated_at) VALUES (?, ?)",
            (row["id"], now),
        )
        return row["id"]


def get_profile(telegram_id):
    user_id = ensure_user(telegram_id)
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else {}


def update_profile(telegram_id, **fields):
    allowed_fields = {"age", "height", "weight", "sex", "activity_level", "avg_sleep"}
    fields = {key: value for key, value in fields.items() if key in allowed_fields}
    if not fields:
        return

    user_id = ensure_user(telegram_id)
    fields["updated_at"] = datetime.utcnow().isoformat(timespec="seconds")
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values())

    with get_connection() as connection:
        connection.execute(
            f"UPDATE user_profiles SET {assignments} WHERE user_id = ?",
            (*values, user_id),
        )


def add_bmi_entry(telegram_id, age, height, weight, bmi, grade):
    user_id = ensure_user(telegram_id)
    entry_date = current_entry_date()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO bmi_entries (user_id, entry_date, age, height, weight, bmi, grade)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, entry_date, age, height, weight, bmi, grade),
        )


def add_water_entry(telegram_id, weight, sport, water_ml, norm_ml, percent, mode="add"):
    user_id = ensure_user(telegram_id)
    entry_date = current_entry_date()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, water_ml
            FROM water_entries
            WHERE user_id = ? AND entry_date = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, entry_date),
        ).fetchone()
        if row:
            total_water = row["water_ml"] + water_ml if mode == "add" else water_ml
            connection.execute(
                """
                UPDATE water_entries
                SET weight = ?, sport = ?, water_ml = ?, norm_ml = ?, percent = ?
                WHERE id = ?
                """,
                (weight, sport, total_water, norm_ml, (total_water / norm_ml) * 100, row["id"]),
            )
            return total_water, True

        connection.execute(
            """
            INSERT INTO water_entries (user_id, entry_date, weight, sport, water_ml, norm_ml, percent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, entry_date, weight, sport, water_ml, norm_ml, percent),
        )
        return water_ml, False


def add_sleep_entry(
    telegram_id,
    sleep_time,
    wake_time,
    state_sleep,
    avg_sleep,
    grade_sleep,
    score,
    duration_hours,
    duration_minutes,
):
    user_id = ensure_user(telegram_id)
    entry_date = current_entry_date()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO sleep_entries (
                user_id, entry_date, sleep_time, wake_time, state_sleep, avg_sleep,
                grade_sleep, score, duration_hours, duration_minutes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                entry_date,
                sleep_time,
                wake_time,
                state_sleep,
                avg_sleep,
                grade_sleep,
                score,
                duration_hours,
                duration_minutes,
            ),
        )


def add_kbzhu_entry(telegram_id, sex, age, height, weight, level, goal, calories, proteins, fats, carbs):
    user_id = ensure_user(telegram_id)
    entry_date = current_entry_date()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO kbzhu_entries (
                user_id, entry_date, sex, age, height, weight, level, goal,
                calories, proteins, fats, carbs
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, entry_date, sex, age, height, weight, level, goal, calories, proteins, fats, carbs),
        )


def get_bmi_history(telegram_id, limit=30):
    user_id = ensure_user(telegram_id)
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT created_at, bmi, weight
            FROM bmi_entries
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def get_water_history(telegram_id, limit=30):
    user_id = ensure_user(telegram_id)
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT entry_date, water_ml, norm_ml, percent
            FROM water_entries
            WHERE user_id = ?
            ORDER BY entry_date DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def get_sleep_history(telegram_id, limit=30):
    user_id = ensure_user(telegram_id)
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT created_at, score, duration_hours, duration_minutes
            FROM sleep_entries
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def get_today_summary(telegram_id):
    user_id = ensure_user(telegram_id)
    today = current_entry_date()
    with get_connection() as connection:
        today_bmi = connection.execute(
            """
            SELECT *
            FROM bmi_entries
            WHERE user_id = ? AND entry_date = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, today),
        ).fetchone()
        latest_bmi = connection.execute(
            """
            SELECT *
            FROM bmi_entries
            WHERE user_id = ?
            ORDER BY entry_date DESC, id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        today_water = connection.execute(
            """
            SELECT *
            FROM water_entries
            WHERE user_id = ? AND entry_date = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, today),
        ).fetchone()
        today_sleep = connection.execute(
            """
            SELECT *
            FROM sleep_entries
            WHERE user_id = ? AND entry_date = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, today),
        ).fetchone()
        today_kbzhu = connection.execute(
            """
            SELECT *
            FROM kbzhu_entries
            WHERE user_id = ? AND entry_date = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, today),
        ).fetchone()
        latest_kbzhu = connection.execute(
            """
            SELECT *
            FROM kbzhu_entries
            WHERE user_id = ?
            ORDER BY entry_date DESC, id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()

    return {
        "date": today,
        "bmi": dict(today_bmi) if today_bmi else None,
        "latest_bmi": dict(latest_bmi) if latest_bmi else None,
        "water": dict(today_water) if today_water else None,
        "sleep": dict(today_sleep) if today_sleep else None,
        "today_kbzhu": dict(today_kbzhu) if today_kbzhu else None,
        "latest_kbzhu": dict(latest_kbzhu) if latest_kbzhu else None,
    }
