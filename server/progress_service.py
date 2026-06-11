"""Learning progress service for review feedback and spelling tests."""

from __future__ import annotations

import datetime as dt
import json

from .db import active_book_id, get_conn, today


VALID_ACTIONS = {"forgot", "vague", "known", "easy"}

FAMILIARITY_DELTA = {
    "forgot": -2,
    "vague": 1,
    "known": 2,
    "easy": 3,
}


def _event_time(today_str: str | None = None) -> str:
    day = today_str or today()
    return f"{day}T{dt.datetime.now().strftime('%H:%M:%S')}"


def update_memory_strength(old_strength: float, action: str, difficulty: float = 5.0) -> float:
    """Update stability-like memory strength.

    The previous project treated "known" and "easy" almost the same. This
    version separates the four buttons more clearly while keeping the same UI.
    """
    old = max(float(old_strength or 1.0), 0.5)
    hard_factor = max(0.0, min(float(difficulty or 5.0), 10.0)) / 10.0

    if action == "forgot":
        new_strength = old - max(0.55, old * (0.22 + hard_factor * 0.08))
    elif action == "vague":
        new_strength = old + 0.35
    elif action == "known":
        new_strength = old + 1.15 - hard_factor * 0.15
    elif action == "easy":
        new_strength = old + 1.95 - hard_factor * 0.2
    else:
        new_strength = old

    return round(min(max(new_strength, 0.5), 30.0), 2)


def update_difficulty(old_difficulty: float, action: str) -> float:
    difficulty = float(old_difficulty or 5.0)
    if action == "forgot":
        difficulty += 0.6
    elif action == "vague":
        difficulty += 0.2
    elif action == "known":
        difficulty -= 0.25
    elif action == "easy":
        difficulty -= 0.55
    return round(min(max(difficulty, 1.0), 10.0), 2)


def review_interval_days(strength: float, difficulty: float, action: str, review_count: int) -> int:
    """Return the next review interval in days.

    Intervals are intentionally action-aware so the four feedback buttons map
    to a result users can feel: forgot soon, easy meaningfully later.
    """
    s = max(float(strength or 1.0), 0.5)
    d = max(1.0, min(float(difficulty or 5.0), 10.0))
    maturity = min(max(int(review_count or 0), 0), 8)

    if action == "forgot":
        return 1
    if action == "vague":
        interval = s * 0.65
        return max(1, min(10, round(interval)))
    if action == "known":
        interval = s * (1.15 + maturity * 0.04) * (1.08 - d * 0.025)
        return max(2, min(90, round(interval)))
    if action == "easy":
        interval = s * (2.0 + maturity * 0.08) * (1.14 - d * 0.025)
        return max(4, min(180, round(interval)))
    return 1


def next_due_date(action: str, strength: float, difficulty: float, review_count: int) -> str:
    base = dt.date.fromisoformat(today())
    return (base + dt.timedelta(days=review_interval_days(strength, difficulty, action, review_count))).isoformat()


def _current_session_snapshot(uid: int) -> tuple[str | None, int | None, list[int] | None]:
    conn = get_conn()
    aid = active_book_id(uid)
    session_book = aid or 0
    today_str = today()
    session = conn.execute(
        "SELECT studied_ids FROM daily_session WHERE user_id = ? AND date = ? AND book_id = ?",
        (uid, today_str, session_book),
    ).fetchone()
    if not session:
        return None, None, None
    return today_str, session_book, json.loads(session["studied_ids"])


def ensure_progress_for_book(uid: int, book_id: int | None) -> int:
    """Create missing progress rows for a user's visible words in a book."""
    if not book_id:
        return 0
    conn = get_conn()
    now = today()
    rows = conn.execute(
        """SELECT w.id
           FROM words w
           LEFT JOIN progress p ON p.word_id = w.id AND p.user_id = ?
           WHERE w.book_id = ? AND p.word_id IS NULL""",
        (uid, book_id),
    ).fetchall()
    for row in rows:
        conn.execute(
            "INSERT OR IGNORE INTO progress(user_id, word_id, due_date) VALUES(?, ?, ?)",
            (uid, row["id"], now),
        )
    if rows:
        conn.commit()
    return len(rows)


def _mastered_status(action: str, new_strength: float, review_count: int, lapse_count: int) -> str:
    if action == "forgot":
        return "learning"
    if action == "easy" and new_strength >= 5.0 and review_count >= 2 and lapse_count == 0:
        return "mastered"
    if action in {"known", "easy"} and new_strength >= 7.0 and review_count >= 3 and lapse_count <= 1:
        return "mastered"
    return "learning"


