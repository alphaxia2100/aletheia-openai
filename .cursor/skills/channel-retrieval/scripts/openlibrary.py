#!/usr/bin/env python3
"""Open Library catalog search -> normalized records (JSONL).

No key. Records are bibliographic leads to books/editions, not proof of a claim; follow them to a
lawfully readable primary text before citing. Usage: openlibrary.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    url = ("https://openlibrary.org/search.json?q=%s&limit=%d&fields="
           "key,title,author_name,first_publish_year,edition_count,subject"
           % (_http.quote(query), min(limit, 100)))
    data = _http.get_json(url, timeout)
    out: List[Dict[str, Any]] = []
    for doc in (data.get("docs") or [])[:limit]:
        key = str(doc.get("key") or "")
        page = "https://openlibrary.org" + key if key.startswith("/") else "https://openlibrary.org/search?q=" + _http.quote(query)
        subjects = [str(s) for s in (doc.get("subject") or [])[:5]]
        out.append(_http.rec(
            "openlibrary", url=page, title=str(doc.get("title") or ""),
            authors=[{"name": str(name)} for name in (doc.get("author_name") or [])],
            published=str(doc.get("first_publish_year") or ""), primary=False,
            snippet="editions=%s subjects=%s" % (doc.get("edition_count", 0), ", ".join(subjects)),
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Open Library catalog -> normalized records"))
