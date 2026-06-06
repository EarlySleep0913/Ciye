"""词页 (CiYe) — Main HTTP server with optimized routing and word enrichment."""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import sqlite3
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .db import (
    APP_DB, DATA_DIR, ROOT, active_book_id, get_conn, get_setting, init_db,
    now_iso, query_ecdict, set_setting, today,
)
from .dict import lookup_word, query_free_dictionary
from .pexels import check_pexels_status, search_pexels

PUBLIC_DIR = ROOT / "public"
HOST = "127.0.0.1"
PORT = int(os.environ.get("CIYE_PORT", "8765"))

REVIEW_INTERVALS = {"forgot": 1, "vague": 2, "known": 4, "easy": 7}
FAMILIARITY_DELTA = {"forgot": -1, "vague": 1, "known": 2, "easy": 3}


def _row_field(record, field: str):
    """Get field from sqlite3.Row or dict without repetitive isinstance checks."""
    return record[field] if hasattr(record, '__getitem__') and not isinstance(record, dict) else record.get(field, "")


def enrich_word(record, include_photo: bool = True) -> dict:
    """Enrich a word record with ECDICT, Free Dictionary, and Pexels data."""
    word = str(_row_field(record, "word")).strip().lower()
    base = {
        "id": _row_field(record, "id"),
        "word": word,
        "translation": _row_field(record, "translation") or "",
        "definition": _row_field(record, "definition") or "",
        "phonetic": _row_field(record, "phonetic") or "",
        "example": _row_field(record, "example") or "",
        "audio_url": _row_field(record, "audio_url") or "",
        "image_url": _row_field(record, "image_url") or "",
    }
    # Fill missing fields from ECDICT
    ecdict = query_ecdict(word)
    for key in ("translation", "definition", "phonetic"):
        if not base[key] and ecdict.get(key):
            base[key] = ecdict[key]
    # Fill missing fields from Free Dictionary API
    if not base["definition"] or not base["phonetic"] or not base["audio_url"] or not base["example"]:
        online = query_free_dictionary(word)
        for key in ("definition", "phonetic", "audio_url", "example"):
            if not base[key] and online.get(key):
                base[key] = online[key]
    # Fill image from Pexels
    if include_photo and not base["image_url"]:
        base["image_url"] = search_pexels(word)
    if not base["example"]:
        base["example"] = f"I want to remember the word {word}."
    _save_enrichment(base)
    return base


def _save_enrichment(item: dict) -> None:
    """Save enriched word data back to database."""
    if not item.get("id"):
        return
    get_conn().execute(
        """UPDATE words SET
            translation = COALESCE(NULLIF(?, ''), translation),
            definition = COALESCE(NULLIF(?, ''), definition),
            phonetic = COALESCE(NULLIF(?, ''), phonetic),
            example = COALESCE(NULLIF(?, ''), example),
            audio_url = COALESCE(NULLIF(?, ''), audio_url),
            image_url = COALESCE(NULLIF(?, ''), image_url)
        WHERE id = ?""",
        (
            item.get("translation", ""),
            item.get("definition", ""),
            item.get("phonetic", ""),
            item.get("example", ""),
            item.get("audio_url", ""),
            item.get("image_url", ""),
            item["id"],
        ),
    )
    get_conn().commit()


def _row_to_word(row, enrich: bool = False) -> dict:
    item = dict(row)
    if enrich:
        item.update(enrich_word(item))
    return item


