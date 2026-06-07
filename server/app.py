"""词页 (CiYe) — HTTP server with per-user data isolation."""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import sqlite3
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .db import (
    APP_DB, DATA_DIR, ROOT, active_book_id, get_conn, get_setting, init_db,
    now_iso, query_ecdict, set_setting, today,
)
from .dict import lookup_word, query_free_dictionary
from .pexels import check_pexels_status, search_pexels
from .auth import (
    get_current_user, handle_login, handle_register, handle_me,
    handle_list_users, handle_update_role, handle_delete_user,
)
from .ebbinghaus import (
    update_memory_strength, calc_next_review, calc_retention, RETENTION_THRESHOLD,
    handle_ebbinghaus_overview, handle_ebbinghaus_word, handle_ebbinghaus_review_queue,
)

PUBLIC_DIR = ROOT / "public"
HOST = "127.0.0.1"
PORT = int(os.environ.get("CIYE_PORT", "8765"))

REVIEW_INTERVALS = {"forgot": 1, "vague": 2, "known": 4, "easy": 7}
FAMILIARITY_DELTA = {"forgot": -1, "vague": 1, "known": 2, "easy": 3}


# ── Helpers ──

def _row_field(record, field: str):
    return record[field] if hasattr(record, '__getitem__') and not isinstance(record, dict) else record.get(field, "")


def enrich_word(record, include_photo: bool = True) -> dict:
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
    ecdict = query_ecdict(word)
    for key in ("translation", "definition", "phonetic"):
        if not base[key] and ecdict.get(key):
            base[key] = ecdict[key]
    need_online = (
        not base["definition"] or not base["phonetic"]
        or not base["audio_url"] or not base["example"]
    )
    if need_online:
        online = query_free_dictionary(word)
        for key in ("definition", "phonetic", "audio_url", "example"):
            if not base[key] and online.get(key):
                base[key] = online[key]
    if include_photo and not base["image_url"]:
        base["image_url"] = search_pexels(word)
    _save_enrichment(base)
    return base


def _save_enrichment(item: dict) -> None:
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
        (item.get("translation", ""), item.get("definition", ""),
         item.get("phonetic", ""), item.get("example", ""),
         item.get("audio_url", ""), item.get("image_url", ""), item["id"]),
    )
    get_conn().commit()


def _enrich_single_word(word_id: int) -> None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM words WHERE id = ?", (word_id,)).fetchone()
    if not row:
        return
    example = (row["example"] or "").strip()
    has_template = "remember the word" in example.lower()
    needs = (
        not (row["image_url"] or "").strip()
        or not example or has_template
        or not (row["audio_url"] or "").strip()
    )
    if not needs:
        return
    try:
        item = dict(row)
        if has_template:
            item["example"] = ""
        enrich_word(item, include_photo=True)
    except Exception:
        pass


def _bg_enrich_images(word_ids: list[int]) -> None:
    conn = get_conn()
    missing = []
    for wid in word_ids:
        row = conn.execute("SELECT image_url, example FROM words WHERE id = ?", (wid,)).fetchone()
        if row and (not (row["image_url"] or "").strip() or not (row["example"] or "").strip()):
            missing.append(wid)
    if not missing:
        return
    def _run():
        for wid in missing:
            _enrich_single_word(wid)
    threading.Thread(target=_run, daemon=True).start()


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


def _clean_example(text: str) -> str:
    """Filter out template examples."""
    if not text:
        return ""
    t = text.strip()
    if "remember the word" in t.lower():
        return ""
    return t


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
                        "example": _clean_example(row.get("example") or row.get("例句") or ""),
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


# ── HTTP Handler ──