def submit_feedback(uid: int, word_id: int, action: str, *, mark_studied: bool = True) -> dict:
    """Apply learning feedback and persist the resulting schedule."""
    if action not in VALID_ACTIONS:
        raise ValueError("未知学习反馈")

    conn = get_conn()
    today_str = today()
    event_time = _event_time(today_str)

    row = conn.execute(
        """SELECT status, familiarity, memory_strength, review_count, lapse_count,
                  difficulty, attempts, correct, first_seen_at, last_seen, due_date,
                  last_grade, is_favorite, is_wrong
           FROM progress WHERE user_id = ? AND word_id = ?""",
        (uid, word_id),
    ).fetchone()
    if not row:
        conn.execute(
            "INSERT OR IGNORE INTO progress(user_id, word_id, due_date) VALUES(?, ?, ?)",
            (uid, word_id, today_str),
        )
        row = conn.execute(
            """SELECT status, familiarity, memory_strength, review_count, lapse_count,
                      difficulty, attempts, correct, first_seen_at, last_seen, due_date,
                      last_grade, is_favorite, is_wrong
               FROM progress WHERE user_id = ? AND word_id = ?""",
            (uid, word_id),
        ).fetchone()

    before_progress = dict(row)
    session_date, session_book, before_studied_ids = (
        _current_session_snapshot(uid) if mark_studied else (None, None, None)
    )

    old_strength = row["memory_strength"] or 1.0
    old_difficulty = row["difficulty"] or 5.0
    new_difficulty = update_difficulty(old_difficulty, action)
    new_strength = update_memory_strength(old_strength, action, new_difficulty)
    review_count = (row["review_count"] or 0) + 1
    lapse_count = (row["lapse_count"] or 0) + (1 if action == "forgot" else 0)
    due = next_due_date(action, new_strength, new_difficulty, review_count)
    status = _mastered_status(action, new_strength, review_count, lapse_count)
    correct_delta = 1 if action in {"known", "easy"} else 0
    wrong_flag = 1 if action == "forgot" else 0
    wrong_recovered = bool(
        row["is_wrong"]
        and action in {"known", "easy"}
        and row["last_grade"] in {"known", "easy"}
    )
    first_seen = row["first_seen_at"] or event_time

    conn.execute(
        """UPDATE progress SET
            status = ?,
            familiarity = max(0, min(10, familiarity + ?)),
            memory_strength = ?,
            review_count = ?,
            lapse_count = ?,
            difficulty = ?,
            attempts = attempts + 1,
            correct = correct + ?,
            last_seen = ?,
            due_date = ?,
            first_seen_at = ?,
            last_grade = ?,
            is_wrong = CASE WHEN ? = 1 THEN 1 WHEN ? = 1 THEN 0 ELSE is_wrong END
           WHERE user_id = ? AND word_id = ?""",
        (
            status,
            FAMILIARITY_DELTA[action],
            new_strength,
            review_count,
            lapse_count,
            new_difficulty,
            correct_delta,
            event_time,
            due,
            first_seen,
            action,
            wrong_flag,
            1 if wrong_recovered else 0,
            uid,
            word_id,
        ),
    )
    event_id = conn.execute(
        "INSERT INTO events(user_id, word_id, action, created_at) VALUES(?, ?, ?, ?)",
        (uid, word_id, action, event_time),
    ).lastrowid
    conn.execute(
        """INSERT INTO progress_snapshots(
              event_id, user_id, word_id, before_progress, session_date,
              session_book, before_studied_ids, created_at
           ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event_id,
            uid,
            word_id,
            json.dumps(before_progress, ensure_ascii=False),
            session_date,
            session_book,
            json.dumps(before_studied_ids, ensure_ascii=False) if before_studied_ids is not None else None,
            event_time,
        ),
    )

    if mark_studied:
        mark_word_studied(uid, word_id, commit=False)

    conn.commit()
    return {
        "ok": True,
        "due_date": due,
        "status": status,
        "memory_strength": new_strength,
        "difficulty": new_difficulty,
        "review_count": review_count,
        "lapse_count": lapse_count,
        "wrong_recovered": wrong_recovered,
    }


def mark_word_studied(uid: int, word_id: int, *, commit: bool = True) -> None:
    conn = get_conn()
    aid = active_book_id(uid)
    session_book = aid or 0
    today_str = today()
    session = conn.execute(
        "SELECT studied_ids FROM daily_session WHERE user_id = ? AND date = ? AND book_id = ?",
        (uid, today_str, session_book),
    ).fetchone()
    if not session:
        return
    studied = json.loads(session["studied_ids"])
    if word_id not in studied:
        studied.append(word_id)
        conn.execute(
            "UPDATE daily_session SET studied_ids = ? WHERE user_id = ? AND date = ? AND book_id = ?",
            (json.dumps(studied), uid, today_str, session_book),
        )
    if commit:
        conn.commit()


def undo_last_feedback(uid: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        """SELECT e.id AS event_id, e.word_id, e.action, s.before_progress,
                  s.session_date, s.session_book, s.before_studied_ids
           FROM events e
           JOIN progress_snapshots s ON s.event_id = e.id
           WHERE e.user_id = ?
           ORDER BY e.id DESC
           LIMIT 1""",
        (uid,),
    ).fetchone()
    if not row:
        raise ValueError("没有可撤销的学习反馈")

    before = json.loads(row["before_progress"])
    conn.execute(
        """UPDATE progress SET
            status = ?,
            familiarity = ?,
            memory_strength = ?,
            review_count = ?,
            lapse_count = ?,
            difficulty = ?,
            attempts = ?,
            correct = ?,
            last_seen = ?,
            due_date = ?,
            first_seen_at = ?,
            last_grade = ?,
            is_favorite = ?,
            is_wrong = ?
           WHERE user_id = ? AND word_id = ?""",
        (
            before.get("status", "new"),
            before.get("familiarity", 0),
            before.get("memory_strength", 1.0),
            before.get("review_count", 0),
            before.get("lapse_count", 0),
            before.get("difficulty", 5.0),
            before.get("attempts", 0),
            before.get("correct", 0),
            before.get("last_seen"),
            before.get("due_date"),
            before.get("first_seen_at"),
            before.get("last_grade"),
            before.get("is_favorite", 0),
            before.get("is_wrong", 0),
            uid,
            row["word_id"],
        ),
    )

    if row["before_studied_ids"] is not None and row["session_date"] is not None:
        conn.execute(
            """UPDATE daily_session SET studied_ids = ?
               WHERE user_id = ? AND date = ? AND book_id = ?""",
            (row["before_studied_ids"], uid, row["session_date"], row["session_book"]),
        )

    conn.execute("DELETE FROM events WHERE id = ? AND user_id = ?", (row["event_id"], uid))
    conn.commit()
    return {
        "ok": True,
        "word_id": row["word_id"],
        "action": row["action"],
        "event_id": row["event_id"],
    }
