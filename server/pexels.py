"""Pexels image search with status caching."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

_pexels_status_cache: dict | None = None
_pexels_status_time: float = 0
PEXELS_STATUS_TTL = 300  # 5 minutes


def _load_api_key() -> str:
    from .db import ROOT
    import os
    config_file = ROOT / "config.json"
    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return os.environ.get("PEXELS_API_KEY") or config.get("pexels_api_key") or ""


def check_pexels_status() -> dict:
    """Check Pexels API status, cached for 5 minutes."""
    global _pexels_status_cache, _pexels_status_time
    if _pexels_status_cache and (time.time() - _pexels_status_time) < PEXELS_STATUS_TTL:
        return _pexels_status_cache

    api_key = _load_api_key()
    if not api_key:
        _pexels_status_cache = {"ok": False, "message": "未配置 Pexels API Key"}
        _pexels_status_time = time.time()
        return _pexels_status_cache

    url = "https://api.pexels.com/v1/search?query=apple&per_page=1"
    req = urllib.request.Request(url, headers={"Authorization": api_key, "User-Agent": "ciye/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = {"ok": resp.status < 400, "message": "Pexels 可用"}
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            result = {"ok": False, "message": "Pexels API Key 无效或已失效"}
        else:
            result = {"ok": False, "message": f"Pexels 请求失败：HTTP {exc.code}"}
    except (urllib.error.URLError, TimeoutError):
        result = {"ok": False, "message": "Pexels 网络请求失败"}

    _pexels_status_cache = result
    _pexels_status_time = time.time()
    return result


IMAGE_QUERY_FALLBACKS = {
    "abandon": ["departure", "empty road"],
    "curious": ["child learning", "question"],
    "efficient": ["workspace", "clock"],
    "serendipity": ["discovery", "sunlight street"],
}


def search_pexels(word: str) -> str:
    """Search Pexels for a word image, with fallback queries."""
    api_key = _load_api_key()
    if not api_key:
        return ""

    candidates = [word] + IMAGE_QUERY_FALLBACKS.get(word.lower(), [])
    for query_text in candidates:
        url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query_text)}&per_page=1&orientation=landscape"
        req = urllib.request.Request(url, headers={"Authorization": api_key, "User-Agent": "ciye/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, dict) and data.get("photos"):
                src = data["photos"][0].get("src", {})
                return src.get("medium") or src.get("large") or src.get("original") or ""
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            continue
    return ""
