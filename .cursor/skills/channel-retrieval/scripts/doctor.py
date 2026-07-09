#!/usr/bin/env python3
"""Aletheia channel doctor — health-probe + ordered failover.

Adopts the one genuinely good idea from agent-reach: for every channel, probe
the real backend(s) in priority order and report which is live, so a dead source
degrades gracefully instead of failing a survey. No-key channels are live-probed;
key-gated channels are reported as configured/not-configured.

Usage: doctor.py [--timeout S] [--json]
Pure Python 3.9+ stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

UA = "aletheia-doctor/0.1"


def load_env() -> None:
    """Populate os.environ from the nearest .env (walking up), without overriding real env."""
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


def live(url: str, timeout: float, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (resp.status < 400, "HTTP %s" % resp.status)
    except urllib.error.HTTPError as e:
        # a 4xx still means the endpoint is up (auth/quota, not down)
        return (e.code < 500, "HTTP %s" % e.code)
    except Exception as e:  # noqa: BLE001
        return (False, type(e).__name__)


def key(var: str) -> bool:
    return bool(os.environ.get(var))


# Each probe returns (channel, index_group, status, active_backend, note).
# status: ok | warn | down | unconfigured

def p_brave(t: float) -> Tuple[str, ...]:
    if key("BRAVE_API_KEY"):
        ok, note = live("https://api.search.brave.com/res/v1/web/search?q=test&count=1", t,
                        {"X-Subscription-Token": os.environ["BRAVE_API_KEY"], "Accept": "application/json"})
        if ok:
            return ("brave", "brave", "ok", "brave", "independent web index (live)")
        return ("brave", "brave", "warn", "brave", "key set but probe failed: " + note)
    return ("brave", "brave", "warn", "fetch/jina", "no BRAVE_API_KEY -> losing your independent web index; add free key")


def p_openalex(t: float) -> Tuple[str, ...]:
    url = "https://api.openalex.org/works?per_page=1"
    if key("OPENALEX_API_KEY"):
        url += "&api_key=" + os.environ["OPENALEX_API_KEY"]
    ok, note = live(url, t)
    if ok and key("OPENALEX_API_KEY"):
        return ("openalex", "openalex", "ok", "openalex", note)
    if ok:
        return ("openalex", "openalex", "warn", "openalex", "up but add OPENALEX_API_KEY (2026 free key; low quota without)")
    return ("openalex", "openalex", "down", "-", note)


def _simple(name: str, group: str, url: str, t: float, headers=None, warn_note="") -> Tuple[str, ...]:
    ok, note = live(url, t, headers)
    return (name, group, "ok" if ok else "down", name if ok else "-", note if ok else (warn_note or note))


def p_search(name: str, group: str, modname: str, t: float, q: str = "climate change effects") -> Tuple[str, ...]:
    """FUNCTIONAL probe: actually call the client's search() and count results, so a channel that is
    HTTP-200 but returns NOTHING (e.g. a dead scrape endpoint or an API change) shows as `warn`,
    not a false `ok`. This is what lets Aletheia surface silently-broken channels."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
        m = __import__(modname)
        fn = getattr(m, "search", None) or getattr(m, "yt_search", None)
        out = fn(q, 3, t) or []
        n = len(out)
        return (name, group, "ok" if n else "warn", name,
                ("%d results" % n) if n else "live but 0 results — DEGRADED (check client/endpoint)")
    except Exception as e:  # noqa: BLE001
        return (name, group, "down", "-", "%s: %s" % (type(e).__name__, str(e)[:55]))


def p_arxiv(t: float) -> Tuple[str, ...]:
    ok, note = live("https://export.arxiv.org/api/query?search_query=all:test&max_results=1", t)
    if "429" in note:
        return ("arxiv", "arxiv", "warn", "arxiv", "rate-limited (429); circuit-breaker active — use openalex/semanticscholar")
    return ("arxiv", "arxiv", "ok" if ok else "down", "arxiv" if ok else "-", note)
def p_hn(t): return p_search("hackernews", "hackernews", "hn", t)
def p_wikipedia(t): return _simple("wikipedia", "wikipedia", "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=test&format=json&srlimit=1", t)
def p_duckduckgo(t): return p_search("duckduckgo", "duckduckgo", "web_ddg", t)
def p_marginalia(t): return p_search("marginalia", "marginalia", "web_marginalia", t)
def p_jina(t): return _simple("read (jina)", "jina", "https://r.jina.ai/https://example.com", t)


