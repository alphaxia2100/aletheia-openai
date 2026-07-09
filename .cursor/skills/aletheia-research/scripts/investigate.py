#!/usr/bin/env python3
"""Deep Aletheia — LEAF investigation pipeline (the DOK 1-2 engine).

Given a leaf node (a directory with a focused question + budget), do the full treatment and
write artifacts INTO the node dir:
  route channels -> retrieve (parallel) -> tag class -> dedupe -> authority-rank ->
  class-budgeted read IN FULL -> write sources.jsonl, notes/<h>.md, evidence.md, decisions.

The worker subagent then reads evidence.md/notes and writes findings.md (DOK 2-3: the compressed
claims-with-citations that bubble up). Run standalone it still produces a complete evidence pack.

Usage:
  investigate.py --node NODE_DIR [--query "..."] [--reads K] [--limit 8] [--channels a,b]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.realpath(__file__))
CH = os.path.join(HERE, "..", "..", "channel-retrieval", "scripts")
PROV = os.path.join(HERE, "..", "..", "provenance-audit", "scripts")
for p in (HERE, CH, PROV):
    sys.path.insert(0, p)

import re  # noqa: E402

import treestate  # noqa: E402
import router  # noqa: E402
import rank as rankmod  # noqa: E402
import dedupe  # noqa: E402
import read as readmod  # noqa: E402
import _http  # noqa: E402  (keywordize, for 0-result relaxation)

MAX_READ_CHARS = 40000   #: read cap; a read that hits it is flagged `_truncated` (no silent cut-off)
_ARXIV = re.compile(r"arxiv\.org/(?:abs|html|pdf)/([0-9]{4}\.[0-9]{4,5})", re.I)
_STOP = set("the a an of for and or to in on is are be was were with without vs versus more "
            "than better best effect effects does do how what why which when who into over "
            "real world results side its their your our".split())
#: generic/self-referential terms that never make a useful subject anchor (a topic that is a coined
#: artifact — "the X agent/skill/system" — anchored on these just injects self-reference).
_SELFREF = set("agent agents tool tools skill skills system systems framework frameworks design "
               "designs decision decisions assumption assumptions approach approaches project "
               "projects pipeline pipelines model models itself every core loop".split())
#: generic research/structure meta words — they describe HOW something is studied, not WHAT. On a
#: coined "deep per-component per-step survey" topic these are all that survive the proper-noun/
#: self-ref drop, so anchoring on them prepends pure fragment noise ("deep component step ..."). Dropped.
_META = set("deep survey research study studies review reviews analysis analyses overview summary "
            "comparison comparisons component components step steps phase phases stage stages part "
            "parts section sections aspect aspects factor factors general overall audit self".split())


def _run_topic(node: str) -> str:
    run = treestate._find_run(node)
    cfg = treestate._read_json(os.path.join(run, "run.json"), {}) or {}
    return cfg.get("topic", "") if run else ""


def _proper_nouns(topic: str) -> set:
    """Tokens that look like a PROPER NOUN / coined name in the ORIGINAL topic string — a
    capitalized word that is either not sentence-initial or part of a Capitalized run (e.g.
    'Aletheia Research', 'OpenAI Deep Research'). Anchoring on these returns self-referential junk,
    so they're dropped. Sentence-initial single caps (a Title-cased common noun) are NOT flagged."""
    words = re.findall(r"[A-Za-z][A-Za-z-]*", topic)
    proper = set()
    for i, w in enumerate(words):
        if len(w) >= 4 and w[:1].isupper():
            prev_cap = i > 0 and words[i - 1][:1].isupper()
            next_cap = i + 1 < len(words) and words[i + 1][:1].isupper()
            if i > 0 or prev_cap or next_cap:      # not a lone sentence-initial capital
                proper.add(w.lower())
    return proper


