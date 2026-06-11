"""Daily study queue scheduler."""

from __future__ import annotations

import datetime as dt
import json
from math import ceil

from .db import active_book_id, get_conn, get_setting, now_iso, today
from .ebbinghaus import RETENTION_THRESHOLD, calc_retention
from .progress_service import ensure_progress_for_book


DEFAULT_REVIEW_LIMIT = 80


def _days_since(last_seen: str | None, today_date: dt.date) -> int:
    if not last_seen:
        return 0
    try:
        return max(0, (today_date - dt.date.fromisoformat(last_seen[:10])).days)
    except (ValueError, IndexError):
        return 0


def _is_due(row, today_str: str, today_date: dt.date) -> tuple[bool, float, int]:
    strength = row["memory_strength"] or 1.0
    days = _days_since(row["last_seen"], today_date)
    retention = calc_retention(strength, days)
    due_date = row["due_date"]
    due_by_date = bool(due_date and due_date <= today_str)
    due_by_retention = retention < RETENTION_THRESHOLD
    return due_by_date or due_by_retention, retention, days


def _effective_new_limit(configured_limit: int, review_count: int) -> int:
    """Protect users from runaway review load without changing the setting."""
    if review_count >= 150:
        return 0
    if review_count >= 80:
        return max(1, ceil(configured_limit / 2))
    return configured_limit


def _load_message(configured_limit: int, effective_limit: int, review_count: int) -> dict:
    if review_count >= 150:
        return {
            "level": "severe",
            "message": "今日复习压力很高，已暂停新词",
            "review_count": review_count,
            "effective_new_limit": effective_limit,
            "configured_new_limit": configured_limit,
        }
    if effective_limit < configured_limit:
        return {
            "level": "heavy",
            "message": "今日复习较多，已自动减少新词",
            "review_count": review_count,
            "effective_new_limit": effective_limit,
            "configured_new_limit": configured_limit,
        }
    return {
        "level": "normal",
        "message": "",
        "review_count": review_count,
        "effective_new_limit": effective_limit,
        "configured_new_limit": configured_limit,
    }


def due_review_ids(uid: int, book_id: int | None, limit: int = DEFAULT_REVIEW_LIMIT) -> list[int]:
    conn = get_conn()
    today_str = today()
    today_date = dt.date.fromisoformat(today_str)
    params = [uid]
    book_filter = ""
    if book_id:
        book_filter = "AND w.book_id = ?"
        params.append(book_id)

    rows = conn.execute(
        f"""SELECT w.id, p.memory_strength, p.last_seen, p.due_date
            FROM words w
            JOIN progress p ON p.word_id = w.id AND p.user_id = ?
            WHERE p.status != 'new' {book_filter}""",
        tuple(params),
    ).fetchall()

    due = []
    for row in rows:
        is_due, retention, days = _is_due(row, today_str, today_date)
        if is_due:
            due.append({
                "id": row["id"],
                "retention": retention,
                "days": days,
                "due_date": row["due_date"] or "",
            })

    due.sort(key=lambda x: (x["retention"], x["due_date"], x["id"]))
    return [item["id"] for item in due[:limit]]


def new_word_ids(uid: int, book_id: int | None, limit: int) -> list[int]:
    if limit <= 0:
        return []
    conn = get_conn()
    params = [uid]
    book_filter = ""
    if book_id:
        book_filter = "AND w.book_id = ?"
        params.append(book_id)
    params.append(limit)

    rows = conn.execute(
        f"""SELECT w.id
            FROM words w
            JOIN progress p ON p.word_id = w.id AND p.user_id = ?
            WHERE p.status = 'new' {book_filter}
            ORDER BY w.id ASC
            LIMIT ?""",
        tuple(params),
    ).fetchall()
    return [row["id"] for row in rows]


def build_today_session(uid: int) -> dict:
    """Return today's stable queue, adding newly due reviews when needed."""
    conn = get_conn()
    book_id = active_book_id(uid)
    session_book = book_id or 0
    today_str = today()
    configured_limit = int(get_setting("daily_new_limit", "15", user_id=uid))

    ensure_progress_for_book(uid, book_id)

    session = conn.execute(
        "SELECT word_ids, studied_ids FROM daily_session WHERE user_id = ? AND date = ? AND book_id = ?",
        (uid, today_str, session_book),
    ).fetchone()

    if session:
        word_ids = json.loads(session["word_ids"])
        studied_ids = set(json.loads(session["studied_ids"]))

        existing = set(word_ids)
        due_now = due_review_ids(uid, book_id, limit=10000)
        newly_due = [wid for wid in due_now if wid not in existing and wid not in studied_ids]
        effective_limit = _effective_new_limit(configured_limit, len(due_now))
        if newly_due:
            word_ids = newly_due + word_ids
            conn.execute(
                "UPDATE daily_session SET word_ids = ? WHERE user_id = ? AND date = ? AND book_id = ?",
                (json.dumps(word_ids), uid, today_str, session_book),
            )
            conn.commit()
    else:
        due_now = due_review_ids(uid, book_id, limit=10000)
        reviews = due_now[:DEFAULT_REVIEW_LIMIT]
        effective_limit = _effective_new_limit(configured_limit, len(due_now))
        new_words = new_word_ids(uid, book_id, effective_limit)
        word_ids = reviews + new_words
        studied_ids = set()
        if word_ids:
            conn.execute(
                """INSERT INTO daily_session(user_id, date, book_id, word_ids, studied_ids, created_at)
                   VALUES(?, ?, ?, ?, ?, ?)""",
                (uid, today_str, session_book, json.dumps(word_ids), "[]", now_iso()),
            )
            conn.commit()

    return {
        "word_ids": word_ids,
        "studied_ids": studied_ids,
        "daily_new_limit": configured_limit,
        "review_load": _load_message(configured_limit, effective_limit, len(due_now)),
        "active_book_id": book_id,
    }


def review_forecast(uid: int, days: int = 7) -> list[dict]:
    conn = get_conn()
    book_id = active_book_id(uid)
    ensure_progress_for_book(uid, book_id)

    today_str = today()
    today_date = dt.date.fromisoformat(today_str)
    end_date = today_date + dt.timedelta(days=max(1, days) - 1)
    params = [uid]
    book_filter = ""
    if book_id:
        book_filter = "AND w.book_id = ?"
        params.append(book_id)

    rows = conn.execute(
        f"""SELECT p.due_date
            FROM progress p
            JOIN words w ON w.id = p.word_id
            WHERE p.user_id = ? AND p.status != 'new'
              AND p.due_date IS NOT NULL {book_filter}""",
        tuple(params),
    ).fetchall()

    buckets = {}
    for i in range(days):
        day = today_date + dt.timedelta(days=i)
        buckets[day.isoformat()] = 0

    for row in rows:
        due = row["due_date"]
        if not due:
            continue
        try:
            due_date = dt.date.fromisoformat(due[:10])
        except (ValueError, IndexError):
            continue
        if due_date < today_date:
            buckets[today_str] += 1
        elif today_date <= due_date <= end_date:
            buckets[due_date.isoformat()] += 1

    return [
        {
            "date": day,
            "count": count,
            "label": "今天" if day == today_str else day[5:],
        }
        for day, count in buckets.items()
    ]
