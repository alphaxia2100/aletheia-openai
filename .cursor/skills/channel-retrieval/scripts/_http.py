#!/usr/bin/env python3
"""Shared helpers for the no-install channel clients.

Every client emits normalized source records (JSONL) that feed provenance_graph.py.
Pure Python 3.9+ stdlib.
"""
from __future__ import annotations

import datetime as _dt
import ipaddress
import json
import os
import re
import socket
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

import _config

UA = "aletheia-surveyor/0.1 (research surveyor)"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024

_ENV_ALLOWLIST = frozenset((
    "APIFY_TOKEN", "BRAVE_API_KEY", "CORE_API_KEY", "EXA_API_KEY", "FIRECRAWL_API_KEY",
    "GETXAPI_KEY", "GITHUB_TOKEN", "GOOGLE_BOOKS_API_KEY", "JINA_API_KEY", "LINKUP_API_KEY",
    "NCBI_API_KEY", "OPENALEX_API_KEY", "OPENALEX_MAILTO", "PERPLEXITY_API_KEY",
    "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT", "SCITE_API_TOKEN",
    "SEMANTIC_SCHOLAR_API_KEY", "SERPER_API_KEY", "SE_SITE", "STACKEXCHANGE_KEY",
    "SUPADATA_API_KEY", "TADDY_API_KEY", "TADDY_USER_ID", "TWITTERAPI_IO_KEY",
))


def _private_regular_file(info: os.stat_result) -> bool:
    """Whether stat metadata describes an owner-only regular secret file."""
    if not stat.S_ISREG(info.st_mode):
        return False
    if os.name == "posix":
        if info.st_uid != os.getuid():
            return False
        # Connector keys are secrets: group/other read access is unsafe too, not merely
        # group/other write access.  Do not silently consume a permissive .env.
        if info.st_mode & 0o077:
            return False
    return True


def _safe_env_file(path: str) -> bool:
    """Accept a regular, owner-only connector configuration file, never a symlink."""
    try:
        # ``lstat`` is intentional: accepting a 0600 symlink would allow a local config path to
        # redirect credential loading outside the user-controlled capability directory.
        return _private_regular_file(os.lstat(path))
    except OSError:
        return False


def _load_env_file(path: str) -> bool:
    if not path or not _safe_env_file(path):
        return False
    fd = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        # Re-check the opened inode: the first lstat prevents ordinary symlinks and this closes
        # the time-of-check/time-of-use window on POSIX hosts that support O_NOFOLLOW.
        if not _private_regular_file(os.fstat(fd)):
            return False
        with os.fdopen(fd, "r", encoding="utf-8") as fh:
            fd = -1
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if key not in _ENV_ALLOWLIST or key in os.environ:
                    continue
                cut = value.find(" #")
                if cut != -1:
                    value = value[:cut]
                value = value.strip().strip('"').strip("'")
                if value:
                    os.environ[key] = value
        return True
    except OSError:
        return False
    finally:
        if fd >= 0:
            os.close(fd)


def load_env() -> None:
    """Load allowlisted connector settings from the explicit user config directory.

    Real environment variables always win.  Aletheia deliberately never loads a checkout/runtime
    `.env` or walks ancestor directories: portable copies must not carry secrets, and a working
    directory must not be able to inject them.  Put connector keys only in the user-scoped path.
    """
    user_env = os.path.join(_config.config_dir(), ".env")
    _load_env_file(user_env)


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


def validate_public_url(url: str) -> None:
    """Reject non-public HTTP(S) targets before a skill asks a remote service to read them.

    This is a best-effort application boundary, not a replacement for host network isolation.
    It blocks literal/private hosts, localhost aliases, non-standard ports, and hostnames resolving
    to non-global addresses.  Callers still need a harness policy for defense against DNS rebinding.
    """
    parsed = urllib.parse.urlsplit(str(url))
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("only absolute http(s) URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid URL port") from exc
    default_port = 443 if parsed.scheme == "https" else 80
    if port not in (None, default_port):
        raise ValueError("only standard HTTP(S) ports are allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("localhost targets are not allowed")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not literal.is_global:
            raise ValueError("non-public IP targets are not allowed")
        return
    try:
        infos = socket.getaddrinfo(host, port or default_port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("hostname could not be resolved") from exc
    addresses = {info[4][0] for info in infos}
    if not addresses:
        raise ValueError("hostname resolved to no addresses")
    for address in addresses:
        if not ipaddress.ip_address(address).is_global:
            raise ValueError("hostname resolves to a non-public IP")


class _PublicOnlyRedirect(urllib.request.HTTPRedirectHandler):
    """Validate every redirect rather than trusting urllib's default redirect policy."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get_bytes(url: str, timeout: float = 10.0, headers: Optional[Dict[str, str]] = None,
              retries: int = 2, max_bytes: int = MAX_RESPONSE_BYTES) -> bytes:
    """Bounded public-HTTP GET with retries on transient upstream failures."""
    validate_public_url(url)
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _PublicOnlyRedirect())
            with opener.open(req, timeout=timeout) as resp:
                body = resp.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise ValueError("response exceeded %d byte limit" % max_bytes)
                return body
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
    """Return immutable bundled metadata plus the current user preference overlay.

    Do not cache this: `channels.py enable` may run in the same long-lived agent process, and
    preferences must take effect without mutating the installed skill or restarting the host.
    """
    try:
        return _config.load_channels()
    except Exception:  # noqa: BLE001 - preserve the old safe empty-config fallback
        return {"indexes": {}}


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


_CLI_CHANNELS = {
    "arxiv": "arxiv", "brave": "brave", "crossref": "crossref", "europepmc": "europepmc",
    "github": "github", "googlebooks": "google_books", "gutendex": "gutenberg", "hn": "hackernews",
    "openalex": "openalex", "openlibrary": "openlibrary", "semanticscholar": "semantic_scholar",
    "stackexchange": "stackexchange", "web_ddg": "duckduckgo", "web_marginalia": "marginalia",
    "wikipedia": "wikipedia",
}


def run_client(fn, description: str) -> int:
    """Standard CLI wrapper: `client.py "query" [--limit N] [--timeout S]`."""
    import argparse
    script = os.path.basename(sys.argv[0]).rsplit(".", 1)[0]
    channel = _CLI_CHANNELS.get(script)
    if channel:
        try:
            _config.require_enabled(channel)
        except PermissionError as exc:
            sys.stderr.write("refusing disabled Aletheia channel: %s\n" % exc)
            return 2
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
