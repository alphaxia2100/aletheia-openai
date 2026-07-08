#!/usr/bin/env python3
"""Project Gutenberg (via Gutendex) client -> normalized records (JSONL). No key.
Class = evidence: public-domain FULL TEXT, cleanest legal posture. Each record's
url points at a readable text/html format. Usage: gutendex.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def _best_format(formats: Dict[str, str]) -> str:
    for mime in ("text/html", "text/plain; charset=utf-8", "text/plain", "application/epub+zip"):
        if mime in formats:
            return formats[mime]
    return next(iter(formats.values()), "")


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    url = "https://gutendex.com/books?search=" + _http.quote(query)
    data = _http.get_json(url, timeout)
    out: List[Dict[str, Any]] = []
    for b in (data.get("results") or [])[:limit]:
        authors = [{"name": a.get("name", "")} for a in (b.get("authors") or [])]
        page = "https://www.gutenberg.org/ebooks/%s" % b.get("id")
        text_url = _best_format(b.get("formats") or {}) or page
        out.append(_http.rec(
            "gutenberg", url=text_url, title=b.get("title", ""),
            authors=authors, primary=True,
            snippet="gutenberg_id=%s downloads=%s page=%s" % (
                b.get("id"), b.get("download_count"), page),
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Gutendex/Project Gutenberg -> normalized records"))