class CiYeHandler(BaseHTTPRequestHandler):
    server_version = "CiYe/1.0"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _require_user(self) -> dict | None:
        user = get_current_user(self)
        if not user:
            _json_response(self, {"error": "未登录"}, 401)
        return user

    def do_GET(self) -> None:
      try:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Static files — no auth needed
        if not path.startswith("/api/"):
            return self._static_file(path)

        # Public API routes
        if path == "/api/health":
            return self._health()
        if path.startswith("/api/auth/"):
            if path == "/api/auth/me":
                return handle_me(self)
            return _json_response(self, {"error": "接口不存在"}, 404)

        # Auth required for all other API routes
        user = self._require_user()
        if not user:
            return

        uid = user["id"]
        routes = {
            "/api/books": lambda: self._books(uid),
            "/api/settings": lambda: self._get_settings(uid),
            "/api/today": lambda: self._today(uid),
            "/api/stats": lambda: self._stats(uid),
            "/api/heatmap": lambda: self._heatmap(uid),
            "/api/pdf-words": lambda: self._pdf_words(uid),
            "/api/wrong-words": lambda: self._wrong_words(uid),
            "/api/favorites": lambda: self._favorites(uid),
            "/api/test/words": lambda: self._test_words(uid, query),
            "/api/ebbinghaus": lambda: handle_ebbinghaus_overview(self, uid),
            "/api/ebbinghaus/review": lambda: handle_ebbinghaus_review_queue(self, uid),
            "/api/ai/settings": lambda: self._get_ai_settings(),
            "/api/users": lambda: handle_list_users(self),
        }
        if path in routes:
            return routes[path]()
        if path == "/api/lookup":
            return self._lookup(query)
        if path.startswith("/api/ebbinghaus/word/"):
            try:
                wid = int(path.split("/")[-1])
                return handle_ebbinghaus_word(self, uid, wid)
            except (ValueError, IndexError):
                return _json_response(self, {"error": "参数错误"}, 400)
        if path.startswith("/api/books/") and path.endswith("/words"):
            try:
                bid = int(path.split("/")[3])
                return self._book_words(uid, bid, query)
            except (ValueError, IndexError):
                return _json_response(self, {"error": "参数错误"}, 400)
        if path.startswith("/api/"):
            return _json_response(self, {"error": "接口不存在"}, 404)
        return self._static_file(path)
      except Exception as e:
        try:
          _json_response(self, {"error": f"服务器错误: {e}"}, 500)
        except Exception:
          pass

    def do_POST(self) -> None:
      try:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Public routes
        if path == "/api/auth/login":
            return handle_login(self)
        if path == "/api/auth/register":
            return handle_register(self)

        # Auth required
        user = self._require_user()
        if not user:
            return

        uid = user["id"]
        routes = {
            "/api/settings": lambda: self._set_settings(uid),
            "/api/books/activate": lambda: self._activate_book(uid),
            "/api/books/reset": lambda: self._reset_book_progress(uid),
            "/api/reset-today": lambda: self._reset_today(uid),
            "/api/pexels-key": lambda: self._save_pexels_key(user),
            "/api/import/preview": lambda: self._import_preview(),
            "/api/books": lambda: self._create_book(uid),
            "/api/progress": lambda: self._progress(uid),
            "/api/favorite": lambda: self._favorite(uid),
            "/api/wrong-words/remove": lambda: self._wrong_words_remove(uid),
            "/api/test/check": lambda: self._test_check(uid),
            "/api/pdf-words/mark": lambda: self._pdf_word_mark(uid),
            "/api/users/role": lambda: handle_update_role(self),
            "/api/ai/generate": lambda: self._ai_generate(uid),
            "/api/ai/settings": lambda: self._save_ai_settings(user),
        }
        if path in routes:
            return routes[path]()
        # DELETE user via POST (simpler)
        if path.startswith("/api/users/") and path.endswith("/delete"):
            try:
                target_id = int(path.split("/")[3])
                return handle_delete_user(self, target_id)
            except (ValueError, IndexError):
                pass
        _json_response(self, {"error": "接口不存在"}, 404)
      except Exception as e:
        try:
          _json_response(self, {"error": f"服务器错误: {e}"}, 500)
        except Exception:
          pass

    def do_PUT(self) -> None:
      try:
        user = self._require_user()
        if not user:
            return
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        uid = user["id"]
        if path.startswith("/api/words/"):
            try:
                wid = int(path.split("/")[3])
                return self._word_edit(uid, wid)
            except (ValueError, IndexError):
                pass
        if path.startswith("/api/books/"):
            try:
                bid = int(path.split("/")[3])
                return self._book_rename(uid, bid)
            except (ValueError, IndexError):
                pass
        _json_response(self, {"error": "接口不存在"}, 404)
      except Exception as e:
        try:
            _json_response(self, {"error": f"服务器错误: {e}"}, 500)
        except Exception:
            pass

    def do_DELETE(self) -> None:
      try:
        user = self._require_user()
        if not user:
            return
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        uid = user["id"]
        if path.startswith("/api/words/"):
            try:
                wid = int(path.split("/")[3])
                return self._word_delete(uid, wid)
            except (ValueError, IndexError):
                pass
        if path.startswith("/api/books/") and path.endswith("/delete"):
            try:
                bid = int(path.split("/")[3])
                return self._book_delete(uid, bid)
            except (ValueError, IndexError):
                pass
        _json_response(self, {"error": "接口不存在"}, 404)
      except Exception as e:
        try:
            _json_response(self, {"error": f"服务器错误: {e}"}, 500)
        except Exception:
            pass

    # ── Book & Word management ──

    def _book_words(self, uid: int, book_id: int, query: dict) -> None:
        """Get paginated words in a book."""
        page = int((query.get("page") or ["1"])[0])
        per_page = int((query.get("per_page") or ["50"])[0])
        per_page = min(per_page, 200)
        offset = (page - 1) * per_page
        conn = get_conn()
        # Verify book belongs to user
        book = conn.execute("SELECT id FROM books WHERE id = ? AND user_id = ?", (book_id, uid)).fetchone()
        if not book:
            return _json_response(self, {"error": "词书不存在"}, 404)
        total = conn.execute("SELECT count(*) AS c FROM words WHERE book_id = ?", (book_id,)).fetchone()["c"]
        rows = conn.execute(
            """SELECT w.id, w.word, w.translation, w.definition, w.phonetic, w.example,
                      p.status, p.familiarity, p.memory_strength
               FROM words w LEFT JOIN progress p ON p.word_id = w.id AND p.user_id = ?
               WHERE w.book_id = ?
               ORDER BY w.id ASC LIMIT ? OFFSET ?""",
            (uid, book_id, per_page, offset),
        ).fetchall()
        _json_response(self, {
            "words": [dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        })

    def _get_ai_settings(self) -> None:
        _json_response(self, {
            "ai_api_url": get_setting("ai_api_url", "", user_id=0),
            "ai_api_key": get_setting("ai_api_key", "", user_id=0),
            "ai_model": get_setting("ai_model", "Pro/moonshotai/Kimi-K2.6", user_id=0),
        })

    def _save_ai_settings(self, user: dict) -> None:
        if user["role"] != "admin":
            return _json_response(self, {"error": "仅管理员可修改"}, 403)
        payload = _read_json(self)
        if "ai_api_url" in payload:
            set_setting("ai_api_url", payload["ai_api_url"].strip(), user_id=0)
        if "ai_api_key" in payload:
            set_setting("ai_api_key", payload["ai_api_key"].strip(), user_id=0)
        if "ai_model" in payload:
            set_setting("ai_model", payload["ai_model"].strip(), user_id=0)
        _json_response(self, {"ok": True})

    def _ai_generate(self, uid: int) -> None:
        """Call AI API to convert text to CSV."""
        payload = _read_json(self)
        text = payload.get("text", "").strip()
        if not text:
            return _json_response(self, {"error": "请输入文本"}, 400)

        api_url = get_setting("ai_api_url", "", user_id=0)
        api_key = get_setting("ai_api_key", "", user_id=0)
        model = get_setting("ai_model", "Pro/moonshotai/Kimi-K2.6", user_id=0)

        if not api_url or not api_key:
            return _json_response(self, {"error": "请先在设置中配置 AI API"}, 400)

        prompt = """请把我提供的英语单词资料整理成标准 CSV。
要求：
1. 只输出 CSV，不要解释。
2. 表头固定为：word,translation,definition,example
3. word 只保留英文单词或短语，统一小写。
4. translation 写中文释义，definition 写英文释义，example 写一句英文例句。
5. 如果原资料缺少某列，请合理补全；不确定时留空。
6. 确保 CSV 格式正确，字段中如有逗号请用英文双引号包裹。

待整理内容：
""" + text

        try:
            import json as _json
            req_body = _json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 4096,
            }).encode("utf-8")

            req = urllib.request.Request(
                api_url,
                data=req_body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = _json.loads(resp.read().decode("utf-8"))

            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            # Clean up: remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            # Remove "csv" header if present
            if content.lower().startswith("csv\n"):
                content = content[4:]

            _json_response(self, {"csv": content})
        except Exception as e:
            _json_response(self, {"error": f"AI 调用失败: {e}"}, 500)

    def _word_edit(self, uid: int, word_id: int) -> None:
        """Edit a word's translation, definition, example."""
        payload = _read_json(self)
        conn = get_conn()
        # Verify word belongs to user's book
        word = conn.execute(
            "SELECT w.id FROM words w JOIN books b ON b.id = w.book_id WHERE w.id = ? AND b.user_id = ?",
            (word_id, uid),
        ).fetchone()
        if not word:
            return _json_response(self, {"error": "单词不存在"}, 404)
        fields = []
        params = []
        for key in ("translation", "definition", "example", "phonetic"):
            if key in payload:
                fields.append(f"{key} = ?")
                params.append(payload[key])
        if fields:
            params.append(word_id)
            conn.execute(f"UPDATE words SET {', '.join(fields)} WHERE id = ?", params)
            conn.commit()
        _json_response(self, {"ok": True})

    def _word_delete(self, uid: int, word_id: int) -> None:
        """Delete a word from a book."""
        conn = get_conn()
        word = conn.execute(
            "SELECT w.id, w.book_id FROM words w JOIN books b ON b.id = w.book_id WHERE w.id = ? AND b.user_id = ?",
            (word_id, uid),
        ).fetchone()
        if not word:
            return _json_response(self, {"error": "单词不存在"}, 404)
        conn.execute("DELETE FROM events WHERE word_id = ?", (word_id,))
        conn.execute("DELETE FROM progress WHERE word_id = ?", (word_id,))
        conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
        conn.commit()
        _json_response(self, {"ok": True})

    def _book_rename(self, uid: int, book_id: int) -> None:
        """Rename a book."""
        payload = _read_json(self)
        name = (payload.get("name") or "").strip()
        if not name:
            return _json_response(self, {"error": "名称不能为空"}, 400)
        conn = get_conn()
        book = conn.execute("SELECT id FROM books WHERE id = ? AND user_id = ?", (book_id, uid)).fetchone()
        if not book:
            return _json_response(self, {"error": "词书不存在"}, 404)
        conn.execute("UPDATE books SET name = ? WHERE id = ?", (name, book_id))
        conn.commit()
        _json_response(self, {"ok": True})

    def _book_delete(self, uid: int, book_id: int) -> None:
        """Delete a book and all its words."""
        conn = get_conn()
        book = conn.execute("SELECT id FROM books WHERE id = ? AND user_id = ?", (book_id, uid)).fetchone()
        if not book:
            return _json_response(self, {"error": "词书不存在"}, 404)
        word_ids = [r["id"] for r in conn.execute("SELECT id FROM words WHERE book_id = ?", (book_id,)).fetchall()]
        if word_ids:
            placeholders = ",".join("?" for _ in word_ids)
            conn.execute(f"DELETE FROM events WHERE word_id IN ({placeholders})", word_ids)
            conn.execute(f"DELETE FROM progress WHERE word_id IN ({placeholders})", word_ids)
            conn.execute(f"DELETE FROM words WHERE id IN ({placeholders})", word_ids)
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        # If deleted book was active, clear active_book_id
        if active_book_id(uid) == book_id:
            conn.execute("DELETE FROM settings WHERE user_id = ? AND key = 'active_book_id'", (uid,))
        conn.commit()
        _json_response(self, {"ok": True})

    # ── Static files ──

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

    # ── API endpoints (user-scoped) ──

    def _health(self) -> None:
        _json_response(self, {
            "ok": True,
            "ecdict": (DATA_DIR / "ecdict.db").exists(),
            "pexels": check_pexels_status(),
            "date": today(),
        })

    def _books(self, uid: int) -> None:
        aid = active_book_id(uid)
        conn = get_conn()
        rows = conn.execute(
            """SELECT b.id, b.name, b.created_at, b.user_id, b.is_public, count(w.id) AS total,
                      CASE WHEN b.id = ? THEN 1 ELSE 0 END AS active
               FROM books b LEFT JOIN words w ON w.book_id = b.id
               WHERE b.user_id = ? OR b.is_public = 1
               GROUP BY b.id ORDER BY active DESC, b.user_id = ? DESC, b.id DESC""",
            (aid or -1, uid, uid),
        ).fetchall()
        books = []
        for row in rows:
            book = dict(row)
            book_id = book["id"]
            book["is_owner"] = book.pop("user_id") == uid
            progress = conn.execute(
                """SELECT
                     sum(CASE WHEN p.status = 'new' THEN 1 ELSE 0 END) AS new_count,
                     sum(CASE WHEN p.status = 'learning' THEN 1 ELSE 0 END) AS learning_count,
                     sum(CASE WHEN p.status = 'mastered' THEN 1 ELSE 0 END) AS mastered_count
                   FROM words w JOIN progress p ON p.word_id = w.id AND p.user_id = ?
                   WHERE w.book_id = ?""",
                (uid, book_id),
            ).fetchone()
            book["new_count"] = progress["new_count"] or 0
            book["learning_count"] = progress["learning_count"] or 0
            book["mastered_count"] = progress["mastered_count"] or 0
            books.append(book)
        _json_response(self, {"books": books})

    def _get_settings(self, uid: int) -> None:
        _json_response(self, {
            "daily_new_limit": int(get_setting("daily_new_limit", "15", user_id=uid)),
            "active_book_id": active_book_id(uid),
            "date_offset": int(get_setting("date_offset", "0", user_id=0)),
            "real_date": dt.date.today().isoformat(),
            "virtual_date": today(),
        })

    def _set_settings(self, uid: int) -> None:
        user = get_current_user(self)
        if not user or user["role"] != "admin":
            return _json_response(self, {"error": "仅管理员可修改设置"}, 403)
        payload = _read_json(self)
        need_clear = False
        if "daily_new_limit" in payload:
            limit = max(1, min(150, int(payload["daily_new_limit"])))
            set_setting("daily_new_limit", str(limit), user_id=uid)
            need_clear = True
        if "date_offset" in payload:
            set_setting("date_offset", str(int(payload["date_offset"])), user_id=0)
            # 改日期不删除任何 session，每个日期的 session 独立存在
        if need_clear:
            # 只在改每日词数时清除当前日期的 session
            get_conn().execute("DELETE FROM daily_session WHERE user_id = ? AND date = ?", (uid, today()))
            get_conn().commit()
        _json_response(self, {
            "daily_new_limit": int(get_setting("daily_new_limit", "15", user_id=uid)),
            "date_offset": int(get_setting("date_offset", "0", user_id=0)),
            "virtual_date": today(),
        })

    def _activate_book(self, uid: int) -> None:
        payload = _read_json(self)
        book_id = payload.get("book_id")
        daily_limit = payload.get("daily_new_limit")
        if book_id:
            set_setting("active_book_id", str(int(book_id)), user_id=uid)
        if daily_limit is not None:
            limit = max(1, min(150, int(daily_limit)))
            set_setting("daily_new_limit", str(limit), user_id=uid)
        # 切换词书时清除当前日期的 session（其他日期保留）
        get_conn().execute("DELETE FROM daily_session WHERE user_id = ? AND date = ?", (uid, today()))
        get_conn().commit()
        _json_response(self, {
            "ok": True,
            "active_book_id": int(book_id) if book_id else active_book_id(uid),
            "daily_new_limit": int(get_setting("daily_new_limit", "15", user_id=uid)),
        })

    def _today(self, uid: int) -> None:
        limit = int(get_setting("daily_new_limit", "15", user_id=uid))
        aid = active_book_id(uid)
        conn = get_conn()
        today_str = today()
        session_book = aid or 0

        session = conn.execute(
            "SELECT word_ids, studied_ids FROM daily_session WHERE user_id = ? AND date = ? AND book_id = ?",
            (uid, today_str, session_book),
        ).fetchone()

        if session:
            word_ids = json.loads(session["word_ids"])
            studied_ids = set(json.loads(session["studied_ids"]))
        else:
            book_filter = "AND w.book_id = ?" if aid else ""
            used_in_other = set()
            other_sessions = conn.execute(
                "SELECT studied_ids FROM daily_session WHERE user_id = ? AND date != ? AND book_id = ?",
                (uid, today_str, session_book),
            ).fetchall()
            for s in other_sessions:
                used_in_other.update(json.loads(s["studied_ids"]))

            all_params = [uid]
            if aid:
                all_params.append(aid)

            all_rows = conn.execute(
                f"""SELECT w.id, p.status, p.due_date, p.familiarity, p.memory_strength, p.last_seen
                    FROM words w JOIN progress p ON p.word_id = w.id AND p.user_id = ?
                    WHERE 1=1 {book_filter}
                    ORDER BY w.id ASC""",
                tuple(all_params),
            ).fetchall()

            today_date = dt.date.fromisoformat(today_str)
            reviews_with_priority = []
            new_words = []
            for r in all_rows:
                if r["id"] in used_in_other:
                    continue
                if r["status"] != "new":
                    # 用艾宾浩斯公式计算保持率，按保持率排序（低优先）
                    s = r["memory_strength"] or 1.0
                    last = r["last_seen"]
                    if last:
                        try:
                            days = (today_date - dt.date.fromisoformat(last[:10])).days
                        except (ValueError, IndexError):
                            days = 0
                    else:
                        days = 0
                    retention = calc_retention(s, days)
                    # 使用艾宾浩斯阈值：保持率 < 60% 时需要复习
                    if retention < RETENTION_THRESHOLD:
                        reviews_with_priority.append((r["id"], retention))
                elif r["status"] == "new":
                    new_words.append(r["id"])

            # 按保持率升序排列（最需要复习的排前面）
            reviews_with_priority.sort(key=lambda x: x[1])
            reviews = [r[0] for r in reviews_with_priority]

            word_ids = reviews[:50] + new_words[:limit]
            studied_ids = set()

            if word_ids:
                conn.execute(
                    "INSERT INTO daily_session(user_id, date, book_id, word_ids, studied_ids, created_at) VALUES(?, ?, ?, ?, ?, ?)",
                    (uid, today_str, session_book, json.dumps(word_ids), "[]", now_iso()),
                )
                conn.commit()

        if not word_ids:
            _json_response(self, {
                "daily_new_limit": limit, "active_book_id": aid,
                "reviews": [], "new_words": [],
            })
            return

        placeholders = ",".join("?" for _ in word_ids)
        rows = conn.execute(
            f"""SELECT w.*, p.status, p.familiarity, p.memory_strength, p.due_date,
                      p.is_favorite, p.is_wrong, p.last_seen
                FROM words w JOIN progress p ON p.word_id = w.id AND p.user_id = ?
                WHERE w.id IN ({placeholders})""",
            [uid] + word_ids,
        ).fetchall()
        row_map = {r["id"]: r for r in rows}

        today_date = dt.date.fromisoformat(today_str)
        reviews, new_words = [], []
        for wid in word_ids:
            if wid not in row_map:
                continue
            row = row_map[wid]
            item = _row_to_word(row)
            # 添加艾宾浩斯数据
            s = row["memory_strength"] or 1.0
            item["memory_strength"] = s
            last = row["last_seen"]
            if last:
                try:
                    days = (today_date - dt.date.fromisoformat(last[:10])).days
                except (ValueError, IndexError):
                    days = 0
            else:
                days = 0
            item["retention"] = round(calc_retention(s, days) * 100, 1)
            item["days_since_review"] = days
            if wid in studied_ids:
                item["studied_today"] = True
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

    def _stats(self, uid: int) -> None:
        aid = active_book_id(uid)
        conn = get_conn()
        book_filter = "WHERE w.book_id = ?" if aid else ""
        params = [uid]
        if aid:
            params.append(aid)

        counts = conn.execute(
            f"""SELECT
                    count(*) AS total,
                    sum(CASE WHEN p.status = 'new' THEN 1 ELSE 0 END) AS new_total,
                    sum(CASE WHEN p.status = 'learning' THEN 1 ELSE 0 END) AS learning,
                    sum(CASE WHEN p.status = 'mastered' THEN 1 ELSE 0 END) AS mastered,
                    sum(CASE WHEN p.is_wrong = 1 THEN 1 ELSE 0 END) AS wrong_total
                FROM words w JOIN progress p ON p.word_id = w.id AND p.user_id = ?
                {book_filter}""",
            tuple(params),
        ).fetchone()
        events = conn.execute(
            """SELECT substr(created_at, 1, 10) AS day, count(*) AS total
               FROM events WHERE user_id = ? AND action IN ('forgot', 'vague', 'known', 'easy')
               GROUP BY substr(created_at, 1, 10)
               ORDER BY day DESC LIMIT 365""",
            (uid,),
        ).fetchall()
        _json_response(self, {"counts": dict(counts), "events": [dict(r) for r in events]})

    def _heatmap(self, uid: int) -> None:
        """Return daily learning counts for the past year."""
        rows = get_conn().execute(
            """SELECT substr(created_at, 1, 10) AS day, count(*) AS count
               FROM events WHERE user_id = ?
               GROUP BY substr(created_at, 1, 10)
               ORDER BY day ASC""",
            (uid,),
        ).fetchall()
        data = {r["day"]: r["count"] for r in rows}
        _json_response(self, {"data": data})

    def _wrong_words(self, uid: int) -> None:
        rows = get_conn().execute(
            """SELECT w.id, w.word, w.translation, w.phonetic,
                      p.familiarity, p.attempts, p.correct, p.last_seen
               FROM progress p JOIN words w ON w.id = p.word_id
               WHERE p.user_id = ? AND p.is_wrong = 1
               ORDER BY p.last_seen DESC LIMIT 200""",
            (uid,),
        ).fetchall()
        _json_response(self, {"words": [dict(r) for r in rows]})

    def _favorites(self, uid: int) -> None:
        rows = get_conn().execute(
            """SELECT w.id, w.word, w.translation, w.phonetic, w.example
               FROM progress p JOIN words w ON w.id = p.word_id
               WHERE p.user_id = ? AND p.is_favorite = 1
               ORDER BY p.last_seen DESC LIMIT 200""",
            (uid,),
        ).fetchall()
        _json_response(self, {"words": [dict(r) for r in rows]})

    def _wrong_words_remove(self, uid: int) -> None:
        payload = _read_json(self)
        word_id = int(payload.get("word_id", 0))
        get_conn().execute(
            "UPDATE progress SET is_wrong = 0 WHERE user_id = ? AND word_id = ?",
            (uid, word_id),
        )
        get_conn().commit()
        _json_response(self, {"ok": True})

    def _test_words(self, uid: int, query: dict) -> None:
        """Get words for spelling test based on range."""
        range_type = (query.get("range") or ["all"])[0]
        limit = int((query.get("limit") or ["20"])[0])
        limit = max(5, min(100, limit))
        aid = active_book_id(uid)
        conn = get_conn()

        if range_type == "today":
            # Words from today's session
            today_str = today()
            session_book = aid or 0
            session = conn.execute(
                "SELECT word_ids, studied_ids FROM daily_session WHERE user_id = ? AND date = ? AND book_id = ?",
                (uid, today_str, session_book),
            ).fetchone()
            if session:
                word_ids = json.loads(session["word_ids"])
            else:
                word_ids = []
            if word_ids:
                placeholders = ",".join("?" for _ in word_ids)
                rows = conn.execute(
                    f"""SELECT w.id, w.word, w.translation FROM words w
                        JOIN progress p ON p.word_id = w.id AND p.user_id = ?
                        WHERE w.id IN ({placeholders})
                        ORDER BY RANDOM() LIMIT ?""",
                    [uid] + word_ids + [limit],
                ).fetchall()
            else:
                rows = []
        elif range_type == "wrong":
            rows = conn.execute(
                """SELECT w.id, w.word, w.translation FROM words w
                   JOIN progress p ON p.word_id = w.id AND p.user_id = ?
                   WHERE p.is_wrong = 1
                   ORDER BY RANDOM() LIMIT ?""",
                (uid, limit),
            ).fetchall()
        else:  # "all"
            book_filter = "AND w.book_id = ?" if aid else ""
            params = [uid]
            if aid:
                params.append(aid)
            params.append(limit)
            rows = conn.execute(
                f"""SELECT w.id, w.word, w.translation FROM words w
                    JOIN progress p ON p.word_id = w.id AND p.user_id = ?
                    WHERE 1=1 {book_filter}
                    ORDER BY RANDOM() LIMIT ?""",
                tuple(params),
            ).fetchall()

        words = [{"id": r["id"], "word": r["word"], "translation": r["translation"] or ""} for r in rows]
        _json_response(self, {"words": words, "total": len(words)})

    def _test_check(self, uid: int) -> None:
        """Check a spelling test answer."""
        payload = _read_json(self)
        word_id = int(payload.get("word_id", 0))
        answer = (payload.get("answer") or "").strip().lower()

        row = get_conn().execute("SELECT word FROM words WHERE id = ?", (word_id,)).fetchone()
        if not row:
            return _json_response(self, {"error": "单词不存在"}, 404)

        correct_word = row["word"].strip().lower()
        is_correct = answer == correct_word

        if not is_correct:
            # Mark as wrong
            get_conn().execute(
                "UPDATE progress SET is_wrong = 1 WHERE user_id = ? AND word_id = ?",
                (uid, word_id),
            )
            get_conn().commit()

        _json_response(self, {
            "correct": is_correct,
            "correct_word": row["word"],
            "user_answer": answer,
        })

    def _pdf_words(self, uid: int) -> None:
        rows = get_conn().execute(
            """SELECT pw.id, pw.day, pw.position, pw.word, pw.translation,
                      coalesce(pwm.crossed, 0) AS crossed, pwm.updated_at
               FROM pdf_words pw
               LEFT JOIN pdf_word_marks pwm ON pwm.word_id = pw.id AND pwm.user_id = ?
               WHERE pw.source = 'cet4_pdf'
               ORDER BY pw.day ASC, pw.position ASC, pw.id ASC""",
            (uid,),
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

    def _pdf_word_mark(self, uid: int) -> None:
        payload = _read_json(self)
        word_id = int(payload.get("word_id", 0))
        crossed = 1 if payload.get("crossed") else 0
        conn = get_conn()
        exists = conn.execute("SELECT id FROM pdf_words WHERE id = ? AND source = 'cet4_pdf'", (word_id,)).fetchone()
        if not exists:
            return _json_response(self, {"error": "word not found"}, 404)
        conn.execute(
            """INSERT INTO pdf_word_marks(user_id, word_id, crossed, updated_at) VALUES(?, ?, ?, ?)
               ON CONFLICT(user_id, word_id) DO UPDATE SET crossed = excluded.crossed, updated_at = excluded.updated_at""",
            (uid, word_id, crossed, now_iso()),
        )
        conn.commit()
        _json_response(self, {"ok": True, "word_id": word_id, "crossed": bool(crossed)})

    def _import_preview(self) -> None:
        payload = _read_json(self)
        rows = parse_import_text(payload.get("text", ""))
        _json_response(self, {"words": rows[:500], "total": len(rows)})

    def _create_book(self, uid: int) -> None:
        payload = _read_json(self)
        name = (payload.get("name") or "我的词书").strip()
        words = payload.get("words") or []
        is_public = 1 if payload.get("is_public") else 0
        # 普通用户不能创建公开词书
        user = get_current_user(self)
        if is_public and (not user or user["role"] != "admin"):
            is_public = 0
        if not words:
            return _json_response(self, {"error": "没有可导入的单词"}, 400)
        conn = get_conn()
        book_id = conn.execute(
            "INSERT INTO books(user_id, name, is_public, created_at) VALUES(?, ?, ?, ?)",
            (uid, name, is_public, now_iso()),
        ).lastrowid
        inserted = 0
        for item in words:
            word = normalize_word(str(item.get("word", "")))
            if not word:
                continue
            try:
                word_id = conn.execute(
                    """INSERT INTO words(book_id, word, translation, definition, example, created_at)
                       VALUES(?, ?, ?, ?, ?, ?)""",
                    (book_id, word, item.get("translation", ""), item.get("definition", ""),
                     _clean_example(item.get("example", "")), now_iso()),
                ).lastrowid
            except sqlite3.IntegrityError:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO progress(user_id, word_id, due_date) VALUES(?, ?, ?)",
                (uid, word_id, today()),
            )
            inserted += 1
        conn.commit()
        _json_response(self, {"book_id": book_id, "inserted": inserted})

    def _progress(self, uid: int) -> None:
        payload = _read_json(self)
        word_id = int(payload.get("word_id", 0))
        action = str(payload.get("action", "vague"))
        if action not in REVIEW_INTERVALS:
            return _json_response(self, {"error": "未知学习反馈"}, 400)
        today_str = today()
        correct = 1 if action in {"known", "easy"} else 0
        wrong = 1 if action == "forgot" else 0
        status = "mastered" if action == "easy" else "learning"
        delta = FAMILIARITY_DELTA[action]
        # 用虚拟日期记录，确保日期隔离
        event_time = f"{today_str}T{dt.datetime.now().strftime('%H:%M:%S')}"
        conn = get_conn()

        # 读取当前记忆强度，计算新的强度和复习日期
        row = conn.execute(
            "SELECT memory_strength FROM progress WHERE user_id = ? AND word_id = ?",
            (uid, word_id),
        ).fetchone()
        old_strength = (row["memory_strength"] if row else 1.0) or 1.0
        new_strength = update_memory_strength(old_strength, action)
        due = calc_next_review(new_strength, event_time)

        conn.execute(
            """UPDATE progress SET
                status = ?, familiarity = max(0, min(10, familiarity + ?)),
                memory_strength = ?,
                attempts = attempts + 1, correct = correct + ?,
                last_seen = ?, due_date = ?,
                is_wrong = CASE WHEN ? = 1 THEN 1 ELSE is_wrong END
               WHERE user_id = ? AND word_id = ?""",
            (status, delta, new_strength, correct, event_time, due, wrong, uid, word_id),
        )
        conn.execute(
            "INSERT INTO events(user_id, word_id, action, created_at) VALUES(?, ?, ?, ?)",
            (uid, word_id, action, event_time),
        )
        # Mark studied in session
        aid = active_book_id(uid)
        session_book = aid or 0
        session = conn.execute(
            "SELECT studied_ids FROM daily_session WHERE user_id = ? AND date = ? AND book_id = ?",
            (uid, today_str, session_book),
        ).fetchone()
        if session:
            studied = json.loads(session["studied_ids"])
            if word_id not in studied:
                studied.append(word_id)
            conn.execute(
                "UPDATE daily_session SET studied_ids = ? WHERE user_id = ? AND date = ? AND book_id = ?",
                (json.dumps(studied), uid, today_str, session_book),
            )
        conn.commit()
        _json_response(self, {"ok": True, "due_date": due, "status": status})

    def _favorite(self, uid: int) -> None:
        payload = _read_json(self)
        word_id = int(payload.get("word_id", 0))
        favorite = 1 if payload.get("favorite") else 0
        get_conn().execute(
            "UPDATE progress SET is_favorite = ? WHERE user_id = ? AND word_id = ?",
            (favorite, uid, word_id),
        )
        get_conn().commit()
        _json_response(self, {"ok": True, "favorite": favorite})

    def _reset_today(self, uid: int) -> None:
        today_str = today()
        conn = get_conn()
        conn.execute("DELETE FROM daily_session WHERE user_id = ? AND date = ?", (uid, today_str))
        conn.execute(
            """UPDATE progress SET status = 'new', familiarity = 0, attempts = 0,
               correct = 0, last_seen = NULL, due_date = ?
               WHERE user_id = ? AND (last_seen LIKE ? OR due_date = ?)""",
            (today_str, uid, f"{today_str}%", today_str),
        )
        conn.execute(
            "DELETE FROM events WHERE user_id = ? AND created_at LIKE ?",
            (uid, f"{today_str}%"),
        )
        conn.commit()
        _json_response(self, {"ok": True, "message": "今日学习已重置"})

    def _save_pexels_key(self, user: dict) -> None:
        if user["role"] != "admin":
            return _json_response(self, {"error": "仅管理员可修改"}, 403)
        payload = _read_json(self)
        key = (payload.get("api_key") or "").strip()
        config_file = ROOT / "config.json"
        config = {}
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        config["pexels_api_key"] = key
        config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        import server.pexels as pexels_mod
        pexels_mod._pexels_status_cache = None
        pexels_mod._pexels_status_time = 0
        _json_response(self, {"ok": True, "message": "Pexels API Key 已保存"})

    def _reset_book_progress(self, uid: int) -> None:
        payload = _read_json(self)
        book_id = int(payload.get("book_id", 0))
        if not book_id:
            return _json_response(self, {"error": "缺少 book_id"}, 400)
        conn = get_conn()
        conn.execute(
            """UPDATE progress SET status = 'new', familiarity = 0, attempts = 0,
               correct = 0, last_seen = NULL, due_date = ?
               WHERE user_id = ? AND word_id IN (SELECT id FROM words WHERE book_id = ?)""",
            (today(), uid, book_id),
        )
        conn.execute(
            "DELETE FROM events WHERE user_id = ? AND word_id IN (SELECT id FROM words WHERE book_id = ?)",
            (uid, book_id),
        )
        conn.execute("DELETE FROM daily_session WHERE user_id = ?", (uid,))
        conn.commit()
        _json_response(self, {"ok": True, "message": "词书学习进度已重置"})


# ── Background enrichment ──

def _batch_enrich_all() -> None:
    import time as _time
    try:
        conn = get_conn()
        rows = conn.execute(
            """SELECT id FROM words
               WHERE example = '' OR example IS NULL
                  OR audio_url = '' OR audio_url IS NULL
                  OR image_url = '' OR image_url IS NULL"""
        ).fetchall()
        total = len(rows)
        if total == 0:
            return
        print(f"[enrich] 后台补全 {total} 个词...")
        done = 0
        for row in rows:
            try:
                _enrich_single_word(row["id"])
            except Exception:
                pass
            done += 1
            if done % 50 == 0:
                print(f"[enrich] {done}/{total}")
            _time.sleep(0.5)
        print(f"[enrich] 完成: {done}")
    except Exception as e:
        print(f"[enrich] 异常: {e}")


def main() -> None:
    init_db()
    # 批量补全已禁用，改为查词时按需补全（避免多线程竞争）
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
