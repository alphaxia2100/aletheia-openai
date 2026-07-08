#!/usr/bin/env python3
"""Europe PMC client -> normalized records (JSONL). No key.

Class = evidence: free biomedical citation graph + OA full text. Usage:
europepmc.py "query" [--limit N].
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=%s&format=json&pageSize=%d&resultType=core"
           % (_http.quote(query), min(limit, 100)))
    data = _http.get_json(url, timeout)
    out: List[Dict[str, Any]] = []
    for r in ((data.get("resultList") or {}).get("result") or []):
        doi = r.get("doi", "") or ""
        pmcid = r.get("pmcid", "")
        authors = [{"name": a.strip()} for a in (r.get("authorString") or "").split(",") if a.strip()]
        if pmcid:
            link = "https://europepmc.org/article/PMC/" + pmcid
        elif doi:
            link = "https://doi.org/" + doi
        else:
            link = "https://europepmc.org/abstract/%s/%s" % (r.get("source", "MED"), r.get("id", ""))
        out.append(_http.rec(
            "europepmc", url=link, title=r.get("title", ""), authors=authors,
            published=str(r.get("pubYear") or ""), doi=doi,
            cited_by_count=r.get("citedByCount") or 0, primary=True,
            snippet="source=%s cited_by=%s" % (r.get("source"), r.get("citedByCount")),
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Europe PMC -> normalized records"))
