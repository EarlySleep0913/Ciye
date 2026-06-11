"""艾宾浩斯遗忘曲线模块

核心公式：R = e^(-t/S)
- R: 记忆保持率 (0~1)
- t: 距上次学习的天数
- S: 记忆强度 (越大遗忘越慢)

记忆强度变化：
- 答对：S = S + 1.0 (成功强化记忆)
- 答错：S = max(0.5, S - 0.5) (记忆减弱)

复习时机：当 R < 0.6 时触发复习
- 复习间隔 = S * ln(1/0.6) ≈ S * 0.51 天
"""

from __future__ import annotations

import math
import datetime as dt
from http.server import BaseHTTPRequestHandler

from .db import get_conn, active_book_id, today

# 保持率阈值：低于此值应该复习
RETENTION_THRESHOLD = 0.6

def calc_retention(strength: float, days_elapsed: float) -> float:
    """计算记忆保持率 R = e^(-t/S)"""
    if strength <= 0:
        strength = 0.5
    if days_elapsed <= 0:
        return 1.0
    return math.exp(-days_elapsed / strength)


def calc_review_interval(strength: float) -> float:
    """计算复习间隔（天）：当 R 降到阈值以下的时间"""
    if strength <= 0:
        strength = 0.5
    # R = e^(-t/S) < threshold => t > S * ln(1/threshold)
    return strength * math.log(1.0 / RETENTION_THRESHOLD)


def update_memory_strength(old_strength: float, action: str) -> float:
    """根据学习反馈更新记忆强度"""
    if action == "easy":
        new_strength = old_strength + 1.8
    elif action == "known":
        new_strength = old_strength + 1.1
    elif action == "vague":
        new_strength = old_strength + 0.3
    else:  # forgot
        new_strength = max(0.5, old_strength - max(0.5, old_strength * 0.25))
    return round(min(max(new_strength, 0.5), 30.0), 2)


def calc_next_review(strength: float, last_seen: str | None) -> str:
    """计算下次复习日期"""
    interval = calc_review_interval(strength)
    if last_seen:
        try:
            base = dt.date.fromisoformat(last_seen[:10])
        except (ValueError, IndexError):
            base = dt.date.fromisoformat(today())
    else:
        base = dt.date.fromisoformat(today())
    next_date = base + dt.timedelta(days=max(1, round(interval)))
    return next_date.isoformat()


def get_retention_data(uid: int) -> dict:
    """获取用户的遗忘曲线统计数据"""
    conn = get_conn()
    aid = active_book_id(uid)
    book_filter = "AND w.book_id = ?" if aid else ""
    params = [uid]
    if aid:
        params.append(aid)

    rows = conn.execute(
        f"""SELECT p.status, p.memory_strength, p.last_seen, p.familiarity,
                   p.attempts, p.correct, p.is_wrong, p.due_date
            FROM progress p
            JOIN words w ON w.id = p.word_id
            WHERE p.user_id = ? AND p.status != 'new' {book_filter}""",
        tuple(params),
    ).fetchall()

    today_date = dt.date.fromisoformat(today())
    total = len(rows)

    # 分类统计
    strong = 0      # 记忆牢固 (S >= 4)
    moderate = 0    # 记忆中等 (2 <= S < 4)
    weak = 0        # 记忆薄弱 (S < 2)
    at_risk = 0     # 即将遗忘 (R < 0.6)
    total_retention = 0.0

    curve_points = []  # 用于绘制平均遗忘曲线

    for row in rows:
        s = row["memory_strength"] or 1.0
        last = row["last_seen"]
        if last:
            try:
                days = (today_date - dt.date.fromisoformat(last[:10])).days
            except (ValueError, IndexError):
                days = 0
        else:
            days = 0

        r = calc_retention(s, days)
        total_retention += r

        if s >= 4:
            strong += 1
        elif s >= 2:
            moderate += 1
        else:
            weak += 1

        if r < RETENTION_THRESHOLD or (row["due_date"] and row["due_date"] <= today()):
            at_risk += 1

    avg_retention = (total_retention / total * 100) if total > 0 else 0

    # 生成标准遗忘曲线数据（用于可视化）
    # 展示不同记忆强度下的遗忘曲线
    curve_data = {}
    for s_val in [1.0, 2.0, 4.0, 7.0, 10.0]:
        points = []
        for d in range(0, 31):
            r = calc_retention(s_val, d)
            points.append({"day": d, "retention": round(r * 100, 1)})
        curve_data[str(s_val)] = points

    return {
        "total": total,
        "strong": strong,
        "moderate": moderate,
        "weak": weak,
        "at_risk": at_risk,
        "avg_retention": round(avg_retention, 1),
        "threshold": RETENTION_THRESHOLD * 100,
        "curve_data": curve_data,
    }


