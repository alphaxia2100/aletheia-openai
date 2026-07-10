#!/usr/bin/env python3
"""OpenAlex client -> normalized source records (JSONL).

The academic independence backbone: exposes authors + institutions + country +
citation edges (referenced_works, cited_by_count) needed to detect echo vs.
independent support. Since Feb 2026 a free OPENALEX_API_KEY is recommended
(low free quota without one). Usage: openalex.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402

_SEARCH_LIMIT = 100  # OpenAlex returns HTTP 400 when `search` exceeds its accepted query length.


def _search_query(query: str) -> str:
    """Preserve natural-language search when accepted; compact only over-limit queries.

    The leaf engine's zero-result relaxation cannot help an HTTP 400 because the request never
    returns a result set. Salience-aware keywordization retains acronyms/entities such as LLM while
    staying under OpenAlex's search limit.
    """
    query = (query or "").strip()
    if len(query) <= _SEARCH_LIMIT:
        return query
    candidate = query
    for n in (6, 5, 4, 3, 2):
        candidate = _http.keywordize(query, n)
        if len(candidate) <= _SEARCH_LIMIT:
            return candidate
    return candidate[:_SEARCH_LIMIT].rsplit(" ", 1)[0] or candidate[:_SEARCH_LIMIT]


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    params = "per_page=%d&search=%s" % (min(limit, 25), _http.quote(_search_query(query)))
    key = os.environ.get("OPENALEX_API_KEY")
    mailto = os.environ.get("OPENALEX_MAILTO")
    if key:
        params += "&api_key=" + _http.quote(key)
    if mailto:
        params += "&mailto=" + _http.quote(mailto)
    data = _http.get_json("https://api.openalex.org/works?" + params, timeout)

    out: List[Dict[str, Any]] = []
    for w in data.get("results", []):
        authors = []
        for a in (w.get("authorships") or []):
            author = a.get("author") or {}
            insts = a.get("institutions") or []
            inst0 = insts[0] if insts else {}
            authors.append({
                "name": author.get("display_name", ""),
                "id": author.get("id", ""),
                "affiliation": inst0.get("display_name", ""),
                "country": inst0.get("country_code", ""),
            })
        out.append(_http.rec(
            "openalex",
            # id = the OpenAlex work id so that other works' `referenced_works`
            # (which are OpenAlex ids) actually match this node in the citation graph.
            id=w.get("id"),
            url=w.get("doi") or w.get("id") or "",
            title=w.get("display_name") or "",
            authors=authors,
            published=str(w.get("publication_year") or ""),
            doi=(w.get("doi") or ""),
            refs=w.get("referenced_works") or [],
            cited_by_count=w.get("cited_by_count") or 0,
            primary=True,
            snippet=("cited_by=%s" % w.get("cited_by_count", 0)),
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "OpenAlex -> normalized records"))
