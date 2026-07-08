#!/usr/bin/env python3
"""agent-reach adapter — a SWAPPABLE backend layer.

agent-reach (https://github.com/Panniantong/Agent-Reach) gives free, browser-session
access to walled gardens (X, Reddit, YouTube, GitHub, Bilibili, ...). This module is
the thin adapter that calls its upstream CLIs and maps their output into Aletheia's
normalized record schema.

The whole point (per the plugin/adapter design): backends break and get replaced. When
a platform's CLI changes or dies, you swap it HERE — reorder/replace the command +
parser in one place — without touching the channel clients. Each channel client
(x.py, reddit.py, ...) just declares an ordered list of backends and uses the first
that returns data.

Nothing here is required: if agent-reach isn't installed, every function degrades to
"unavailable" and the channel client falls back to its native no-key backend.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

# agent-reach's CLIs land in various user bins depending on how they were installed
# (twitter -> ~/.local/bin; opencli/mcporter -> the npm global prefix, often ~/.npm-global/bin).
# These are frequently NOT on a non-interactive shell's PATH, so we search them explicitly.
_EXTRA_BINS = [
    os.path.expanduser("~/.local/bin"),
    os.path.expanduser("~/.npm-global/bin"),
    "/usr/local/bin",
    "/opt/homebrew/bin",
]


def find_cli(name: str) -> Optional[str]:
    """Locate an agent-reach upstream CLI on PATH or in the common user bins."""
    p = shutil.which(name)
    if p:
        return p
    for d in _EXTRA_BINS:
        cand = os.path.join(d, name)
        if os.path.exists(cand):
            return cand
    return None


def _augmented_env() -> Dict[str, str]:
    """Ensure node/opencli/twitter and their runtimes resolve even from a bare PATH."""
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(_EXTRA_BINS + [env.get("PATH", "")])
    return env


def _run(cmd: List[str], timeout: float) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=_augmented_env())
        return r.stdout or ""
    except Exception:  # noqa: BLE001 - a dead/absent backend must never crash the survey
        return ""


# ---------------- X / Twitter (backend: agent-reach twitter-cli) ----------------

def twitter_authed(timeout: float = 10.0) -> bool:
    tw = find_cli("twitter")
    if not tw:
        return False
    out = _run([tw, "status"], timeout).lower()
    return "ok: true" in out or "authenticated: true" in out or '"authenticated": true' in out


def x_search(query: str, limit: int = 15, top: bool = False, frm: str = "",
             since: str = "", timeout: float = 45.0):
    """Return (records, error). error is None on success, else a short reason."""
    import _http  # local import so this module is importable without side effects
    tw = find_cli("twitter")
    if not tw:
        return [], "twitter CLI not found (agent-reach not installed?)"
    cmd = [tw, "search", query, "--type", "top" if top else "latest",
           "-n", str(limit), "--json"]
    if frm:
        cmd += ["--from", frm]
    if since:
        cmd += ["--since", since]
    out = _run(cmd, timeout).strip()
    if not out:
        return [], "no output (not logged in? run: agent-reach configure --from-browser chrome)"
    import json
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return [], "non-JSON output from twitter CLI"
    if isinstance(data, dict) and data.get("ok") is False:
        return [], (data.get("error") or {}).get("code", "not_authenticated")

    # locate the tweet list (agent-reach: {ok, schema_version, data:[...]})
    if isinstance(data, list):
        tweets = data
    elif isinstance(data, dict):
        d = data.get("data")
        if isinstance(d, list):
            tweets = d
        elif isinstance(d, dict):
            tweets = d.get("tweets") or d.get("results") or []
        else:
            tweets = data.get("tweets") or data.get("results") or []
    else:
        tweets = []

    records: List[Dict[str, Any]] = []
    for t in tweets:
        if not isinstance(t, dict):
            continue
        text = t.get("text") or t.get("full_text") or t.get("content") or ""
        author = t.get("author") or t.get("user") or {}
        handle = (author.get("screenName") or author.get("screen_name")
                  or author.get("username") or author.get("handle") or "")
        name = author.get("name") or handle
        tid = str(t.get("id") or t.get("id_str") or "")
        m = t.get("metrics") or {}
        likes = m.get("likes", t.get("favorite_count", t.get("like_count", 0)))
        rts = m.get("retweets", t.get("retweet_count", 0))
        url = ("https://x.com/%s/status/%s" % (handle, tid)) if (handle and tid) else (t.get("url") or "")
        published = t.get("createdAtISO") or t.get("createdAt") or t.get("created_at") or ""
        records.append(_http.rec(
            "x", url=url, title=("@%s" % handle) if handle else (name or "tweet"),
            authors=[{"name": handle or name}] if (handle or name) else [],
            published=published, primary=False,
            snippet="likes=%s rts=%s :: %s" % (likes, rts, text[:220]),
        ))
    return records, None


# ---------------- Reddit (backend: agent-reach opencli / rdt) ----------------

def reddit_backend() -> Optional[str]:
    """Name of an available agent-reach Reddit CLI, else None (falls back to native)."""
    for name in ("opencli", "rdt"):
        if find_cli(name):
            return name
    return None


# ---------------- Generic browser bridge (the JS/paywall way-around) ----------------

def browser_available() -> bool:
    return find_cli("opencli") is not None


def browser_extract(url: str, timeout: float = 60.0, max_chars: int = 40000,
                    session: str = "aletheia") -> Tuple[str, Optional[str]]:
    """Render a URL in the real, logged-in Chrome (opencli Browser Bridge) and
    extract readable markdown. This is how you get past JS-rendered pages and
    login/soft-paywalls that Jina returns as stubs — it's an actual authenticated
    browser executing the page. Returns (text, error).
    """
    import json
    cli = find_cli("opencli")
    if not cli:
        return "", "opencli not installed"
    _run([cli, "browser", session, "open", url, "--window", "background"], timeout)
    parts: List[str] = []
    start = 0
    for _ in range(6):  # cap pages so a huge doc can't spin forever
        out = _run([cli, "browser", session, "extract", "--start", str(start)], timeout).strip()
        if not out:
            break
        try:
            d = json.loads(out)
        except json.JSONDecodeError:
            break
        parts.append(d.get("content") or d.get("markdown") or "")
        nsc = d.get("next_start_char")
        if not nsc or sum(len(p) for p in parts) >= max_chars:
            break
        start = nsc
    text = "\n".join(p for p in parts if p).strip()
    if not text:
        return "", "empty extract"
    return (text[:max_chars] if max_chars > 0 else text), None


# ---------------- Reddit thread reader (post + comments) ----------------

def reddit_post_id(s: str) -> str:
    s = s.strip()
    m = re.search(r"comments/([a-z0-9]+)", s) or re.search(r"redd\.it/([a-z0-9]+)", s)
    if m:
        return m.group(1)
    return s  # already a bare id


def reddit_read(post: str, timeout: float = 90.0) -> Tuple[str, Optional[str]]:
    """Read a full Reddit thread (OP + comments) via opencli's authed browser.
    `opencli reddit read <id> -f json` returns a list: [post, comment, comment, ...].
    Returns (thread_markdown, error). This is the un-laundered layer, read in full.
    """
    import json
    cli = find_cli("opencli")
    if not cli:
        return "", "opencli not installed"
    pid = reddit_post_id(post)
    out = _run([cli, "reddit", "read", pid, "-f", "json"], max(timeout, 90.0)).strip()
    if not out:
        return "", "opencli reddit read returned nothing (logged in?)"
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return "", "reddit read output not JSON"
    items = data if isinstance(data, list) else (data.get("data") or data.get("comments") or [])
    if not items:
        return "", "no thread content"
    op = items[0] if isinstance(items[0], dict) else {}
    op_text = (op.get("text") or op.get("selftext") or op.get("title") or "").strip()
    sub = (op.get("subreddit") or "").strip()
    lines = ["# Reddit thread" + (" (r/%s)" % sub if sub else ""),
             "**OP** u/%s (score %s):\n%s\n" % (op.get("author", ""), op.get("score", ""), op_text),
             "## Comments (%d)" % (len(items) - 1)]
    for c in items[1:]:
        if not isinstance(c, dict):
            continue
        ctext = (c.get("text") or c.get("body") or "").strip()
        if ctext:
            lines.append("- u/%s (%s): %s" % (c.get("author", ""), c.get("score", ""), ctext))
    return "\n".join(lines).strip(), None


def reddit_search(query: str, limit: int = 10, subreddit: str = "", timeout: float = 45.0):
    """Live/authed Reddit via agent-reach's opencli (or rdt). Returns (records, error).

    opencli reddit is browser-automated and slow (~30-40s), so we floor the timeout.
    Verified against opencli 1.8.x: `reddit search <q> --limit N --sort relevance -f json`
    returns a top-level JSON list of posts
    (keys: id, title, subreddit, author, score, comments, url, created_utc, selftext).
    """
    import _http
    import json
    backend = reddit_backend()
    if not backend:
        return [], "no agent-reach reddit backend (opencli/rdt) installed"
    cli = find_cli(backend)
    t = max(timeout, 75.0)  # opencli drives a browser; give it room
    if backend == "opencli":
        if subreddit:
            cmd = [cli, "reddit", "subreddit", subreddit, "--limit", str(limit), "-f", "json"]
        else:
            cmd = [cli, "reddit", "search", query, "--limit", str(limit), "--sort", "relevance", "-f", "json"]
    else:  # rdt-cli
        cmd = [cli, "search", query, "--limit", str(limit), "--json"]
    out = _run(cmd, t).strip()
    if not out:
        return [], "%s returned nothing (logged in? run: opencli reddit whoami)" % backend
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return [], "%s output not JSON" % backend
    rows = data if isinstance(data, list) else (
        data.get("data") or data.get("results") or data.get("posts") or [])
    records = []
    for d in rows[:limit]:
        if not isinstance(d, dict):
            continue
        body = (d.get("selftext") or d.get("body") or d.get("text") or "").strip()
        sub = (d.get("subreddit") or "").strip()
        if sub and not sub.startswith("r/"):
            sub = "r/" + sub
        records.append(_http.rec(
            "reddit",
            url=d.get("url") or d.get("permalink") or "",
            title=d.get("title") or ("%s comment" % sub),
            authors=[{"name": d.get("author", "")}] if d.get("author") else [],
            published=str(d.get("created_utc") or d.get("created") or ""),
            primary=False,
            snippet="%s score=%s comments=%s :: %s" % (
                sub, d.get("score"),
                d.get("comments", d.get("num_comments", "")), body[:200]),
        ))
    return records, None
