#!/usr/bin/env python3
"""Wikipedia search -> normalized records (JSONL). No key.

Class = lead_gen: fast orientation + canonical terms; follow its citations to
primaries, never cite the encyclopedia as final evidence. Usage: wikipedia.py "q" [--limit N].
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    url = ("https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=%d&srsearch=%s"
           % (min(limit, 50), _http.quote(query)))
    data = _http.get_json(url, timeout)
    out: List[Dict[str, Any]] = []
    for r in ((data.get("query") or {}).get("search") or []):
        title = r.get("title", "")
        snippet = re.sub("<[^>]+>", "", r.get("snippet", ""))
        out.append(_http.rec(
            "wikipedia",
            url="https://en.wikipedia.org/wiki/" + _http.quote(title.replace(" ", "_")),
            title=title, primary=False,
            snippet=snippet[:220],
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Wikipedia -> normalized records"))
