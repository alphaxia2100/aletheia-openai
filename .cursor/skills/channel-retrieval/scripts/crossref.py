#!/usr/bin/env python3
"""Crossref client -> normalized records (JSONL). No key.

Class = evidence (identity layer): DOI/metadata + funder + sometimes a deposited
reference list (refs) usable for the citation graph. Set OPENALEX_MAILTO for the
polite pool. Usage: crossref.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    mailto = os.environ.get("OPENALEX_MAILTO", "")
    url = "https://api.crossref.org/works?query=%s&rows=%d" % (_http.quote(query), min(limit, 100))
    if mailto:
        url += "&mailto=" + _http.quote(mailto)
    data = _http.get_json(url, timeout)
    out: List[Dict[str, Any]] = []
    for it in ((data.get("message") or {}).get("items") or []):
        doi = it.get("DOI", "")
        title = (it.get("title") or [""])[0]
        authors = []
        for a in (it.get("author") or []):
            nm = (" ".join(x for x in [a.get("given", ""), a.get("family", "")] if x)).strip()
            if nm:
                authors.append({"name": nm, "affiliation": (a.get("affiliation") or [{}])[0].get("name", "")})
        refs = [r["DOI"] for r in (it.get("reference") or []) if r.get("DOI")][:60]
        out.append(_http.rec(
            "crossref", url=it.get("URL", "") or ("https://doi.org/" + doi),
            title=title, authors=authors, doi=doi, refs=refs,
            published=str((it.get("issued") or {}).get("date-parts", [[""]])[0][0] or ""),
            cited_by_count=it.get("is-referenced-by-count") or 0, primary=False,
            snippet="type=%s refs_deposited=%d cited_by=%s" % (
                it.get("type"), len(refs), it.get("is-referenced-by-count")),
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Crossref -> normalized records"))