def _anchor(question: str, topic: str) -> str:
    """Keep an UNDER-SPECIFIED sub-question tied to the ROOT SUBJECT — a bare leaf like
    'real-world adherence' must still be about *intermittent fasting*, not medication adherence.
    But do NOT anchor when it would only pollute (the audited '_anchor injected Aletheia papers'
    bug): skip if the question already carries the subject or is self-contained, and build the
    anchor from COMMON-NOUN subject terms only (drop proper nouns + generic self-referential words)."""
    if not topic:
        return question
    tt = [w for w in re.findall(r"[a-z]{4,}", topic.lower()) if w not in _STOP]
    ql = question.lower()
    if sum(1 for w in set(tt) if w in ql) >= 2:            # already tied to the subject
        return question
    q_terms = {w for w in re.findall(r"[a-z]{4,}", ql) if w not in _STOP}
    if len(q_terms) >= 5:                                  # specific enough to stand on its own
        return question
    proper = _proper_nouns(topic)
    # candidates = the topic's content words minus proper nouns, self-ref, and generic research-meta
    # words. Since _META already strips the generic words, whatever survives is a real subject term —
    # so keep the FIRST few in topic order (do NOT rank by length: a short word like "keto"/"json"
    # is often the MOST specific term, and length-ranking would wrongly drop it for a longer generic
    # word). If nothing survives (pure proper noun / coined name / only meta words), leave unchanged.
    subj_terms = [w for w in dict.fromkeys(tt)
                  if w not in proper and w not in _SELFREF and w not in _META][:3]
    if not subj_terms:
        return question
    subj = " ".join(subj_terms)[:60]
    return (subj + " " + question).strip()


def _work_key(r: Dict[str, Any]) -> str:
    """Collapse the SAME work across URL variants so it never eats multiple read slots
    (arXiv abs/html/pdf + vN -> one id; DOI -> one)."""
    url = r.get("url", "") or ""
    m = _ARXIV.search(url)
    if m:
        return "arxiv:" + m.group(1)
    doi = (r.get("doi") or "").strip().lower()
    if doi:
        return "doi:" + doi.split("doi.org/")[-1]
    if "doi.org/" in url:
        return "doi:" + url.split("doi.org/")[-1].lower()
    return "url:" + dedupe.canonical_url(url)


def _search(mod: str, q: str, n: int, t: float):
    return getattr(importlib.import_module(mod), "search")(q, n, t)


DISPATCH = {
    "brave": lambda q, n, t: _search("brave", q, n, t),
    "marginalia": lambda q, n, t: _search("web_marginalia", q, n, t),
    "duckduckgo": lambda q, n, t: _search("web_ddg", q, n, t),
    "openalex": lambda q, n, t: _search("openalex", q, n, t),
    "arxiv": lambda q, n, t: _search("arxiv", q, n, t),
    "hackernews": lambda q, n, t: _search("hn", q, n, t),
    "stackexchange": lambda q, n, t: _search("stackexchange", q, n, t),
    "github": lambda q, n, t: _search("github", q, n, t),
    "reddit": lambda q, n, t: importlib.import_module("reddit").search(q, n, t),
    "europepmc": lambda q, n, t: _search("europepmc", q, n, t),          # biomed/clinical primary
    "wikipedia": lambda q, n, t: _search("wikipedia", q, n, t),          # orientation / humanities
    "crossref": lambda q, n, t: _search("crossref", q, n, t),            # DOI metadata / references
    "semanticscholar": lambda q, n, t: _search("semanticscholar", q, n, t),  # CS/ML citation graph
    "googlebooks": lambda q, n, t: _search("googlebooks", q, n, t),      # books / history / humanities
    "gutenberg": lambda q, n, t: _search("gutendex", q, n, t),           # public-domain full texts
    "youtube": lambda q, n, t: [{"index_of_origin": "youtube",
                                 "url": "https://www.youtube.com/watch?v=" + v, "title": ""}
                                for v in importlib.import_module("youtube").yt_search(q, n, t)],
}


def _cfg_classes() -> Dict[str, Dict[str, Any]]:
    with open(os.path.join(os.path.dirname(CH), "channels.json"), encoding="utf-8") as fh:
        return json.load(fh)["indexes"]


def retrieve(query: str, channels: List[str], limit: int, timeout: float):
    idx = _cfg_classes()
    per, recs = {}, []

    def one(ch):
        start = time.time()
        used = query
        try:
            out = DISPATCH[ch](query, limit, timeout) or []
            # 0-result relaxation: many free indexes AND their terms, so a long compound query returns
            # NOTHING (the audited AND-cliff). On a TRUE zero, retry with progressively fewer MOST-
            # SALIENT terms until non-empty — capped at 2 retries, and never when the query already
            # returned results (so it can't broaden a working query into noise).
            if not out and len(query.split()) > 3:
                for k in (3, 2):
                    relaxed = _http.keywordize(query, k)
                    if len(relaxed.split()) >= len(used.split()):
                        continue
                    used = relaxed
                    out = DISPATCH[ch](relaxed, limit, timeout) or []
                    if out:
                        break
            for r in out:
                r.setdefault("_channel", ch)
            return ch, out, time.time() - start, None, used
        except Exception as e:  # noqa: BLE001
            return ch, [], time.time() - start, "%s: %s" % (type(e).__name__, str(e)[:80]), query

    with ThreadPoolExecutor(max_workers=max(len(channels), 1)) as ex:
        for f in as_completed([ex.submit(one, c) for c in channels]):
            ch, out, dt, err, used = f.result()
            per[ch] = {"n": len(out), "latency_s": round(dt, 2), "error": err}
            if used != query:                      # surface that this channel needed relaxation
                per[ch]["relaxed_to"] = used
            recs += out
    for r in recs:
        meta = idx.get(r.get("index_of_origin") or r.get("_channel"), {})
        r["_class"] = r.get("channel_class") or meta.get("class", "?")
        r["_index_group"] = meta.get("index_group", r.get("_channel"))
    return recs, per


