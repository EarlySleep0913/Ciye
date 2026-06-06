"""Dictionary lookup: ECDICT (local) + Free Dictionary API (online)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .db import query_ecdict


def _request_json(url: str, headers: dict | None = None, timeout: int = 8) -> dict | list | None:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "ciye/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status >= 400:
                return None
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def query_free_dictionary(word: str) -> dict:
    """Query Free Dictionary API for phonetic, definition, audio, example."""
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
    data = _request_json(url)
    if not isinstance(data, list) or not data:
        return {}
    entry = data[0]
    phonetic = entry.get("phonetic") or ""
    audio_url = ""
    for item in entry.get("phonetics", []):
        phonetic = phonetic or item.get("text") or ""
        if not audio_url and item.get("audio"):
            audio_url = item["audio"]
    definitions = []
    example = ""
    for meaning in entry.get("meanings", []):
        part = meaning.get("partOfSpeech", "")
        for defn in meaning.get("definitions", [])[:2]:
            text = defn.get("definition")
            if text:
                definitions.append(f"{part}. {text}" if part else text)
            example = example or defn.get("example") or ""
    return {
        "phonetic": phonetic,
        "definition": "\n".join(definitions[:3]),
        "example": example,
        "audio_url": audio_url,
    }


def lookup_word(word: str) -> dict:
    """Combined lookup: ECDICT first, then Free Dictionary API for missing fields."""
    ecdict = query_ecdict(word)
    result = {
        "word": word,
        "translation": ecdict.get("translation", ""),
        "definition": ecdict.get("definition", ""),
        "phonetic": ecdict.get("phonetic", ""),
        "example": "",
        "audio_url": "",
    }
    if not result["definition"] or not result["phonetic"] or not result["audio_url"]:
        online = query_free_dictionary(word)
        for key in ("definition", "phonetic", "audio_url", "example"):
            if not result[key] and online.get(key):
                result[key] = online[key]
    if not result["example"]:
        result["example"] = f"I want to remember the word {word}."
    return result
