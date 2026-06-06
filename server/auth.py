"""Authentication module — login, register, user management."""

from __future__ import annotations

import uuid
from http.server import BaseHTTPRequestHandler

from .db import (
    get_conn, get_user_by_token, get_user_by_username,
    hash_password, now_iso,
)


def _json(h: BaseHTTPRequestHandler, data: dict, status: int = 200) -> None:
    import json
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


def _read(h: BaseHTTPRequestHandler) -> dict:
    import json
    length = int(h.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = h.rfile.read(length)
    return json.loads(raw.decode("utf-8")) if raw else {}


def _get_token(h: BaseHTTPRequestHandler) -> str | None:
    auth = h.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def get_current_user(h: BaseHTTPRequestHandler) -> dict | None:
    token = _get_token(h)
    if not token:
        return None
    return get_user_by_token(token)


# ── API Handlers ──

def handle_login(h: BaseHTTPRequestHandler) -> None:
    payload = _read(h)
    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    if not username or not password:
        return _json(h, {"error": "请输入用户名和密码"}, 400)

    user = get_user_by_username(username)
    if not user or user["password_hash"] != hash_password(password):
        return _json(h, {"error": "用户名或密码错误"}, 401)

    token = str(uuid.uuid4())
    conn = get_conn()
    conn.execute(
        "INSERT INTO sessions(token, user_id, created_at) VALUES(?, ?, ?)",
        (token, user["id"], now_iso()),
    )
    conn.commit()

    _json(h, {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        },
    })


def handle_register(h: BaseHTTPRequestHandler) -> None:
    payload = _read(h)
    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    if not username or not password:
        return _json(h, {"error": "请输入用户名和密码"}, 400)
    if len(username) < 2 or len(password) < 4:
        return _json(h, {"error": "用户名至少2位，密码至少4位"}, 400)
    if get_user_by_username(username):
        return _json(h, {"error": "用户名已存在"}, 409)

    conn = get_conn()
    conn.execute(
        "INSERT INTO users(username, password_hash, role, created_at) VALUES(?, ?, 'user', ?)",
        (username, hash_password(password), now_iso()),
    )
    conn.commit()

    user = get_user_by_username(username)
    token = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO sessions(token, user_id, created_at) VALUES(?, ?, ?)",
        (token, user["id"], now_iso()),
    )

    # Create default book for new user
    book_id = conn.execute(
        "INSERT INTO books(user_id, name, created_at) VALUES(?, ?, ?)",
        (user["id"], "我的词书", now_iso()),
    ).lastrowid
    conn.execute(
        "INSERT OR IGNORE INTO settings(user_id, key, value) VALUES(?, 'active_book_id', ?)",
        (user["id"], str(book_id)),
    )
    conn.execute(
        "INSERT OR IGNORE INTO settings(user_id, key, value) VALUES(?, 'daily_new_limit', '15')",
        (user["id"],),
    )
    conn.commit()

    _json(h, {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        },
    })


def handle_me(h: BaseHTTPRequestHandler) -> None:
    user = get_current_user(h)
    if not user:
        return _json(h, {"error": "未登录"}, 401)
    _json(h, {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
    })


def handle_list_users(h: BaseHTTPRequestHandler) -> None:
    user = get_current_user(h)
    if not user or user["role"] != "admin":
        return _json(h, {"error": "无权限"}, 403)

    rows = get_conn().execute(
        "SELECT id, username, role, created_at FROM users ORDER BY id"
    ).fetchall()
    _json(h, {"users": [dict(r) for r in rows]})


def handle_update_role(h: BaseHTTPRequestHandler) -> None:
    user = get_current_user(h)
    if not user or user["role"] != "admin":
        return _json(h, {"error": "无权限"}, 403)

    payload = _read(h)
    target_id = int(payload.get("user_id", 0))
    new_role = payload.get("role", "")
    if new_role not in ("admin", "user"):
        return _json(h, {"error": "角色无效"}, 400)
    if target_id == user["id"]:
        return _json(h, {"error": "不能修改自己的角色"}, 400)

    conn = get_conn()
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, target_id))
    conn.commit()
    _json(h, {"ok": True})


def handle_delete_user(h: BaseHTTPRequestHandler, user_id: int) -> None:
    user = get_current_user(h)
    if not user or user["role"] != "admin":
        return _json(h, {"error": "无权限"}, 403)
    if user_id == user["id"]:
        return _json(h, {"error": "不能删除自己"}, 400)

    conn = get_conn()
    # Delete user's sessions, progress, events, daily_session, pdf_word_marks
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM events WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM daily_session WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM pdf_word_marks WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
    # Delete user's words (via books)
    book_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM books WHERE user_id = ?", (user_id,)
    ).fetchall()]
    for bid in book_ids:
        conn.execute("DELETE FROM words WHERE book_id = ?", (bid,))
    conn.execute("DELETE FROM books WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    _json(h, {"ok": True})
