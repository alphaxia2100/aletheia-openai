#!/usr/bin/env python3
"""Stack Exchange client -> normalized records (JSONL).

Class = evidence: structured, voted, accepted answers make consensus AND
disagreement visible. Works keyless (300 req/day/IP); set STACKEXCHANGE_KEY for
10000/day. Site defaults to stackoverflow; override with --site via env SE_SITE.
Note: the SE API always gzip-encodes responses, handled here.
Usage: stackexchange.py "query" [--limit N].
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))
import _http  # noqa: E402


def _get_json_gz(url: str, timeout: float) -> Any:
    raw = _http.get_bytes(url, timeout, headers={"Accept-Encoding": "gzip"})
    if raw[:2] == b"\x1f\x8b":  # gzip magic
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8", "replace"))


def search(query: str, limit: int, timeout: float) -> List[Dict[str, Any]]:
    site = os.environ.get("SE_SITE", "stackoverflow")
    params = ("order=desc&sort=relevance&pagesize=%d&site=%s&q=%s"
              % (min(limit, 100), site, _http.quote(query)))
    key = os.environ.get("STACKEXCHANGE_KEY")
    if key:
        params += "&key=" + _http.quote(key)
    data = _get_json_gz("https://api.stackexchange.com/2.3/search/advanced?" + params, timeout)
    out: List[Dict[str, Any]] = []
    for it in data.get("items", []):
        owner = it.get("owner") or {}
        out.append(_http.rec(
            "stackexchange", url=it.get("link", ""),
            title=it.get("title", ""),
            authors=[{"name": owner.get("display_name", "")}] if owner.get("display_name") else [],
            published=str(it.get("creation_date", "")),
            primary=False,
            snippet="score=%s answers=%s accepted=%s" % (
                it.get("score"), it.get("answer_count"), it.get("is_answered")),
        ))
    return out


if __name__ == "__main__":
    raise SystemExit(_http.run_client(search, "Stack Exchange -> normalized records"))