def _json_response(handler: BaseHTTPRequestHandler, payload: object, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8")) if raw else {}


def normalize_word(word: str) -> str:
    match = re.search(r"[A-Za-z][A-Za-z'\- ]*", word)
    return match.group(0).strip().lower() if match else word.strip().lower()


def dedupe_words(rows: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for row in rows:
        w = row["word"]
        if w and w not in seen:
            seen.add(w)
            output.append(row)
    return output


def parse_import_text(text: str) -> list[dict]:
    text = text.strip("﻿ \n\r\t")
    if not text:
        return []
    first_line = text.splitlines()[0]
    delimiter = "\t" if "\t" in first_line else ","
    rows = []
    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        if reader.fieldnames and any(n.lower() in {"word", "单词", "vocabulary"} for n in reader.fieldnames):
            for row in reader:
                w = (row.get("word") or row.get("单词") or row.get("vocabulary") or "").strip()
                if w:
                    rows.append({
                        "word": normalize_word(w),
                        "translation": (row.get("translation") or row.get("中文释义") or row.get("释义") or "").strip(),
                        "definition": (row.get("definition") or row.get("英文释义") or "").strip(),
                        "example": (row.get("example") or row.get("例句") or "").strip(),
                    })
            return dedupe_words(rows)
    except csv.Error:
        pass
    for line in text.splitlines():
        parts = [p.strip() for p in re.split(r"\t|,", line) if p.strip()]
        if not parts:
            continue
        rows.append({
            "word": normalize_word(parts[0]),
            "translation": parts[1] if len(parts) > 1 else "",
            "definition": parts[2] if len(parts) > 2 else "",
            "example": parts[3] if len(parts) > 3 else "",
        })
    return dedupe_words([r for r in rows if r["word"]])


class CiYeHandler(BaseHTTPRequestHandler):
    server_version = "CiYe/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        routes = {
            "/api/health": self._health,
            "/api/books": self._books,
            "/api/settings": self._get_settings,
            "/api/today": self._today,
            "/api/stats": self._stats,
            "/api/pdf-words": self._pdf_words,
        }
        if path in routes:
            return routes[path]()
        if path == "/api/lookup":
            return self._lookup(query)
        if path.startswith("/api/"):
            return _json_response(self, {"error": "接口不存在"}, 404)
        return self._static_file(path)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        routes = {
            "/api/settings": self._set_settings,
            "/api/books/activate": self._activate_book,
            "/api/books/reset": self._reset_book_progress,
            "/api/reset-today": self._reset_today,
            "/api/pexels-key": self._save_pexels_key,
            "/api/import/preview": self._import_preview,
            "/api/books": self._create_book,
            "/api/progress": self._progress,
            "/api/favorite": self._favorite,
            "/api/pdf-words/mark": self._pdf_word_mark,
        }
        if path in routes:
            return routes[path]()
        _json_response(self, {"error": "接口不存在"}, 404)

    def _static_file(self, path: str) -> None:
        if path == "/":
            path = "/index.html"
        rel = path.lstrip("/").replace("/", os.sep)
        target = (PUBLIC_DIR / rel).resolve()
        if not str(target).startswith(str(PUBLIC_DIR.resolve())) or not target.exists():
            self.send_error(404)
            return
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_types.get(target.suffix, "text/plain; charset=utf-8"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _health(self) -> None:
        _json_response(self, {
            "ok": True,
            "ecdict": (DATA_DIR / "ecdict.db").exists(),
            "pexels": check_pexels_status(),
            "date": today(),
        })

    def _books(self) -> None:
        aid = active_book_id()
        conn = get_conn()
        rows = conn.execute(
            """SELECT b.id, b.name, b.created_at, count(w.id) AS total,
                      CASE WHEN b.id = ? THEN 1 ELSE 0 END AS active
               FROM books b LEFT JOIN words w ON w.book_id = b.id
               GROUP BY b.id ORDER BY active DESC, b.id DESC""",
            (aid or -1,),
        ).fetchall()
        books = []
        for row in rows:
            book = dict(row)
            book_id = book["id"]
            progress = conn.execute(
                """SELECT
                     sum(CASE WHEN p.status = 'new' THEN 1 ELSE 0 END) AS new_count,
                     sum(CASE WHEN p.status = 'learning' THEN 1 ELSE 0 END) AS learning_count,
                     sum(CASE WHEN p.status = 'mastered' THEN 1 ELSE 0 END) AS mastered_count
                   FROM words w JOIN progress p ON p.word_id = w.id
                   WHERE w.book_id = ?""",
                (book_id,),
            ).fetchone()
            book["new_count"] = progress["new_count"] or 0
            book["learning_count"] = progress["learning_count"] or 0
            book["mastered_count"] = progress["mastered_count"] or 0
            books.append(book)
        _json_response(self, {"books": books})

    def _get_settings(self) -> None:
        _json_response(self, {
            "daily_new_limit": int(get_setting("daily_new_limit", "12")),
            "active_book_id": active_book_id(),
            "date_offset": int(get_setting("date_offset", "0")),
            "real_date": dt.date.today().isoformat(),
            "virtual_date": today(),
        })

    def _set_settings(self) -> None:
        payload = _read_json(self)
        need_clear_session = False
        if "daily_new_limit" in payload:
            limit = max(1, min(150, int(payload["daily_new_limit"])))
            set_setting("daily_new_limit", str(limit))
            need_clear_session = True
        if "date_offset" in payload:
            set_setting("date_offset", str(int(payload["date_offset"])))
            need_clear_session = True
        if need_clear_session:
            get_conn().execute("DELETE FROM daily_session")
            get_conn().commit()
        _json_response(self, {
            "daily_new_limit": int(get_setting("daily_new_limit", "12")),
            "date_offset": int(get_setting("date_offset", "0")),
            "virtual_date": today(),
        })

    def _activate_book(self) -> None:
        payload = _read_json(self)
        book_id = payload.get("book_id")
        daily_limit = payload.get("daily_new_limit")
        if book_id:
            set_setting("active_book_id", str(int(book_id)))
        if daily_limit is not None:
            limit = max(1, min(150, int(daily_limit)))
            set_setting("daily_new_limit", str(limit))
        # Clear session when switching book or changing limit
        get_conn().execute("DELETE FROM daily_session")
        get_conn().commit()
        _json_response(self, {
            "ok": True,
            "active_book_id": int(book_id) if book_id else active_book_id(),
            "daily_new_limit": int(get_setting("daily_new_limit", "12")),
        })

    def _reset_today(self) -> None:
        """Reset today's learning: clear session and progress for today."""
        today_str = today()
        conn = get_conn()
        # Delete today's sessions
        conn.execute("DELETE FROM daily_session WHERE date = ?", (today_str,))
        # Reset progress for words studied today
        conn.execute(
            """UPDATE progress SET status = 'new', familiarity = 0, attempts = 0,
               correct = 0, last_seen = NULL, due_date = ?
               WHERE last_seen LIKE ? OR due_date = ?""",
            (today_str, f"{today_str}%", today_str),
        )
        conn.execute("DELETE FROM events WHERE created_at LIKE ?", (f"{today_str}%",))
        conn.commit()
        _json_response(self, {"ok": True, "message": "今日学习已重置"})

    def _save_pexels_key(self) -> None:
        payload = _read_json(self)
        key = (payload.get("api_key") or "").strip()
        # Save to config.json
        config_file = ROOT / "config.json"
        config = {}
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        config["pexels_api_key"] = key
        config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        # Reset pexels status cache
        from .pexels import _pexels_status_cache, _pexels_status_time
        import server.pexels as pexels_mod
        pexels_mod._pexels_status_cache = None
        pexels_mod._pexels_status_time = 0
        _json_response(self, {"ok": True, "message": "Pexels API Key 已保存"})

    def _reset_book_progress(self) -> None:
        """Reset all progress for a specific book."""
        payload = _read_json(self)
        book_id = int(payload.get("book_id", 0))
        if not book_id:
            return _json_response(self, {"error": "缺少 book_id"}, 400)
        conn = get_conn()
        conn.execute(
            """UPDATE progress SET status = 'new', familiarity = 0, attempts = 0,
               correct = 0, last_seen = NULL, due_date = ?
               WHERE word_id IN (SELECT id FROM words WHERE book_id = ?)""",
            (today(), book_id),
        )
        conn.execute(
            "DELETE FROM events WHERE word_id IN (SELECT id FROM words WHERE book_id = ?)",
            (book_id,),
        )
        conn.commit()
        _json_response(self, {"ok": True, "message": "词书学习进度已重置"})

    def _today(self) -> None:
        limit = int(get_setting("daily_new_limit", "12"))
        aid = active_book_id()
        conn = get_conn()
        today_str = today()
        session_book = aid or 0

        # Check if session already exists for today
        session = conn.execute(
            "SELECT word_ids, studied_ids FROM daily_session WHERE date = ? AND book_id = ?",
            (today_str, session_book),
        ).fetchone()

        if session:
            # Session exists — use saved queue
            word_ids = json.loads(session["word_ids"])
            studied_ids = set(json.loads(session["studied_ids"]))
        else:
            # Create new session
            book_filter = "AND w.book_id = ?" if aid else ""
            review_params = [today_str, today_str]
            new_params = []
            if aid:
                review_params.append(aid)
                new_params.append(aid)
            new_params.append(limit)

            review_rows = conn.execute(
                f"""SELECT w.id FROM progress p JOIN words w ON w.id = p.word_id
                    WHERE p.status != 'new' AND coalesce(p.due_date, ?) <= ?
                    {book_filter}
                    ORDER BY p.due_date ASC, p.familiarity ASC LIMIT 50""",
                tuple(review_params),
            ).fetchall()
            new_rows = conn.execute(
                f"""SELECT w.id FROM words w JOIN progress p ON p.word_id = w.id
                    WHERE p.status = 'new'
                    {book_filter}
                    ORDER BY w.id ASC LIMIT ?""",
                tuple(new_params),
            ).fetchall()

            word_ids = [r["id"] for r in review_rows] + [r["id"] for r in new_rows]
            studied_ids = set()

            conn.execute(
                "INSERT INTO daily_session(date, book_id, word_ids, studied_ids, created_at) VALUES(?, ?, ?, ?, ?)",
                (today_str, session_book, json.dumps(word_ids), "[]", now_iso()),
            )
            conn.commit()

        # Fetch full word data for the session
        if not word_ids:
            _json_response(self, {
                "daily_new_limit": limit, "active_book_id": aid,
                "reviews": [], "new_words": [],
            })
            return

        placeholders = ",".join("?" for _ in word_ids)
        rows = conn.execute(
            f"""SELECT w.*, p.status, p.familiarity, p.due_date, p.is_favorite, p.is_wrong
                FROM words w JOIN progress p ON p.word_id = w.id
                WHERE w.id IN ({placeholders})""",
            word_ids,
        ).fetchall()
        row_map = {r["id"]: r for r in rows}

        reviews = []
        new_words = []
        for wid in word_ids:
            if wid not in row_map:
                continue
            row = row_map[wid]
            item = _row_to_word(row)
            if wid in studied_ids:
                item["studied_today"] = True
            # Classify based on original status at session creation
            if row["status"] != "new":
                reviews.append(item)
            else:
                new_words.append(item)

        _json_response(self, {
            "daily_new_limit": limit, "active_book_id": aid,
            "reviews": reviews, "new_words": new_words,
        })

    def _lookup(self, query: dict) -> None:
        word = normalize_word((query.get("word") or [""])[0])
        if not word:
            return _json_response(self, {"error": "缺少 word 参数"}, 400)
        row = get_conn().execute(
            "SELECT * FROM words WHERE lower(word) = lower(?) ORDER BY id DESC LIMIT 1", (word,)
        ).fetchone()
        if row:
            item = _row_to_word(row, enrich=True)
        else:
            enriched = lookup_word(word)
            enriched["id"] = None
            enriched["image_url"] = ""
            item = enriched
        _json_response(self, item)

    def _stats(self) -> None:
        aid = active_book_id()
        book_filter = "WHERE w.book_id = ?" if aid else ""
        params = (aid,) if aid else ()
        conn = get_conn()
        counts = conn.execute(
            f"""SELECT
                    count(*) AS total,
                    sum(CASE WHEN p.status = 'new' THEN 1 ELSE 0 END) AS new_total,
                    sum(CASE WHEN p.status = 'learning' THEN 1 ELSE 0 END) AS learning,
                    sum(CASE WHEN p.status = 'mastered' THEN 1 ELSE 0 END) AS mastered,
                    sum(CASE WHEN p.is_wrong = 1 THEN 1 ELSE 0 END) AS wrong_total
                FROM words w JOIN progress p ON p.word_id = w.id
                {book_filter}""",
            params,
        ).fetchone()
        events = conn.execute(
            """SELECT substr(created_at, 1, 10) AS day, count(*) AS total
               FROM events WHERE action IN ('forgot', 'vague', 'known', 'easy')
               GROUP BY substr(created_at, 1, 10)
               ORDER BY day DESC LIMIT 14"""
        ).fetchall()
        _json_response(self, {"counts": dict(counts), "events": [dict(r) for r in events]})

    def _pdf_words(self) -> None:
        rows = get_conn().execute(
            """SELECT pw.id, pw.day, pw.position, pw.word, pw.translation,
                      coalesce(pwm.crossed, 0) AS crossed, pwm.updated_at
               FROM pdf_words pw
               LEFT JOIN pdf_word_marks pwm ON pwm.word_id = pw.id
               WHERE pw.source = 'cet4_pdf'
               ORDER BY pw.day ASC, pw.position ASC, pw.id ASC"""
        ).fetchall()
        days, by_day, crossed_total = [], {}, 0
        for row in rows:
            item = dict(row)
            item["crossed"] = bool(item["crossed"])
            if item["crossed"]:
                crossed_total += 1
            d = item["day"]
            if d not in by_day:
                by_day[d] = {"day": d, "words": []}
                days.append(by_day[d])
            by_day[d]["words"].append(item)
        _json_response(self, {"source": "cet4_pdf", "total": len(rows), "crossed_total": crossed_total, "days": days})

    def _pdf_word_mark(self) -> None:
        payload = _read_json(self)
        word_id = int(payload.get("word_id", 0))
        crossed = 1 if payload.get("crossed") else 0
        conn = get_conn()
        exists = conn.execute("SELECT id FROM pdf_words WHERE id = ? AND source = 'cet4_pdf'", (word_id,)).fetchone()
        if not exists:
            return _json_response(self, {"error": "word not found"}, 404)
        conn.execute(
            """INSERT INTO pdf_word_marks(word_id, crossed, updated_at) VALUES(?, ?, ?)
               ON CONFLICT(word_id) DO UPDATE SET crossed = excluded.crossed, updated_at = excluded.updated_at""",
            (word_id, crossed, now_iso()),
        )
        conn.commit()
        _json_response(self, {"ok": True, "word_id": word_id, "crossed": bool(crossed)})

    def _import_preview(self) -> None:
        payload = _read_json(self)
        rows = parse_import_text(payload.get("text", ""))
        _json_response(self, {"words": rows[:500], "total": len(rows)})

    def _create_book(self) -> None:
        payload = _read_json(self)
        name = (payload.get("name") or f"导入词书 {today()}").strip()
        words = payload.get("words") or []
        if not words:
            return _json_response(self, {"error": "没有可导入的单词"}, 400)
        conn = get_conn()
        book_id = conn.execute("INSERT INTO books(name, created_at) VALUES(?, ?)", (name, now_iso())).lastrowid
        inserted = 0
        for item in words:
            word = normalize_word(str(item.get("word", "")))
            if not word:
                continue
            try:
                word_id = conn.execute(
                    """INSERT INTO words(book_id, word, translation, definition, example, created_at)
                       VALUES(?, ?, ?, ?, ?, ?)""",
                    (book_id, word, item.get("translation", ""), item.get("definition", ""), item.get("example", ""), now_iso()),
                ).lastrowid
            except sqlite3.IntegrityError:
                continue
            conn.execute("INSERT OR IGNORE INTO progress(word_id, due_date) VALUES(?, ?)", (word_id, today()))
            inserted += 1
        conn.commit()
        _json_response(self, {"book_id": book_id, "inserted": inserted})

    def _progress(self) -> None:
        payload = _read_json(self)
        word_id = int(payload.get("word_id", 0))
        action = str(payload.get("action", "vague"))
        if action not in REVIEW_INTERVALS:
            return _json_response(self, {"error": "未知学习反馈"}, 400)
        interval = REVIEW_INTERVALS[action]
        today_str = today()
        due = (dt.date.fromisoformat(today_str) + dt.timedelta(days=interval)).isoformat()
        correct = 1 if action in {"known", "easy"} else 0
        wrong = 1 if action == "forgot" else 0
        status = "mastered" if action == "easy" else "learning"
        delta = FAMILIARITY_DELTA[action]
        conn = get_conn()
        conn.execute(
            """UPDATE progress SET
                status = ?, familiarity = max(0, min(10, familiarity + ?)),
                attempts = attempts + 1, correct = correct + ?,
                last_seen = ?, due_date = ?,
                is_wrong = CASE WHEN ? = 1 THEN 1 ELSE is_wrong END
               WHERE word_id = ?""",
            (status, delta, correct, now_iso(), due, wrong, word_id),
        )
        conn.execute("INSERT INTO events(word_id, action, created_at) VALUES(?, ?, ?)", (word_id, action, now_iso()))

        # Mark word as studied in today's session
        aid = active_book_id()
        session_book = aid or 0
        session = conn.execute(
            "SELECT studied_ids FROM daily_session WHERE date = ? AND book_id = ?",
            (today_str, session_book),
        ).fetchone()
        if session:
            studied = json.loads(session["studied_ids"])
            if word_id not in studied:
                studied.append(word_id)
            conn.execute(
                "UPDATE daily_session SET studied_ids = ? WHERE date = ? AND book_id = ?",
                (json.dumps(studied), today_str, session_book),
            )

        conn.commit()
        _json_response(self, {"ok": True, "due_date": due, "status": status})

    def _favorite(self) -> None:
        payload = _read_json(self)
        word_id = int(payload.get("word_id", 0))
        favorite = 1 if payload.get("favorite") else 0
        get_conn().execute("UPDATE progress SET is_favorite = ? WHERE word_id = ?", (favorite, word_id))
        get_conn().commit()
        _json_response(self, {"ok": True, "favorite": favorite})


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), CiYeHandler)
    print(f"词页 (CiYe) 已启动: http://{HOST}:{PORT}")
    print("按 Ctrl+C 停止服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        server.server_close()
        from .db import close_pool
        close_pool()


if __name__ == "__main__":
    main()
