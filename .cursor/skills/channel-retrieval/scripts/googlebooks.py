#!/usr/bin/env python3
"""Google Books client -> normalized records (JSONL).

Class = evidence: court-blessed snippet search across a huge corpus (metadata +
in-copyright snippets). Works keyless at low rate; set GOOGLE_BOOKS_API_KEY for
higher quota. Metadata is famously noisy -> verify dates/authors.
Usage: googlebooks.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    params = "maxResults=%d&q=%s" % (min(limit, 40), _http.quote(query))
    key = os.environ.get("GOOGLE_BOOKS_API_KEY")
    if key:
        params += "&key=" + _http.quote(key)
    data = _http.get_json("https://www.googleapis.com/books/v1/volumes?" + params, timeout)
    out: List[Dict[str, Any]] = []
    for it in (data.get("items") or []):
        vi = it.get("volumeInfo") or {}
        si = it.get("searchInfo") or {}
        authors = [{"name": n} for n in (vi.get("authors") or [])]
        out.append(_http.rec(
            "google_books", url=vi.get("infoLink", "") or vi.get("canonicalVolumeLink", ""),
            title=vi.get("title", ""),
            authors=authors,
            published=str(vi.get("publishedDate", "")),
            primary=True,
            snippet=(si.get("textSnippet", "") or vi.get("description", ""))[:300],
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Google Books -> normalized records"))
