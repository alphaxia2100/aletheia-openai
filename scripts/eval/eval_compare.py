#!/usr/bin/env python3
"""Compare research-survey runs through the canonical evaluator-v2 scorer.

The self-audit's verdict was that "surveyor > the old skills" must be MEASURED, not asserted, and
that the retired `aletheia`/`deep-aletheia` runs are kept as baselines. This scores any run dir
(auto-detecting the surveyor flat layout OR the deep-aletheia tree layout) on the metrics the audit
said matter, so improvement (or regression) across generations is visible on one table.

This command no longer reimplements citation accuracy or source quality.  It calls ``score_run``,
which delegates citation scoring to the skill's hardened scorer and requires a valid final-answer
claim-scope audit.  Unmeasured dimensions remain null instead of being replaced with formatting or
authority-domain proxies.

Usage:
  eval_compare.py --runs "surveyor-std=runs/survey/…,da-0.2=runs/deep/…,da-0.1=runs/deep/…"
  eval_compare.py --topics scripts/eval/topics.jsonl        # list the fixed eval topics
"""
from __future__ import annotations

import argparse
import json
import os
import score_run


def _jsonl(p):
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def score(run: str) -> dict:
    return score_run.score(run, require_scope=True)


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
    cols = ["citation_accuracy", "citation_entailment_precision", "scope_gate_passed",
            "source_quality", "independence", "sources", "brief_word_count"]
    w = max(len(l) for l, _ in scored) + 2
    print("%-*s %s" % (w, "run", "  ".join("%-16s" % c for c in cols)))
    for label, s in scored:
        print("%-*s %s" % (w, label, "  ".join("%-16s" % str(s.get(c)) for c in cols)))
    print("\n(None is an explicit unmeasured/failed-gate value, never a pass.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
