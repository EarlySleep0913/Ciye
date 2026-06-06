"""Database layer with connection pooling, caching, and index management."""

from __future__ import annotations

import sqlite3
import datetime as dt
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
APP_DB = DATA_DIR / "app.db"
ECDICT_DB = DATA_DIR / "ecdict.db"

_pool: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    """Return a single shared connection (connection pool for single-user app)."""
    global _pool
    if _pool is None:
        DATA_DIR.mkdir(exist_ok=True)
        _pool = sqlite3.connect(APP_DB, check_same_thread=False)
        _pool.row_factory = sqlite3.Row
        _pool.execute("PRAGMA journal_mode=WAL")
        _pool.execute("PRAGMA synchronous=NORMAL")
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@lru_cache(maxsize=1)
def _ecdict_conn() -> sqlite3.Connection | None:
    """Cached read-only connection to ECDICT dictionary."""
    if not ECDICT_DB.exists():
        return None
    conn = sqlite3.connect(f"file:{ECDICT_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def query_ecdict(word: str) -> dict:
    """Lookup word in ECDICT with LRU caching."""
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
    """Return today's date, adjusted by date_offset setting for testing."""
    offset = int(get_setting("date_offset", "0"))
    return (dt.date.today() + dt.timedelta(days=offset)).isoformat()


def now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def get_setting(key: str, default: str) -> str:
    row = get_conn().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    get_conn().execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    get_conn().commit()


def active_book_id() -> int | None:
    value = get_setting("active_book_id", "")
    try:
        return int(value) if value else None
    except ValueError:
        return None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
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
    FOREIGN KEY(book_id) REFERENCES books(id)
);

CREATE TABLE IF NOT EXISTS progress (
    word_id INTEGER PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'new',
    familiarity INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    last_seen TEXT,
    due_date TEXT,
    is_favorite INTEGER NOT NULL DEFAULT 0,
    is_wrong INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(word_id) REFERENCES words(id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_id INTEGER,
    action TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(word_id) REFERENCES words(id)
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
    word_id INTEGER PRIMARY KEY,
    crossed INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(word_id) REFERENCES pdf_words(id)
);

CREATE TABLE IF NOT EXISTS daily_session (
    date TEXT NOT NULL,
    book_id INTEGER,
    word_ids TEXT NOT NULL,
    studied_ids TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    PRIMARY KEY(date, book_id)
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_progress_due ON progress(status, due_date);
CREATE INDEX IF NOT EXISTS idx_words_book_word ON words(book_id, word);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_pdf_words_source ON pdf_words(source, day, position);
"""

SAMPLE_WORDS = [
    {"word": "apple", "translation": "n. 苹果", "definition": "a round fruit with firm white flesh and red, green, or yellow skin", "example": "She packed an apple for lunch."},
    {"word": "abandon", "translation": "v. 放弃；遗弃", "definition": "to leave someone or something permanently", "example": "They had to abandon the old plan."},
    {"word": "curious", "translation": "adj. 好奇的", "definition": "eager to know or learn something", "example": "The child was curious about every new sound."},
    {"word": "efficient", "translation": "adj. 高效的", "definition": "working well without wasting time or energy", "example": "This method is more efficient than the old one."},
    {"word": "memory", "translation": "n. 记忆；回忆", "definition": "the ability to remember information or experiences", "example": "Regular review strengthens memory."},
]


def init_db() -> None:
    conn = get_conn()
    conn.executescript(SCHEMA_SQL)
    conn.executescript(INDEX_SQL)
    conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('daily_new_limit', '12')")
    row = conn.execute("SELECT count(*) AS total FROM books").fetchone()
    if row["total"] == 0:
        book_id = conn.execute(
            "INSERT INTO books(name, created_at) VALUES(?, ?)", ("Demo 示例词书", now_iso())
        ).lastrowid
        for item in SAMPLE_WORDS:
            word_id = conn.execute(
                "INSERT INTO words(book_id, word, translation, definition, example, created_at) VALUES(?, ?, ?, ?, ?, ?)",
                (book_id, item["word"].lower(), item["translation"], item["definition"], item["example"], now_iso()),
            ).lastrowid
            conn.execute("INSERT OR IGNORE INTO progress(word_id, due_date) VALUES(?, ?)", (word_id, today()))
    conn.commit()
