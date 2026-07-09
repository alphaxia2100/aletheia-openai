#!/usr/bin/env python3
"""Aletheia eval — the trustworthy-measurement core (deterministic, testable, stdlib only).

The eval loop is: for each held-out TOPIC, generate a brief from each VERSION (baseline run from its
git TAG), then a DIFFERENT-model judge does a BLIND, POSITION-RANDOMIZED, multi-trial pairwise
comparison; objective grounded sub-metrics (citation F1@K, independence, decisive-source-hit) are
computed alongside. This module turns those raw verdicts into an HONEST answer to two questions:

  1. Did the candidate actually beat the baseline?  -> win-rate + Wilson 95% CI (excludes 0.5 or not)
  2. Can we TRUST the automated judge at all?        -> agreement + Cohen's kappa vs the human anchor set

Automated LLM-judge is the engine (it scales to a self-improving loop); the human anchor is used ONCE
to CALIBRATE the judge. A candidate is only declared better when BOTH the CI clears 0.5 AND the judge
is calibrated (kappa >= TRUST_KAPPA on the anchor set) — otherwise the honest verdict is "inconclusive:
get more anchor labels / topics." This is the guard against reward-hacking an unvalidated judge.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from typing import Any, Dict, List, Optional

TRUST_KAPPA = 0.6        # below this the automated judge is not trusted to drive improvement
CATS = ("candidate", "baseline", "tie")


def _wilson(wins: int, n: int, z: float = 1.96) -> Dict[str, float]:
    """Wilson score interval for a proportion — honest CI at tiny N (unlike normal approx)."""
    if n == 0:
        return {"p": 0.0, "lo": 0.0, "hi": 1.0}
    p = wins / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return {"p": round(p, 3), "lo": round(max(0.0, centre - half), 3), "hi": round(min(1.0, centre + half), 3)}


def _majority(verdicts: List[str]) -> str:
    """Per-topic majority across trials; a tie among trials (or literal 'tie' plurality) -> 'tie'."""
    if not verdicts:
        return "tie"
    c = Counter(verdicts)
    top = c.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return "tie"
    return top[0][0]


def _consistency(verdicts: List[str]) -> float:
    """Fraction of trials agreeing with the topic's majority — the judge's self-consistency."""
    if not verdicts:
        return 0.0
    m = _majority(verdicts)
    return round(sum(1 for v in verdicts if v == m) / len(verdicts), 3)


def _cohen_kappa(a: List[str], b: List[str]) -> Optional[float]:
    """Cohen's kappa between two raters over paired categorical labels (judge vs human)."""
    pairs = [(x, y) for x, y in zip(a, b) if x and y]
    n = len(pairs)
    if n == 0:
        return None
    po = sum(1 for x, y in pairs if x == y) / n
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    pe = sum((ca.get(k, 0) / n) * (cb.get(k, 0) / n) for k in set(ca) | set(cb))
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else 0.0
    return round((po - pe) / (1 - pe), 3)


def summarize(results: Dict[str, Any]) -> Dict[str, Any]:
    """results: {pairwise:[{topic,winner in CATS}], objective:{candidate:{topic:{metric:val}},baseline:{...}},
    human:[{topic,winner}] (optional)}. winner is always in generator-space (candidate/baseline/tie),
    i.e. the harness has ALREADY de-randomized the shown order — this module never sees position."""
    pw = results.get("pairwise", [])
    by_topic: Dict[str, List[str]] = {}
    for r in pw:
        by_topic.setdefault(r["topic"], []).append(r.get("winner", "tie"))
    topic_major = {t: _majority(v) for t, v in by_topic.items()}
    topic_consistency = {t: _consistency(v) for t, v in by_topic.items()}

    # win-rate over DECISIVE topics (ties excluded from the rate but reported)
    wins = sum(1 for w in topic_major.values() if w == "candidate")
    losses = sum(1 for w in topic_major.values() if w == "baseline")
    ties = sum(1 for w in topic_major.values() if w == "tie")
    decisive = wins + losses
    ci = _wilson(wins, decisive)

    # objective sub-metric deltas (candidate - baseline), averaged over topics present in both
    obj = results.get("objective", {})
    cand_o, base_o = obj.get("candidate", {}), obj.get("baseline", {})
    metric_keys = set()
    for d in list(cand_o.values()) + list(base_o.values()):
        metric_keys |= {k for k, v in (d or {}).items() if isinstance(v, (int, float))}
    obj_delta = {}
    for k in sorted(metric_keys):
        deltas = [cand_o[t][k] - base_o[t][k] for t in cand_o
                  if t in base_o and k in (cand_o[t] or {}) and k in (base_o[t] or {})]
        if deltas:
            obj_delta[k] = round(sum(deltas) / len(deltas), 3)

    # judge calibration vs the human anchor set (the trust gate)
    human = {h["topic"]: h["winner"] for h in results.get("human", [])}
    kappa = agree = n_anchor = None
    if human:
        common = [t for t in human if t in topic_major]
        n_anchor = len(common)
        if common:
            j = [topic_major[t] for t in common]
            h = [human[t] for t in common]
            agree = round(sum(1 for x, y in zip(j, h) if x == y) / len(common), 3)
            kappa = _cohen_kappa(j, h)
    judge_trusted = (kappa is not None and kappa >= TRUST_KAPPA)

    # verdict: candidate better ONLY if the CI clears 0.5 AND the judge is calibrated
    if decisive == 0:
        verdict = "inconclusive: no decisive topics (all ties) — need harder/more topics"
    elif human and not judge_trusted:
        verdict = ("inconclusive: JUDGE NOT TRUSTED (kappa %s < %.2f on n=%s anchors) — calibrate the "
                   "judge before believing the win-rate" % (kappa, TRUST_KAPPA, n_anchor))
    elif not human:
        verdict = ("provisional: win-rate p=%.2f [%.2f,%.2f] but judge UNCALIBRATED (no human anchor) "
                   "— label the anchor set to trust it" % (ci["p"], ci["lo"], ci["hi"]))
    elif ci["lo"] > 0.5:
        verdict = "candidate BETTER (CI clears 0.5, judge calibrated)"
    elif ci["hi"] < 0.5:
        verdict = "candidate WORSE (CI below 0.5, judge calibrated)"
    else:
        verdict = "inconclusive: CI spans 0.5 (need more topics for power)"

    return {
        "n_topics": len(topic_major), "wins": wins, "losses": losses, "ties": ties,
        "win_rate_over_decisive": ci, "per_topic": topic_major,
        "judge_self_consistency": topic_consistency,
        "objective_delta_candidate_minus_baseline": obj_delta,
        "judge_calibration": {"n_anchor": n_anchor, "agreement": agree, "cohen_kappa": kappa,
                              "trusted": judge_trusted, "trust_kappa_threshold": TRUST_KAPPA},
        "verdict": verdict,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aletheia eval measurement core (win-rate + judge trust).")
    ap.add_argument("results", help="JSON with pairwise/objective/human")
    args = ap.parse_args(argv)
    print(json.dumps(summarize(json.load(open(args.results, encoding="utf-8"))), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
