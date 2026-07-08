#!/usr/bin/env python3
"""Shared helpers for the no-install channel clients.

Every client emits normalized source records (JSONL) that feed provenance_graph.py.
Pure Python 3.9+ stdlib.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

UA = "aletheia-surveyor/0.1 (research surveyor)"

_CHANNELS_CACHE: Optional[Dict[str, Any]] = None


def load_env() -> None:
    """Populate os.environ from the nearest .env (walking up), without overriding
    real env. Uses realpath so it finds the repo's .env even when this file is
    reached through a ~/.cursor/skills symlink (i.e. used from another project)."""
    d = os.path.dirname(os.path.realpath(__file__))
    for _ in range(8):
        p = os.path.join(d, ".env")
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, _, v = line.partition("=")
                        k = k.strip()
                        cut = v.find(" #")
                        if cut != -1:
                            v = v[:cut]
                        v = v.strip().strip('"').strip("'")
                        if k and v and k not in os.environ:
                            os.environ[k] = v
            except OSError:
                pass
            return
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent


load_env()  # so every client sees keys from .env


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def quote(s: str) -> str:
    return urllib.parse.quote(str(s))


def get_bytes(url: str, timeout: float = 10.0, headers: Optional[Dict[str, str]] = None,
              retries: int = 2) -> bytes:
    """GET with exponential backoff on 429 / 5xx / transient network errors."""
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                ra = e.headers.get("Retry-After") if e.headers else None
                delay = float(ra) if (ra and str(ra).strip().isdigit()) else min(1.5 * (2 ** attempt), 30)
                time.sleep(min(delay, 30))  # honor Retry-After, else exponential backoff (capped)
                continue
            raise
        except urllib.error.URLError as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
    if last_err:
        raise last_err
    raise RuntimeError("get_bytes failed")


def get_json(url: str, timeout: float = 10.0, headers: Optional[Dict[str, str]] = None) -> Any:
    return json.loads(get_bytes(url, timeout, headers).decode("utf-8", "replace"))


def load_channels() -> Dict[str, Any]:
    global _CHANNELS_CACHE
    if _CHANNELS_CACHE is None:
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "channels.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                _CHANNELS_CACHE = json.load(fh)
        except Exception:
            _CHANNELS_CACHE = {"indexes": {}}
    return _CHANNELS_CACHE


def class_for(index_of_origin: str) -> str:
    idx = load_channels().get("indexes", {}).get(index_of_origin, {})
    return idx.get("class", "lead_gen")


def primary_default_for(index_of_origin: str) -> bool:
    idx = load_channels().get("indexes", {}).get(index_of_origin, {})
    return bool(idx.get("primary_default", False))


def rec(index_of_origin: str, url: str, title: str = "", **kw: Any) -> Dict[str, Any]:
    """Build a normalized source record with sensible defaults."""
    record = {
        "id": kw.get("id") or _short_id(index_of_origin, url),
        "url": url,
        "index_of_origin": index_of_origin,
        "title": title,
        "authors": kw.get("authors", []),
        "published": kw.get("published", ""),
        "doi": kw.get("doi", ""),
        "refs": kw.get("refs", []),
        "derives_from": kw.get("derives_from", []),
        "primary": kw.get("primary", primary_default_for(index_of_origin)),
        "cited_by_count": kw.get("cited_by_count", 0),
        "snippet": kw.get("snippet", ""),
        "channel_class": kw.get("channel_class") or class_for(index_of_origin),
        "retrieved_at": now_iso(),
    }
    return record


def _short_id(prefix: str, url: str) -> str:
    import hashlib
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return prefix[:4] + "-" + h


def emit(records: List[Dict[str, Any]]) -> None:
    for r in records:
        sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


def run_client(fn, description: str) -> int:
    """Standard CLI wrapper: `client.py "query" [--limit N] [--timeout S]`."""
    import argparse
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("query", help="search query")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--timeout", type=float, default=10.0)
    args = ap.parse_args()
    try:
        records = fn(args.query, args.limit, args.timeout)
    except Exception as e:  # noqa: BLE001 - clients are best-effort
        sys.stderr.write("error: %s: %s\n" % (type(e).__name__, e))
        return 1
    emit(records)
    return 0
