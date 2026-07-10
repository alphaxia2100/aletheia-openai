#!/usr/bin/env python3
"""Shared helpers for the no-install channel clients.

Every client emits normalized source records (JSONL) that feed provenance_graph.py.
Pure Python 3.9+ stdlib.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
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
    reached through a skill symlink. Copy installs carry a non-secret `.aletheia-root` pointer so
    they retain the repository's single source of truth without duplicating secrets."""
    roots = []
    override = os.environ.get("ALETHEIA_ROOT", "").strip()
    if override:
        roots.append(override)
    d = os.path.dirname(os.path.realpath(__file__))
    marker = os.path.realpath(os.path.join(d, "..", ".aletheia-root"))
    try:
        with open(marker, "r", encoding="utf-8") as fh:
            pointed = fh.readline().strip()
        if pointed:
            roots.append(pointed)
    except OSError:
        pass
    roots.append(d)

    seen = set()
    for root in roots:
        d = os.path.abspath(os.path.expanduser(root))
        if d in seen:
            continue
        seen.add(d)
        # Explicit roots point directly at the repository; the script root still walks upward.
        limit = 1 if root != roots[-1] else 8
        for _ in range(limit):
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


_KW_STOP = set(
    "the a an of for and or to in on is are be was were with without vs versus more than most "
    "how what why which when who into over under about across your our their its it this that these "
    "those do does did can could should would will may might best good better new using use used "
    "study studies research paper papers review overview guide intro introduction survey whether".split())

# Common orchestration language is useful in a human prompt but weakens compact API queries. Keep
# these terms as a last resort rather than dropping them outright: a standards-specific question can
# still retain "standards" when the requested budget has room, while its actual subject wins first.
_KW_META = set(
    "primary primaries standard standards guidance establish establishes established exact strongest "
    "case cases threat threats model models support supports supported comparison comparisons compare "
    "hunt decisive source sources contrary result results treating investigate distinguish".split())


_ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,5}\b")        # RAG, LLM, GPT, USA, 10K — short but salient
_PROPER_RE = re.compile(r"\b[A-Z][A-Za-z0-9]{2,}\b")       # Claude, Tavily, PyTorch — proper nouns


def keywordize(query: str, n: int = 6) -> str:
    """Reduce a long natural-language query to n keywords for KEYWORD-matching APIs (HN Algolia,
    Stack Exchange, GitHub, Marginalia, and any index that ANDs terms), which return NOTHING when a
    long sentence over-constrains them. Selection priority: (1) quoted phrases; (2) the first two
    non-meta content units, because natural and anchored queries front-load the subject; (3) ENTITY
    terms (acronyms / proper nouns / identifiers) from anywhere, which rescues late names such as
    Exa/Tavily; (4) remaining content in discovery order, then orchestration meta terms. Length is
    never used as salience because it rewards generic filler like 'significantly' over 'acid rain'.
    Total output is capped at n units. Short queries and quoted phrases pass through/are preserved."""
    if not query or len(query.split()) <= n:
        return query
    phrases = re.findall(r'"([^"]+)"', query)
    acronyms = set(_ACRONYM_RE.findall(query))
    caps = set()
    for match in _PROPER_RE.finditer(query):
        raw = match.group(0)
        before = query[:match.start()].rstrip()
        # A capital after sentence punctuation is usually grammar ("Hunt ..."), not an entity.
        # True acronyms remain entities even at sentence start.
        if raw.isupper() or (before and before[-1] not in ".!?"):
            caps.add(raw.lower())
    in_phrases = " ".join(phrases).lower()
    kept, seen = [], set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9+.#_-]{1,}", query):
        # A sentence-final period used to turn ordinary words such as "results." into apparent
        # identifiers and crowd the actual subject out of a short query.
        w = raw.lower().rstrip(".")
        if w in seen or (in_phrases and w in in_phrases) or w in _KW_STOP:
            continue
        if len(w) < 3 and w.upper() not in acronyms:       # keep short ALL-CAPS acronyms (AI/ML/RAG)
            continue
        seen.add(w)
        kept.append(w)

    def _is_entity(w: str) -> bool:                         # distinctive regardless of position
        has_alpha = any(c.isalpha() for c in w)
        has_digit = any(c.isdigit() for c in w)
        # Preserve GPT-4, C++, C#, node.js, and snake_case. Do not promote ordinary hyphenated
        # adjectives ("app-based") or bare dates ("2026-07-09") above the topic.
        identifier = (has_alpha and has_digit) or any(c in "+#_." for c in w)
        return w.upper() in acronyms or w in caps or identifier

    slots = max(0, n - len(phrases))
    # Always preserve the first two non-meta content units: natural questions (and Aletheia's
    # anchored leaf queries) front-load the actual subject. Then rescue late entities. This keeps
    # `synced passkeys` ahead of incidental TOTP/RP/date tokens without regressing late Exa/Tavily.
    entities = [i for i, w in enumerate(kept) if _is_entity(w) and w not in _KW_META]
    ordinary = [i for i, w in enumerate(kept) if not _is_entity(w) and w not in _KW_META]
    non_meta = [i for i, w in enumerate(kept) if w not in _KW_META]
    front = non_meta[:min(2, slots)]
    remaining_entities = [i for i in entities if i not in front]
    remaining_ordinary = [i for i in ordinary if i not in front]
    meta = [i for i, w in enumerate(kept) if w in _KW_META]
    priority = front + remaining_entities + remaining_ordinary + meta
    chosen = set(priority[:slots])
    selected = [kept[i] for i in range(len(kept)) if i in chosen]
    return " ".join((phrases + selected)[:n]) or query     # cap TOTAL units at n (phrases can't overflow)


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
