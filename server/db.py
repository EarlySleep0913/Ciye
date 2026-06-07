"""Database layer — user-isolated, connection-pooled, indexed."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
import datetime as dt
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
APP_DB = DATA_DIR / "app.db"
ECDICT_DB = DATA_DIR / "ecdict.db"

_local = threading.local()

# Password hashing
_SALT = "ciye-salt-2026"


def hash_password(password: str) -> str:
    return hashlib.sha256((_SALT + password).encode()).hexdigest()


def get_conn() -> sqlite3.Connection:
    """每个线程独立连接，避免多线程竞争。"""
    if not hasattr(_local, 'conn') or _local.conn is None:
        DATA_DIR.mkdir(exist_ok=True)
        conn = sqlite3.connect(str(APP_DB), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return _local.conn


def close_pool() -> None:
    if hasattr(_local, 'conn') and _local.conn is not None:
        _local.conn.close()
        _local.conn = None


@lru_cache(maxsize=1)
def _ecdict_conn() -> sqlite3.Connection | None:
    if not ECDICT_DB.exists():
        return None
    conn = sqlite3.connect(f"file:{ECDICT_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def query_ecdict(word: str) -> dict:
    conn = _ecdict_conn()
    if conn is None:
        return {}
    try:
        row = conn.execute(
            "SELECT word, phonetic, definition, translation FROM stardict WHERE lower(word) = lower(?) LIMIT 1",
            (word,),
        ).fetchone()
        if not row:
            return {}
        return {
            "word": row["word"],
            "phonetic": row["phonetic"] or "",
            "definition": row["definition"] or "",
            "translation": row["translation"] or "",
        }
    except sqlite3.Error:
        return {}


def today() -> str:
    offset = int(get_setting("date_offset", "0", user_id=0))
    return (dt.date.today() + dt.timedelta(days=offset)).isoformat()


def now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


# ── Settings (user-aware) ──

def get_setting(key: str, default: str, user_id: int = 0) -> str:
    row = get_conn().execute(
        "SELECT value FROM settings WHERE user_id = ? AND key = ?", (user_id, key)
    ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str, user_id: int = 0) -> None:
    get_conn().execute(
        """INSERT INTO settings(user_id, key, value) VALUES(?, ?, ?)
           ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value""",
        (user_id, key, value),
    )
    get_conn().commit()


def active_book_id(user_id: int) -> int | None:
    value = get_setting("active_book_id", "", user_id=user_id)
    try:
        return int(value) if value else None
    except ValueError:
        return None


# ── User helpers ──

def get_user_by_username(username: str) -> dict | None:
    row = get_conn().execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    return dict(row) if row else None


def get_user_by_token(token: str) -> dict | None:
    row = get_conn().execute(
        """SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
           WHERE s.token = ?""", (token,)
    ).fetchone()
    return dict(row) if row else None


# ── Schema ──

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    is_public INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    word TEXT NOT NULL,
    translation TEXT,
    definition TEXT,
    phonetic TEXT,
    example TEXT,
    audio_url TEXT,
    image_url TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(book_id, word),
    FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS progress (
    user_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    familiarity INTEGER NOT NULL DEFAULT 0,
    memory_strength REAL NOT NULL DEFAULT 1.0,
    attempts INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    last_seen TEXT,
    due_date TEXT,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    is_wrong INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(user_id, word_id),
    FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER NOT NULL DEFAULT 0,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY(user_id, key)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    word_id INTEGER,
    action TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pdf_words (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day INTEGER NOT NULL,
    position INTEGER NOT NULL,
    word TEXT NOT NULL,
    translation TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'cet4_pdf',
    UNIQUE(source, day, word)
);

CREATE TABLE IF NOT EXISTS pdf_word_marks (
    user_id INTEGER NOT NULL,
    word_id INTEGER NOT NULL,
    crossed INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(user_id, word_id),
    FOREIGN KEY(word_id) REFERENCES pdf_words(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS daily_session (
    user_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    book_id INTEGER,
    word_ids TEXT NOT NULL,
    studied_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    PRIMARY KEY(user_id, date, book_id)
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_books_user ON books(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_due ON progress(user_id, status, due_date);
CREATE INDEX IF NOT EXISTS idx_words_book_word ON words(book_id, word);
CREATE INDEX IF NOT EXISTS idx_events_user_date ON events(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_pdf_words_source ON pdf_words(source, day, position);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""

def _clean_example(text: str) -> str:
    """Filter out template examples from CSV data."""
    if not text:
        return ""
    t = text.strip()
    if t.lower().startswith("i need to remember the word"):
        return ""
    if t.lower().startswith("i want to remember the word"):
        return ""
    return t


PRESET_USERS = [
    ("earlysleep0913", "200413", "admin"),
    ("bing", "jbjzhkpku200595", "admin"),
    ("lbw", "200413", "user"),
]

PRESET_BOOKS = {
    "英语四级高频词汇（一）": "E:\\Codex\\danci\\data\\英语四级高频词汇_submission.csv",
}


def _seed_preset_data(conn: sqlite3.Connection) -> None:
    """Insert preset users and sample books for each user."""
    import csv, os

    # Preset users
    for username, password, role in PRESET_USERS:
        conn.execute(
            "INSERT OR IGNORE INTO users(username, password_hash, role, created_at) VALUES(?, ?, ?, ?)",
            (username, hash_password(password), role, now_iso()),
        )

    # Preset books for each user
    csv_path = PRESET_BOOKS.get("英语四级高频词汇（一）")
    users = conn.execute("SELECT id FROM users").fetchall()

    for user_row in users:
        uid = user_row["id"]
        # Create 3 books per user
        for part_name in ["英语四级高频词汇（一）", "英语四级高频词汇（二）", "英语四级高频词汇（三）"]:
            book_id = conn.execute(
                "INSERT INTO books(user_id, name, created_at) VALUES(?, ?, ?)",
                (uid, part_name, now_iso()),
            ).lastrowid

            if csv_path and os.path.exists(csv_path):
                with open(csv_path, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    rows = [r for r in reader if r.get("word", "").strip()]

                total = len(rows)
                chunk = total // 3
                idx = ["（一）", "（二）", "（三）"].index(part_name.replace("英语四级高频词汇", ""))
                part_rows = rows[chunk * idx : chunk * (idx + 1)] if idx < 2 else rows[chunk * idx:]

                for r in part_rows:
                    word = r["word"].strip().lower()
                    if not word:
                        continue
                    try:
                        wid = conn.execute(
                            """INSERT INTO words(book_id, word, translation, definition, example, created_at)
                               VALUES(?, ?, ?, ?, ?, ?)""",
                            (book_id, word, r.get("translation", ""), r.get("definition", ""),
                             _clean_example(r.get("example", "")), now_iso()),
                        ).lastrowid
                        conn.execute(
                            "INSERT OR IGNORE INTO progress(user_id, word_id, due_date) VALUES(?, ?, ?)",
                            (uid, wid, today()),
                        )
                    except sqlite3.IntegrityError:
                        continue

        # Set first book as active for this user
        first_book = conn.execute(
            "SELECT id FROM books WHERE user_id = ? ORDER BY id LIMIT 1", (uid,)
        ).fetchone()
        if first_book:
            conn.execute(
                "INSERT OR IGNORE INTO settings(user_id, key, value) VALUES(?, 'active_book_id', ?)",
                (uid, str(first_book["id"])),
            )
            conn.execute(
                "INSERT OR IGNORE INTO settings(user_id, key, value) VALUES(?, 'daily_new_limit', '15')",
                (uid,),
            )


def init_db() -> None:
    conn = get_conn()
    conn.executescript(SCHEMA_SQL)
    conn.executescript(INDEX_SQL)

    # Migration: add memory_strength column if missing
    try:
        conn.execute("SELECT memory_strength FROM progress LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE progress ADD COLUMN memory_strength REAL NOT NULL DEFAULT 1.0")
        conn.commit()

    # Migration: add is_public column to books if missing
    try:
        conn.execute("SELECT is_public FROM books LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE books ADD COLUMN is_public INTEGER NOT NULL DEFAULT 0")
        conn.commit()

    # Global AI settings defaults
    conn.execute("INSERT OR IGNORE INTO settings(user_id, key, value) VALUES(0, 'ai_api_url', '')")
    conn.execute("INSERT OR IGNORE INTO settings(user_id, key, value) VALUES(0, 'ai_api_key', '')")
    conn.execute("INSERT OR IGNORE INTO settings(user_id, key, value) VALUES(0, 'ai_model', 'Pro/moonshotai/Kimi-K2.6')")

    # Global settings
    conn.execute(
        "INSERT OR IGNORE INTO settings(user_id, key, value) VALUES(0, 'date_offset', '0')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO settings(user_id, key, value) VALUES(0, 'pexels_api_key', '')"
    )

    # Seed preset data if users table is empty
    user_count = conn.execute("SELECT count(*) AS c FROM users").fetchone()["c"]
    if user_count == 0:
        _seed_preset_data(conn)

    conn.commit()
