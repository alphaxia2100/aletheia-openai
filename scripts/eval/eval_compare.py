#!/usr/bin/env python3
"""Compare research-survey runs on a shared rubric — surveyor vs the retired baselines.

The self-audit's verdict was that "surveyor > the old skills" must be MEASURED, not asserted, and
that the retired `aletheia`/`deep-aletheia` runs are kept as baselines. This scores any run dir
(auto-detecting the surveyor flat layout OR the deep-aletheia tree layout) on the metrics the audit
said matter, so improvement (or regression) across generations is visible on one table.

Shared metrics (format-agnostic):
  citation_accuracy  supported / total     (from verify.jsonl's final LLM verdicts; None if not run)
  source_quality     share of sources that are evidence-class AND high-authority
  independence       1 - echo_ratio        (voice_key over the run's source index)
  sources / reads    corpus size + full reads
  brief_complete     Agreement/Disagreement/Unverified all present

Usage:
  eval_compare.py --runs "surveyor-std=runs/survey/…,da-0.2=runs/deep/…,da-0.1=runs/deep/…"
  eval_compare.py --topics scripts/eval/topics.jsonl        # list the fixed eval topics
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, ".cursor", "skills", "surveyor", "scripts"))
sys.path.insert(0, os.path.join(REPO, ".cursor", "skills", "provenance-audit", "scripts"))
import surveyor  # noqa: E402  (authority + independence — the sound utilities)
import dedupe  # noqa: E402


def _jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def _index_path(run):
    for p in (os.path.join(run, "index", "sources.jsonl"), os.path.join(run, "sources.jsonl")):
        if os.path.exists(p):
            return p
    return ""


def score(run: str) -> dict:
    idx = _jsonl(_index_path(run))
    indep = surveyor.independence(idx)
    quality = round(sum(1 for r in idx
                        if (r.get("_class") or r.get("channel_class")) == "evidence"
                        and surveyor.authority(r.get("url", "")) >= 0.8) / len(idx), 3) if idx else 0.0
    ver = _jsonl(os.path.join(run, "verify.jsonl"))
    vc = Counter(r.get("verdict") for r in ver)
    llm_done = vc["supported"] + vc["contradicted"] + vc["unsupported"]
    cit = round(vc["supported"] / len(ver), 3) if (ver and llm_done) else None
    reads = sum(len(fs) for d, _s, fs in os.walk(run) if d.endswith("notes"))
    bt = ""
    bp = os.path.join(run, "brief.md")
    if os.path.exists(bp):
        bt = open(bp, encoding="utf-8").read().lower()
    brief_complete = all(s in bt for s in ("agreement", "disagreement", "unverified"))
    cfg = json.load(open(os.path.join(run, "run.json"), encoding="utf-8")) if os.path.exists(os.path.join(run, "run.json")) else {}
    return {"version": cfg.get("version", "?"), "citation_accuracy": cit,
            "source_quality": quality, "independence": round(1 - indep["echo_ratio"], 3),
            "sources": len(idx), "reads": reads, "voices": indep["voices"],
            "brief_complete": brief_complete}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compare survey runs on a shared rubric.")
    ap.add_argument("--runs", default="", help='label=dir,label=dir')
    ap.add_argument("--topics", default="", help="print the fixed eval topic set")
    args = ap.parse_args(argv)
    if args.topics:
        for t in _jsonl(args.topics):
            print("- [%s] %s" % (t.get("domain", "?"), t.get("topic", "")))
        return 0
    if not args.runs:
        ap.error("provide --runs or --topics")
    pairs = [kv.split("=", 1) for kv in args.runs.split(",") if "=" in kv]
    scored = [(label, score(d)) for label, d in pairs]
    cols = ["citation_accuracy", "source_quality", "independence", "sources", "reads", "voices", "brief_complete"]
    w = max(len(l) for l, _ in scored) + 2
    print("%-*s %s" % (w, "run", "  ".join("%-16s" % c for c in cols)))
    for label, s in scored:
        print("%-*s %s" % (w, label, "  ".join("%-16s" % str(s.get(c)) for c in cols)))
    print("\n(citation_accuracy = None means the verify gate never completed — a real gap, not a pass.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
