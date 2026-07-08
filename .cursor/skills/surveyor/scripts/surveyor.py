#!/usr/bin/env python3
"""Surveyor — a thoroughness-scaled research surveyor (single-agent-first).

Rebuilt from the deep-aletheia self-audit (see docs/surveyor-design.md). The evidence says:
default to a SINGLE-AGENT loop, fan out to parallel workers ONLY for breadth, and scale effort to
COMPLEXITY (a thoroughness dial) rather than a uniform per-node budget. This driver owns the
deterministic state in a FLAT run dir; the calling agent (or, at `deep`, breadth subagents) supplies
the judgment (angles, reflection, adversary, synthesis, entailment). It reuses only the low-level
channel/independence utilities — none of the retired tree/budget/gate machinery.

Subcommands:
  surveyor.py plan   --topic "..." --thoroughness auto|quick|standard|deep|exhaustive [--slug s]
  surveyor.py gather --run RUN [--query Q | --queries "a||b"] [--angle NAME] [--reads K] [--channels c,c]
  surveyor.py deepen --run RUN [--angle NAME] [--learning "..."]... [--followup "..."]...   # exit 3 = STOP
  surveyor.py independence --run RUN
  surveyor.py verify --run RUN --claims claims.jsonl [--out verify.jsonl]   # lexical prefilter only
  surveyor.py score  --run RUN
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import json
import math
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.realpath(__file__))
CH = os.path.abspath(os.path.join(HERE, "..", "..", "channel-retrieval", "scripts"))
PROV = os.path.abspath(os.path.join(HERE, "..", "..", "provenance-audit", "scripts"))
for p in (CH, PROV):
    sys.path.insert(0, p)
import rerank  # noqa: E402  (tokenize + TF-IDF relevance)
import read as readmod  # noqa: E402  (full-page/PDF reads, browser escalation)
import dedupe  # noqa: E402  (canonical_url / registrable_domain / voice_key)

# ---------------------------------------------------------------- thoroughness
# Effort scales to complexity (the fix for the retired uniform-budget model). auto is resolved by
# the AGENT during SCOPE (breadth x contestedness) — the driver defaults it to standard.
TIERS: Dict[str, Dict[str, Any]] = {
    "quick":      {"angles": 2, "channels": 2, "reads": 5, "rounds": 0, "fanout": False, "verify": "light", "adversary": False},
    "standard":   {"angles": 3, "channels": 3, "reads": 6, "rounds": 2, "fanout": False, "verify": "full",  "adversary": True},
    "deep":       {"angles": 4, "channels": 4, "reads": 6, "rounds": 2, "fanout": True,  "verify": "full",  "adversary": True},
    "exhaustive": {"angles": 6, "channels": 5, "reads": 8, "rounds": 3, "fanout": True,  "verify": "multi", "adversary": True},
}

# channel roles so every survey covers the 3 classes (independent web / primary / un-laundered).
WEB = ["brave", "marginalia", "duckduckgo"]
PRIMARY = ["openalex", "arxiv", "github", "stackexchange"]
COMMUNITY = ["reddit", "hackernews"]
COLOR = ["youtube"]
DISPATCH = {
    "brave": ("brave", "search"), "marginalia": ("web_marginalia", "search"),
    "duckduckgo": ("web_ddg", "search"), "openalex": ("openalex", "search"),
    "arxiv": ("arxiv", "search"), "hackernews": ("hn", "search"),
    "stackexchange": ("stackexchange", "search"), "github": ("github", "search"),
    "reddit": ("reddit", "search"),
}
# arXiv is CS/physics only — drop it on clearly biomed/clinical topics (sound heuristic kept from the audit).
BIOMED = ["clinical", "fasting", "diet", "caloric", "calorie", "metabolic", "insulin", "glucose",
          "obesity", "weight loss", "patient", "disease", "drug", "dose", "nutrition", "cancer",
          "cardiovascular", "cholesterol", "therapy", "trial", "medicine", "medical", "hormone", "vitamin"]

AUTH_HIGH = {"arxiv.org", "doi.org", "openalex.org", "semanticscholar.org", "nature.com", "science.org",
             "acm.org", "ieee.org", "ncbi.nlm.nih.gov", "nih.gov", "pnas.org", "cell.com", "plos.org",
             "biorxiv.org", "medrxiv.org", "jstor.org", "springer.com", "sciencedirect.com", "europepmc.org"}
AUTH_MED = {"github.com", "gitlab.com", "python.org", "mozilla.org", "w3.org", "ietf.org",
            "anthropic.com", "openai.com", "stanford.edu", "mit.edu"}
FARM = {"medium.com", "dev.to", "geeksforgeeks.org", "w3schools.com", "tutorialspoint.com",
        "simplilearn.com", "guru99.com", "quora.com", "linkedin.com", "hackernoon.com"}
_ARXIV = re.compile(r"arxiv\.org/(?:abs|html|pdf)/([0-9]{4}\.[0-9]{4,5})", re.I)


# ---------------------------------------------------------------- helpers
def _now() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(s: str, n: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:n] or "survey"


def _read_json(p: str, d: Any = None) -> Any:
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return d


def _jsonl(p: str) -> List[Dict[str, Any]]:
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def _append_jsonl(p: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj) + "\n")


def resolve_tier(name: str) -> Dict[str, Any]:
    return dict(TIERS.get(name if name in TIERS else "standard", TIERS["standard"]))


def _channels_cfg() -> Dict[str, Any]:
    return _read_json(os.path.join(os.path.dirname(CH), "channels.json"), {}) or {}


def _class_of(ch: str, cfg: Dict[str, Any]) -> str:
    return (cfg.get("indexes", {}).get(ch, {}) or {}).get("class", "lead_gen")


def pick_channels(topic: str, n: int) -> List[str]:
    """Cover the 3 roles, capped at n, using only enabled+runnable channels."""
    cfg = _channels_cfg()
    enabled = set(cfg.get("enabled", [])) | {"duckduckgo", "marginalia"}  # keyless web always usable
    ok = lambda lst: [c for c in lst if c in DISPATCH and c in enabled]
    web, primary, comm = ok(WEB), ok(PRIMARY), ok(COMMUNITY)
    if sum(1 for kw in BIOMED if kw in topic.lower()) >= 2:
        primary = [c for c in primary if c != "arxiv"]  # arXiv is off-domain for biomed
    chosen: List[str] = []
    for role in (primary, web, comm):          # guarantee one of each role first
        if role:
            chosen.append(role[0])
    for role in (primary, web, comm):          # then widen by role until n
        for c in role:
            if c not in chosen and len(chosen) < n:
                chosen.append(c)
    return chosen[:max(n, 1)]


def authority(url: str) -> float:
    dom = dedupe.registrable_domain(url or "")
    if not dom:
        return 0.5
    if dom in AUTH_HIGH or dom.endswith((".edu", ".gov", ".ac.uk")):
        return 1.0
    if dom in AUTH_MED:
        return 0.8
    if dom in FARM:
        return 0.2
    return 0.5


def work_key(r: Dict[str, Any]) -> str:
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


# ---------------------------------------------------------------- retrieval + ranking
def _search(ch: str, q: str, n: int, t: float):
    mod, fn = DISPATCH[ch]
    out = getattr(importlib.import_module(mod), fn)(q, n, t) or []
    for r in out:
        r.setdefault("_channel", ch)
    return out


def retrieve(query: str, channels: List[str], limit: int, timeout: float):
    cfg = _channels_cfg()
    per, recs = {}, []

    def one(ch):
        start = time.time()
        try:
            out = _search(ch, query, limit, timeout)
            return ch, out, time.time() - start, None
        except Exception as e:  # noqa: BLE001
            return ch, [], time.time() - start, "%s: %s" % (type(e).__name__, str(e)[:80])

    with ThreadPoolExecutor(max_workers=max(len(channels), 1)) as ex:
        for f in as_completed([ex.submit(one, c) for c in channels]):
            ch, out, el, err = f.result()
            per[ch] = {"n": len(out), "latency_s": round(el, 2), "error": err}
            recs += out
    for r in recs:
        r["_class"] = r.get("channel_class") or _class_of(r.get("_channel", ""), cfg)
    return recs, per


def rank(query: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = rerank.rerank(query, records)               # relevance (TF-IDF cosine)
    maxrel = max((r.get("relevance", 0) for r in ranked), default=0) or 1.0
    out = []
    CLASS_W = {"evidence": 1.0, "lead_gen": 0.6, "color": 0.3}
    for r in ranked:
        rel = r.get("relevance", 0) / maxrel
        auth = authority(r.get("url", ""))
        cite = min(math.log1p(r.get("cited_by_count", 0) or 0) / math.log1p(1000), 1.0)
        rel_base = 0.2 + 0.8 * rel                         # relevance GATES quality (multiplicative)
        quality = 0.5 + 0.5 * auth + 0.2 * cite + 0.2 * CLASS_W.get(r.get("_class"), 0.5)
        rr = dict(r)
        rr["_authority"] = auth
        rr["score"] = round(rel_base * quality * (1.05 if r.get("primary") else 1.0), 4)
        out.append(rr)
    return sorted(out, key=lambda r: r["score"], reverse=True)


def select_reads(ranked: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    """Class-budgeted so primaries are read, not crowded out by high-lexical blogs."""
    if k <= 0:
        return []
    ev = [r for r in ranked if r.get("_class") == "evidence"]
    pick, seen = [], set()

    def take(pool, n):
        for r in pool:
            u = r.get("url", "")
            if n <= 0:
                break
            if u and u not in seen:
                seen.add(u); pick.append(r); n -= 1

    take(ev, max(1, math.ceil(0.6 * k)))
    for r in ranked:                                       # fill the rest by score
        u = r.get("url", "")
        if len(pick) >= k:
            break
        if u and u not in seen:
            seen.add(u); pick.append(r)
    return sorted(pick, key=lambda r: r["score"], reverse=True)[:k]


def _note_path(scope: str, url: str) -> str:
    return os.path.join(scope, "notes", hashlib.sha1(url.encode()).hexdigest()[:10] + ".md")


# ---------------------------------------------------------------- subcommands
def cmd_plan(a) -> int:
    params = resolve_tier(a.thoroughness)
    ts = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    run = os.path.join(a.base, "%s-%s" % (ts, _slug(a.slug or a.topic)))
    os.makedirs(os.path.join(run, "notes"), exist_ok=True)
    channels = pick_channels(a.topic, params["channels"])
    cfg = {"topic": a.topic, "created": _now(), "version": "surveyor 0.1.0",
           "thoroughness": a.thoroughness, "resolved_tier": a.thoroughness if a.thoroughness in TIERS else "standard",
           "params": params, "channels": channels}
    with open(os.path.join(run, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    with open(os.path.join(run, "angles.md"), "w", encoding="utf-8") as fh:
        fh.write("# Angles — %s\n\n_(write %d competing angles incl. ONE disconfirming; commit to none)_\n"
                 % (a.topic, params["angles"]))
    note = ("auto: the agent picks the tier in SCOPE by breadth x contestedness, then re-runs plan "
            "with that tier; defaulting to standard." if a.thoroughness == "auto" else "")
    print(json.dumps({"run": run, "tier": cfg["resolved_tier"], "params": params,
                      "channels": channels, "angles_to_write": params["angles"], "note": note}, indent=2))
    return 0


def cmd_gather(a) -> int:
    cfg = _read_json(os.path.join(a.run, "run.json"), {}) or {}
    params = cfg.get("params", TIERS["standard"])
    scope = os.path.join(a.run, "angles", _slug(a.angle, 24)) if a.angle else a.run
    os.makedirs(os.path.join(scope, "notes"), exist_ok=True)
    queries = [q for q in (a.queries.split("||") if a.queries else [a.query or cfg.get("topic", "")]) if q.strip()]
    channels = [c.strip() for c in a.channels.split(",") if c.strip()] or cfg.get("channels") \
        or pick_channels(cfg.get("topic", ""), params["channels"])
    reads = a.reads or params["reads"]
    timeout = a.timeout

    st = _read_json(os.path.join(scope, "state.json"), {}) or {}
    round_no = int(st.get("rounds", 0)) + 1
    existing = {work_key(r) for r in _jsonl(os.path.join(scope, "sources.jsonl"))}

    recs = []
    per_all = {}
    for q in queries:
        r, per = retrieve(q, channels, max(reads + 2, 8), timeout)
        recs += r
        for k, v in per.items():
            per_all[k] = v
    seen, uniq = set(), []
    for r in recs:
        wk = work_key(r)
        if wk and wk not in seen:
            seen.add(wk); uniq.append(r)
    ranked = rank(queries[0], uniq)
    sel = [r for r in select_reads(ranked, reads) if not os.path.exists(_note_path(scope, r.get("url", "")))]

    read_ok = 0
    ev_lines = ["", "## Round %d — %s" % (round_no, " | ".join(queries)),
                "channels: " + ", ".join("%s(%d)" % (k, v["n"]) for k, v in per_all.items()), ""]
    for r in sel:
        u = r.get("url", "")
        if not u.lower().startswith(("http://", "https://")):
            continue
        try:
            txt, method = readmod.read_url(u, timeout, 40000, False)
            with open(_note_path(scope, u), "w", encoding="utf-8") as fh:
                fh.write("<!-- %s (via %s) -->\n\n%s" % (u, method, txt))
            ok = len(txt.strip()) >= 1500
            read_ok += 1 if ok else 0
            r["_read"] = ok
            ev_lines.append("- [%s] %s (%s, %d ch) %s" % (r.get("_class", "?"),
                            (r.get("title") or u)[:80], method, len(txt), u))
        except Exception as e:  # noqa: BLE001
            ev_lines.append("- FAIL(%s) %s" % (type(e).__name__, u))

    # append new work-keys to this scope AND the run-global index (dedup) for independence/score
    for r in ranked:
        if work_key(r) not in existing:
            _append_jsonl(os.path.join(scope, "sources.jsonl"), r)
            if scope != a.run:
                _append_jsonl(os.path.join(a.run, "sources.jsonl"), r)
            existing.add(work_key(r))
    with open(os.path.join(scope, "evidence.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(ev_lines) + "\n")
    st["rounds"] = round_no
    with open(os.path.join(scope, "state.json"), "w", encoding="utf-8") as fh:
        json.dump(st, fh)
    print(json.dumps({"scope": scope, "round": round_no, "queries": queries, "channels": channels,
                      "retrieved": len(recs), "unique": len(uniq), "read_ok": read_ok,
                      "per_channel": {k: v["n"] for k, v in per_all.items()},
                      "evidence": os.path.join(scope, "evidence.md")}, indent=2))
    return 0


def cmd_deepen(a) -> int:
    """Record learnings + novel follow-ups; print the next round's queries. Exit 3 = STOP
    (converged: no novel follow-ups, or the tier's round cap reached)."""
    cfg = _read_json(os.path.join(a.run, "run.json"), {}) or {}
    cap = int(cfg.get("params", {}).get("rounds", 2))
    scope = os.path.join(a.run, "angles", _slug(a.angle, 24)) if a.angle else a.run
    sp = os.path.join(scope, "deepen.json")
    dstate = _read_json(sp, {"visited": [], "pending": [], "learnings": [], "level": 0}) or {}
    norm = lambda q: re.sub(r"[^a-z0-9 ]", "", q.lower()).strip()
    for l in (a.learning or []):
        if l.strip():
            dstate["learnings"].append(l.strip())
    seen = set(dstate["visited"]) | {norm(p) for p in dstate["pending"]}
    for f in (a.followup or []):
        if norm(f) and norm(f) not in seen:
            dstate["pending"].append(f.strip()); seen.add(norm(f))
    stop = None
    if dstate["level"] >= cap:
        stop = "round cap (%d) reached" % cap
    elif not dstate["pending"]:
        stop = "converged: no novel follow-ups"
    if stop:
        with open(sp, "w", encoding="utf-8") as fh:
            json.dump(dstate, fh, indent=2)
        sys.stderr.write("STOP: %s\n" % stop)
        return 3
    dstate["level"] += 1
    nxt = dstate["pending"][:2]                            # narrow as we drill
    dstate["pending"] = dstate["pending"][2:]
    dstate["visited"] += [norm(q) for q in nxt]
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(dstate, fh, indent=2)
    print("||".join(nxt))
    return 0


def independence(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    from collections import Counter
    if not records:
        return {"n": 0, "voices": 0, "echo_ratio": 0, "domains": 0, "top_domain_share": 0}
    voices = {dedupe.voice_key(r) for r in records}
    doms = Counter(dedupe.registrable_domain(r.get("url", "")) for r in records if r.get("url"))
    return {"n": len(records), "voices": len(voices),
            "echo_ratio": round(1 - len(voices) / len(records), 3), "domains": len(doms),
            "top_domain_share": round(doms.most_common(1)[0][1] / sum(doms.values()), 3) if doms else 0}


def cmd_independence(a) -> int:
    recs = _jsonl(os.path.join(a.run, "sources.jsonl"))
    rep = independence(recs)
    if rep["echo_ratio"] >= 0.4 or rep["top_domain_share"] >= 0.4:
        rep["warning"] = "high echo/concentration — don't treat convergence as truth; trace to origins."
    with open(os.path.join(a.run, "independence.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2)
    print(json.dumps(rep, indent=2))
    return 0


def _source_text(url: str, run: str, timeout: float) -> str:
    for scope in [run] + [os.path.join(run, "angles", d) for d in
                          (os.listdir(os.path.join(run, "angles")) if os.path.isdir(os.path.join(run, "angles")) else [])]:
        p = _note_path(scope, url)
        if os.path.exists(p):
            try:
                return open(p, encoding="utf-8").read()
            except OSError:
                pass
    try:
        return readmod.read_url(url, timeout, 40000, False)[0]
    except Exception:  # noqa: BLE001
        return ""


def cmd_verify(a) -> int:
    """Deterministic layer ONLY: relevance (broken/off_topic/relevant). NEVER certifies support —
    lexical overlap can't see polarity/magnitude. The agent/subagent Fact-Checks each `relevant`
    claim (entailment) and writes the final supported/contradicted/unsupported into verify.jsonl."""
    claims = _jsonl(a.claims)
    out = a.out or os.path.join(a.run, "verify.jsonl")
    results = []
    for c in claims:
        urls = c.get("urls") or ([c["url"]] if c.get("url") else [])
        ctoks = set(rerank.tokenize(c.get("claim", "")))
        best = {"overlap": 0.0, "url": urls[0] if urls else "", "link_works": False, "snippet": ""}
        for u in urls:
            txt = _source_text(u, a.run, a.timeout)
            if len(txt.strip()) < 200:
                continue
            ov = len(ctoks & set(rerank.tokenize(txt))) / max(len(ctoks), 1)
            if not best["link_works"] or ov > best["overlap"]:
                snip = max((s for s in re.split(r"(?<=[.!?])\s+|\n", txt) if len(s) > 20),
                           key=lambda s: len(ctoks & set(rerank.tokenize(s))) / max(len(ctoks), 1), default="")
                best = {"overlap": round(ov, 3), "url": u, "link_works": True, "snippet": snip[:300]}
        verdict = ("broken" if not best["link_works"] else "relevant" if best["overlap"] >= 0.30 else "off_topic")
        results.append({"claim": c.get("claim", ""), "verdict": verdict, "overlap": best["overlap"],
                        "url": best["url"], "link_works": best["link_works"], "snippet": best["snippet"],
                        "needs_llm_check": True})
    with open(out, "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")
    from collections import Counter
    counts = Counter(r["verdict"] for r in results)
    print(json.dumps({"n": len(results), "counts": dict(counts), "out": out,
                      "note": "relevance only; agent must Fact-Check each 'relevant' -> supported/contradicted/unsupported"}, indent=2))
    return 0


def cmd_score(a) -> int:
    cfg = _read_json(os.path.join(a.run, "run.json"), {}) or {}
    idx = _jsonl(os.path.join(a.run, "sources.jsonl"))
    indep = independence(idx)
    quality = round(sum(1 for r in idx if r.get("_class") == "evidence" and authority(r.get("url", "")) >= 0.8)
                    / len(idx), 3) if idx else 0
    ver = _jsonl(os.path.join(a.run, "verify.jsonl"))
    from collections import Counter
    vc = Counter(r.get("verdict") for r in ver)
    llm_done = vc["supported"] + vc["contradicted"] + vc["unsupported"]
    cit_acc = round(vc["supported"] / len(ver), 3) if (ver and llm_done) else None
    angles_dir = os.path.join(a.run, "angles")
    angles = [d for d in os.listdir(angles_dir)] if os.path.isdir(angles_dir) else []
    reads = len([p for _d, _s, fs in os.walk(a.run) for p in fs if _d.endswith("notes")])
    brief = os.path.join(a.run, "brief.md")
    bt = open(brief, encoding="utf-8").read().lower() if os.path.exists(brief) else ""
    print(json.dumps({
        "topic": cfg.get("topic"), "version": cfg.get("version"), "tier": cfg.get("resolved_tier"),
        "citation_accuracy": cit_acc,
        "verdicts": {"supported": vc["supported"], "contradicted": vc["contradicted"],
                     "unsupported": vc["unsupported"], "awaiting_llm_check": vc["relevant"]},
        "source_quality": quality, "sources": len(idx),
        "independence": round(1 - indep["echo_ratio"], 3), "echo_ratio": indep["echo_ratio"],
        "unique_voices": indep["voices"], "reads": reads, "angles": len(angles),
        "brief_sections": {s: (s in bt) for s in ("agreement", "disagreement", "unverified")},
    }, indent=2))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Surveyor — thoroughness-scaled research surveyor.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("--topic", required=True)
    p.add_argument("--thoroughness", default="auto"); p.add_argument("--slug", default="")
    p.add_argument("--base", default="runs/survey"); p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("gather"); p.add_argument("--run", required=True)
    p.add_argument("--query", default=""); p.add_argument("--queries", default="")
    p.add_argument("--angle", default=""); p.add_argument("--reads", type=int, default=0)
    p.add_argument("--channels", default=""); p.add_argument("--timeout", type=float, default=40.0)
    p.set_defaults(fn=cmd_gather)
    p = sub.add_parser("deepen"); p.add_argument("--run", required=True); p.add_argument("--angle", default="")
    p.add_argument("--learning", action="append"); p.add_argument("--followup", action="append")
    p.set_defaults(fn=cmd_deepen)
    p = sub.add_parser("independence"); p.add_argument("--run", required=True); p.set_defaults(fn=cmd_independence)
    p = sub.add_parser("verify"); p.add_argument("--run", required=True); p.add_argument("--claims", required=True)
    p.add_argument("--out", default=""); p.add_argument("--timeout", type=float, default=40.0); p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("score"); p.add_argument("--run", required=True); p.set_defaults(fn=cmd_score)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