def p_x(t: float) -> Tuple[str, ...]:
    tw = shutil.which("twitter") or next(
        (p for p in (os.path.expanduser("~/.local/bin/twitter"),
                     os.path.expanduser("~/.aletheia-agentreach/bin/twitter")) if os.path.exists(p)), None)
    if tw:
        try:
            r = subprocess.run([tw, "status"], capture_output=True, text=True, timeout=t)
            out = (r.stdout + r.stderr).lower()
            if "ok: true" in out or "authenticated: true" in out:
                return ("x", "x", "ok", "agent-reach", "logged-in session (color-only)")
            return ("x", "x", "warn", "twitter-cli", "installed; log into x.com then `agent-reach configure --from-browser chrome`")
        except Exception:  # noqa: BLE001
            pass
    if key("GETXAPI_KEY") or key("TWITTERAPI_IO_KEY"):
        return ("x", "x", "ok", "paid-api", "key set (color-only)")
    return ("x", "x", "warn", "agent-reach", "install agent-reach + twitter, or set GETXAPI/TWITTERAPI_IO_KEY")


def p_youtube(t: float) -> Tuple[str, ...]:
    import importlib.util
    has_lib = importlib.util.find_spec("youtube_transcript_api") is not None
    ok, note = live("https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v=aircAruvnKk", t)
    if ok and has_lib:
        return ("youtube (transcripts)", "youtube", "ok", "youtube-transcript-api", "no-key captions")
    if ok:
        return ("youtube (transcripts)", "youtube", "warn", "-", "reachable; pip install --user youtube-transcript-api yt-dlp")
    return ("youtube (transcripts)", "youtube", "down", "-", note)
def p_se(t): return p_search("stackexchange", "stackexchange", "stackexchange", t, q="python asyncio")
def _has_cli(name: str) -> bool:
    if shutil.which(name):
        return True
    return any(os.path.exists(os.path.join(os.path.expanduser(d), name))
               for d in ("~/.local/bin", "~/.npm-global/bin"))


def p_reddit(t: float) -> Tuple[str, ...]:
    if _has_cli("opencli") or _has_cli("rdt"):
        return ("reddit", "reddit", "ok", "agent-reach", "live/authed via opencli (browser session)")
    ok, note = live("https://api.pullpush.io/reddit/search/submission/?q=test&size=1", t)
    if ok:
        return ("reddit", "reddit", "ok", "pullpush", "no-key archive (agent-reach reddit backend not installed)")
    return ("reddit", "reddit", "down", "-", note)
def p_gutendex(t): return _simple("gutenberg", "gutenberg", "https://gutendex.com/books?search=test", t)
def p_openlibrary(t): return _simple("openlibrary", "internet_archive", "https://openlibrary.org/search.json?q=test&limit=1", t)
def p_europepmc(t): return _simple("europepmc", "europepmc", "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=test&format=json&pageSize=1", t)
def p_crossref(t): return _simple("crossref", "crossref", "https://api.crossref.org/works?rows=1", t)


def p_github(t: float) -> Tuple[str, ...]:
    name, group, status, active, note = p_search("github", "github", "github", t, q="deep learning")
    return (name, group, status, active, note + ("" if key("GITHUB_TOKEN") else " (60/hr unauth; add GITHUB_TOKEN)"))


def p_s2(t: float) -> Tuple[str, ...]:
    ok, note = live("https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1", t)
    throttled = "429" in note
    status = "ok" if (ok and not throttled) else "warn"
    detail = note if (ok and not throttled) else "shared anon pool throttles (429); add SEMANTIC_SCHOLAR_API_KEY"
    return ("semantic_scholar", "semantic_scholar", status, "semantic_scholar" if status == "ok" else "semantic_scholar", detail)


def p_googlebooks(t: float) -> Tuple[str, ...]:
    url = "https://www.googleapis.com/books/v1/volumes?q=test&maxResults=1"
    if key("GOOGLE_BOOKS_API_KEY"):
        url += "&key=" + os.environ["GOOGLE_BOOKS_API_KEY"]
    ok, note = live(url, t)
    throttled = "429" in note
    status = "ok" if (ok and not throttled) else "warn"
    detail = note if (ok and not throttled) else "keyless throttled (429); add GOOGLE_BOOKS_API_KEY"
    return ("google_books", "google_books", status, "google_books", detail)


def p_keyonly(name: str, group: str, var: str) -> Tuple[str, ...]:
    if key(var):
        return (name, group, "ok", name, "%s set" % var)
    return (name, group, "unconfigured", "-", "set %s to enable" % var)