def _save_read(node: str, url: str, text: str, method: str, truncated: bool = False) -> str:
    d = os.path.join(node, "notes")
    os.makedirs(d, exist_ok=True)
    h = hashlib.sha1(url.encode()).hexdigest()[:10]
    path = os.path.join(d, h + ".md")
    trunc = " TRUNCATED at %d chars — re-read with a larger cap if a claim rests on the tail" % \
        MAX_READ_CHARS if truncated else ""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("<!-- %s (via %s)%s -->\n\n%s" % (url, method, trunc, text))
    return path


def _note_exists(node: str, url: str) -> bool:
    if not url:
        return False
    h = hashlib.sha1(url.encode()).hexdigest()[:10]
    return os.path.exists(os.path.join(node, "notes", h + ".md"))


def _existing_work_keys(node: str) -> set:
    """Work keys already in this node's sources.jsonl (for cross-round node-level dedup)."""
    keys = set()
    p = os.path.join(node, "sources.jsonl")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.strip():
                try:
                    keys.add(_work_key(json.loads(line)))
                except ValueError:
                    pass
    return keys


def _run_cfg(node: str) -> Dict[str, Any]:
    run = treestate._find_run(node)
    return (treestate._read_json(os.path.join(run, "run.json"), {}) or {}) if run else {}


def investigate(node: str, query: str = "", reads: int = 0, limit: int = 8,
                channels: List[str] = None, timeout: float = 30.0) -> dict:
    """ONE deepening round on a node. The worker calls this repeatedly (round 1 = the node
    question; later rounds = the top gap from reflection), so evidence ACCUMULATES across rounds
    (append to evidence.md, accumulate n_read, bump the rounds counter) — that is where depth
    comes from. Reads/round default to ~one scrutiny unit; the worker sequences the rounds."""
    st = treestate._read_json(os.path.join(node, "status.json"), {}) or {}
    cfg = _run_cfg(node)
    unit = float(cfg.get("unit", 4))
    query = query or st.get("question", "")
    query = _anchor(query, cfg.get("topic", ""))   # keep the leaf tied to the root subject
    round_no = int(st.get("rounds", 0)) + 1
    prev_read = int(st.get("n_read", 0) or 0)
    reads = reads or max(3, round(unit))           # ~one scrutiny unit per round, not the whole budget
    treestate.set_status(node, state="active")

    # router is only a DEFAULT; the worker may override channels after seeing round-1 evidence
    chans = channels or router.route(query, framing=st.get("question", ""), enabled_only=True)["channels"]
    treestate.log_decision(node, "investigate", "round %d channels=%s" % (round_no, ",".join(chans)),
                           "router category=%s (default; worker may override)" % router.classify(query))

    recs, per = retrieve(query, chans, limit, timeout)
    # dedupe at the WORK level (arXiv id / DOI / canonical url) so versions don't duplicate
    seen, uniq = set(), []
    for r in recs:
        wk = _work_key(r)
        if wk and wk not in seen:
            seen.add(wk); uniq.append(r)
    ranked = rankmod.rank(query, uniq)
    # don't spend read slots re-reading a source already read in a previous round
    sel = [r for r in rankmod.select_reads(ranked, reads) if not _note_exists(node, r.get("url", ""))]
    treestate.log_decision(node, "investigate",
                           "round %d: retrieved %d -> %d unique; reading %d new" % (
                               round_no, len(recs), len(uniq), len(sel)),
                           "per-channel: %s" % {k: v["n"] for k, v in per.items()})

    # read selected in full
    read_meta = []
    for r in sel:
        u = r.get("url", "")
        if not u.lower().startswith(("http://", "https://")):
            continue
        t0 = time.time()
        try:
            txt, method = readmod.read_url(u, timeout, MAX_READ_CHARS, False)
            truncated = len(txt) >= MAX_READ_CHARS      # hit the cap -> tail may be missing
            path = _save_read(node, u, txt, method, truncated)
            ok = len(txt.strip()) >= 1500
            r["_read_file"] = os.path.relpath(path, node)
            r["_read_ok"] = ok
            r["_truncated"] = truncated
            read_meta.append({"url": u, "chars": len(txt), "method": method, "ok": ok,
                              "truncated": truncated,
                              "t": round(time.time() - t0, 1), "title": r.get("title", "")})
        except Exception as e:  # noqa: BLE001
            read_meta.append({"url": u, "chars": 0, "method": "FAIL", "ok": False,
                              "err": type(e).__name__})

    # node-level dedup across rounds: add_sources only deduped the GLOBAL index, so repeated
    # rounds duplicated this node's sources.jsonl and corrupted independence math. Add only
    # work-keys this node hasn't seen yet.
    existing = _existing_work_keys(node)
    new_for_node = [r for r in ranked if _work_key(r) not in existing]
    treestate.add_sources(node, new_for_node)
    _write_evidence(node, query, ranked, sel, per, read_meta, round_no)
    this_ok = sum(1 for m in read_meta if m.get("ok"))
    treestate.set_status(node, state="investigated", n_sources=len(_existing_work_keys(node)),
                         n_read=prev_read + this_ok, rounds=round_no)
    return {"node": node, "round": round_no, "query": query, "channels": chans, "unique": len(uniq),
            "reads_ok": this_ok, "reads_total": prev_read + this_ok, "per_channel": per}