def get_word_retention(uid: int, word_id: int) -> dict:
    """获取单个词的遗忘曲线详情"""
    conn = get_conn()
    row = conn.execute(
        """SELECT p.memory_strength, p.last_seen, p.familiarity,
                  p.attempts, p.correct, p.status, p.due_date,
                  p.difficulty, p.review_count, p.lapse_count, p.last_grade
           FROM progress p WHERE p.user_id = ? AND p.word_id = ?""",
        (uid, word_id),
    ).fetchone()
    if not row:
        return {}

    s = row["memory_strength"] or 1.0
    last = row["last_seen"]
    today_date = dt.date.fromisoformat(today())

    if last:
        try:
            days_elapsed = (today_date - dt.date.fromisoformat(last[:10])).days
        except (ValueError, IndexError):
            days_elapsed = 0
    else:
        days_elapsed = 0

    current_r = calc_retention(s, days_elapsed)
    interval = calc_review_interval(s)

    # 生成这个词的遗忘曲线（30天）
    curve = []
    for d in range(0, 31):
        r = calc_retention(s, d)
        curve.append({"day": d, "retention": round(r * 100, 1)})

    # 获取学习历史
    events = conn.execute(
        """SELECT action, created_at FROM events
           WHERE user_id = ? AND word_id = ?
           ORDER BY created_at DESC LIMIT 20""",
        (uid, word_id),
    ).fetchall()

    return {
        "word_id": word_id,
        "memory_strength": s,
        "current_retention": round(current_r * 100, 1),
        "days_elapsed": days_elapsed,
        "review_interval": round(interval, 1),
        "next_review": row["due_date"] or calc_next_review(s, last),
        "at_risk": current_r < RETENTION_THRESHOLD or bool(row["due_date"] and row["due_date"] <= today()),
        "familiarity": row["familiarity"],
        "attempts": row["attempts"],
        "correct": row["correct"],
        "difficulty": row["difficulty"],
        "review_count": row["review_count"],
        "lapse_count": row["lapse_count"],
        "last_grade": row["last_grade"],
        "curve": curve,
        "history": [{"action": e["action"], "date": e["created_at"][:10]} for e in events],
    }


def get_review_queue_ebbinghaus(uid: int) -> list[dict]:
    """基于艾宾浩斯曲线获取需要复习的词"""
    conn = get_conn()
    aid = active_book_id(uid)
    book_filter = "AND w.book_id = ?" if aid else ""
    params = [uid]
    if aid:
        params.append(aid)

    rows = conn.execute(
        f"""SELECT w.id, w.word, w.translation, p.memory_strength, p.last_seen, p.due_date
            FROM progress p JOIN words w ON w.id = p.word_id
            WHERE p.user_id = ? AND p.status != 'new' {book_filter}""",
        tuple(params),
    ).fetchall()

    today_date = dt.date.fromisoformat(today())
    due_words = []

    for row in rows:
        s = row["memory_strength"] or 1.0
        last = row["last_seen"]
        if last:
            try:
                days = (today_date - dt.date.fromisoformat(last[:10])).days
            except (ValueError, IndexError):
                days = 0
        else:
            days = 0

        r = calc_retention(s, days)
        due_by_date = bool(row["due_date"] and row["due_date"] <= today())
        if r < RETENTION_THRESHOLD or due_by_date:
            due_words.append({
                "id": row["id"],
                "word": row["word"],
                "translation": row["translation"],
                "retention": round(r * 100, 1),
                "strength": s,
                "days_since": days,
                "due_date": row["due_date"],
            })

    # 按保持率排序（最低的优先复习）
    due_words.sort(key=lambda x: (x["retention"], x.get("due_date") or "", x["id"]))
    return due_words


def _json(h: BaseHTTPRequestHandler, data: dict, status: int = 200) -> None:
    import json
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


def handle_ebbinghaus_overview(h: BaseHTTPRequestHandler, uid: int) -> None:
    """GET /api/ebbinghaus — 遗忘曲线总览"""
    data = get_retention_data(uid)
    _json(h, data)


def handle_ebbinghaus_word(h: BaseHTTPRequestHandler, uid: int, word_id: int) -> None:
    """GET /api/ebbinghaus/word/{id} — 单词遗忘曲线详情"""
    data = get_word_retention(uid, word_id)
    if not data:
        return _json(h, {"error": "单词不存在"}, 404)
    _json(h, data)


def handle_ebbinghaus_review_queue(h: BaseHTTPRequestHandler, uid: int) -> None:
    """GET /api/ebbinghaus/review — 基于遗忘曲线的复习队列"""
    words = get_review_queue_ebbinghaus(uid)
    _json(h, {"words": words, "total": len(words)})