LIVE_PROBES = [p_brave, p_openalex, p_arxiv, p_hn, p_se, p_reddit, p_gutendex,
               p_openlibrary, p_europepmc, p_crossref, p_github, p_s2, p_googlebooks,
               p_wikipedia, p_duckduckgo, p_marginalia, p_jina, p_youtube, p_x]

# Map a probe's display name to its channels.json index id (for core filtering).
_CID = {
    "serper (one Google window)": "google_serper",
    "supadata (youtube)": "supadata",
    "taddy (podcasts)": "taddy",
    "reddit-oauth (PRAW live)": "reddit-oauth",
    "youtube (transcripts)": "youtube",
    "read (jina)": "read",
}


def _cid(display: str) -> str:
    return _CID.get(display, display)


def _enabled_set() -> set:
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "channels.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        return set(d.get("enabled", [])) | set(d.get("utilities_always_on", []))
    except Exception:  # noqa: BLE001
        return set()

KEYONLY = [
    ("exa", "exa_neural", "EXA_API_KEY"),
    ("perplexity", "perplexity", "PERPLEXITY_API_KEY"),
    ("linkup", "linkup", "LINKUP_API_KEY"),
    ("firecrawl", "firecrawl", "FIRECRAWL_API_KEY"),
    ("serper (one Google window)", "google", "SERPER_API_KEY"),
    ("supadata (youtube)", "youtube", "SUPADATA_API_KEY"),
    ("taddy (podcasts)", "podcast", "TADDY_API_KEY"),
    ("scite", "scite", "SCITE_API_TOKEN"),
    ("reddit-oauth (PRAW live)", "reddit", "REDDIT_CLIENT_ID"),
]

_ORDER = {"ok": 0, "warn": 1, "down": 2, "unconfigured": 3}


def run(timeout: float) -> List[Tuple[str, ...]]:
    rows: List[Tuple[str, ...]] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(fn, timeout) for fn in LIVE_PROBES]
        for f in futs:
            try:
                rows.append(f.result())
            except Exception as e:  # noqa: BLE001
                rows.append(("?", "?", "down", "-", type(e).__name__))
    for name, group, var in KEYONLY:
        rows.append(p_keyonly(name, group, var))
    rows.sort(key=lambda r: (_ORDER.get(r[2], 9), r[0]))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Aletheia channel doctor")
    ap.add_argument("--timeout", type=float, default=6.0)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true", help="show disabled/hidden channels too (default: core only)")
    args = ap.parse_args()

    load_env()
    rows = run(args.timeout)
    total = len(rows)
    if not args.all:
        enabled = _enabled_set()
        if enabled:
            rows = [r for r in rows if _cid(r[0]) in enabled]
    hidden = total - len(rows)
    if args.json:
        keys = ("channel", "index_group", "status", "active_backend", "note")
        json.dump([dict(zip(keys, r)) for r in rows], sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    w = max(len(r[0]) for r in rows) + 2
    print("Aletheia channels  (ok=live, warn=degraded/keyless, down=unreachable, unconfigured=needs key)\n")
    print("%-*s %-13s %-16s %s" % (w, "CHANNEL", "STATUS", "ACTIVE", "NOTE"))
    print("-" * 96)
    for name, group, status, active, note in rows:
        print("%-*s %-13s %-16s %s" % (w, name, status, active, note))
    live_ok = sum(1 for r in rows if r[2] == "ok")
    scope = "all" if args.all else "core"
    print("\n%d/%d %s channels live." % (live_ok, len(rows), scope))
    if hidden:
        print("%d channels hidden (disabled). Run with --all to see them, or `channels.py enable <name>`." % hidden)
    # Honest caveat: these probes are SEQUENTIAL single requests. They confirm a channel is REACHABLE,
    # not that it survives concurrent fan-out — deep/exhaustive spawn many workers that hit arXiv /
    # OpenAlex / Semantic Scholar in parallel and may still 429 (the keyless pools rate-limit under
    # load). 'ok' = reachable now; watch each run's per-channel `error`/`relaxed_to` for live degradation.
    print("\nNote: sequential single-request probes — 'ok' means REACHABLE, not concurrency-proof. "
          "Under parallel fan-out (deep/exhaustive) the keyless academic pools (arXiv/OpenAlex/"
          "Semantic Scholar) may still rate-limit; check per-channel errors in the run's evidence.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