def _write_evidence(node, query, ranked, sel, per, read_meta, round_no=1):
    """Append a `## Round N` section to evidence.md so the pack ACCUMULATES across deepening
    rounds (it used to clobber, erasing prior rounds)."""
    path = os.path.join(node, "evidence.md")
    first = round_no <= 1 or not os.path.exists(path)
    lines = []
    if first:
        st = treestate._read_json(os.path.join(node, "status.json"), {}) or {}
        lines += ["# Evidence pack", "", "**Node question:** %s" % (st.get("question", "") or query), ""]
    lines += ["## Round %d — query: %s" % (round_no, query), "",
              "**Channels:** " + ", ".join("%s(%d)" % (k, v["n"]) for k, v in per.items()), "",
              "### Read in full this round (%d)" % len(read_meta), ""]
    rf = {m["url"]: m for m in read_meta}
    for r in sel:
        m = rf.get(r.get("url", ""), {})
        flag = "ok" if m.get("ok") else "MISS(%s)" % m.get("method", "?")
        if m.get("truncated"):
            flag += " ⚠TRUNCATED"
        excerpt = ""
        if r.get("_read_file"):
            try:
                body = open(os.path.join(node, r["_read_file"]), encoding="utf-8").read()
                excerpt = " ".join(body.split()[:80])
            except OSError:
                pass
        lines += ["#### [%s] %s" % (r.get("_class", "?"), (r.get("title") or r.get("url"))[:90]),
                  "- url: %s" % r.get("url", ""),
                  "- score=%.3f rel=%.2f authority=%.1f  read=%s (%d ch)" % (
                      r.get("score", 0), r.get("_relnorm", 0), r.get("_authority", 0),
                      flag, m.get("chars", 0)),
                  "", "> " + (excerpt[:600] or "_(no excerpt)_"), ""]
    lines += ["### Other ranked sources this round (not read)", ""]
    for r in ranked:
        if r.get("_read_file") or _note_exists(node, r.get("url", "")):
            continue
        lines.append("- [%.3f][%s] %s — %s" % (r.get("score", 0), r.get("_class", "?"),
                                               (r.get("title") or "")[:70], r.get("url", "")))
    with open(path, "w" if first else "a", encoding="utf-8") as fh:
        fh.write(("" if first else "\n") + "\n".join(lines) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deep Aletheia leaf investigation.")
    ap.add_argument("--node", required=True)
    ap.add_argument("--query", default="")
    ap.add_argument("--reads", type=int, default=0)
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--channels", default="")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args(argv)
    chans = [c.strip() for c in args.channels.split(",") if c.strip()] or None
    res = investigate(args.node, args.query, args.reads, args.limit, chans, args.timeout)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
