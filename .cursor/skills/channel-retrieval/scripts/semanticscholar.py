#!/usr/bin/env python3
"""Semantic Scholar (S2AG) client -> normalized records (JSONL).

Class = evidence: adds citation CONTEXT + influential-citation flag on top of
OpenAlex. Works keyless (shared anon pool, 429-prone -> one retry); set
SEMANTIC_SCHOLAR_API_KEY for a dedicated rate. Usage: semanticscholar.py "q" [--limit N].
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402

_FIELDS = "title,year,authors,externalIds,citationCount,influentialCitationCount"


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    url = ("https://api.semanticscholar.org/graph/v1/paper/search?query=%s&limit=%d&fields=%s"
           % (_http.quote(query), min(limit, 100), _FIELDS))
    headers = {}
    if os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        headers["x-api-key"] = os.environ["SEMANTIC_SCHOLAR_API_KEY"]
    for attempt in range(2):
        try:
            data = _http.get_json(url, timeout, headers)
            break
        except Exception:  # noqa: BLE001 - retry once on throttle
            if attempt == 0:
                time.sleep(2.5)
                continue
            raise
    out: List[Dict[str, Any]] = []
    for p in data.get("data", []):
        ext = p.get("externalIds") or {}
        doi = ext.get("DOI", "")
        authors = [{"name": a.get("name", ""), "id": a.get("authorId", "")}
                   for a in (p.get("authors") or [])]
        pid = p.get("paperId", "")
        out.append(_http.rec(
            "semantic_scholar",
            url=("https://doi.org/" + doi) if doi else ("https://www.semanticscholar.org/paper/" + pid),
            title=p.get("title", ""), authors=authors,
            published=str(p.get("year") or ""), doi=doi,
            cited_by_count=p.get("citationCount") or 0, primary=True,
            snippet="citations=%s influential=%s" % (
                p.get("citationCount"), p.get("influentialCitationCount")),
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Semantic Scholar -> normalized records"))
