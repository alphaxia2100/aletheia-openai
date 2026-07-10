#!/usr/bin/env python3
"""Proper probabilistic calibration and selective-risk metrics for evaluator v2.

Confidence prose is not calibration.  This module accepts binary outcomes plus probabilities,
validates the sample, and reports Brier/log loss, reliability error, discrimination, and (when a
confidence ranking is supplied) risk by retained coverage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

MIN_META_CASES = 10
MIN_RELEASE_CASES = 30


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _validate(outcomes: Iterable[Any], probabilities: Iterable[Any]) -> tuple[List[int], List[float]]:
    ys = list(outcomes)
    ps = list(probabilities)
    if len(ys) != len(ps) or not ys:
        raise ValueError("outcomes and probabilities must have equal non-zero length")
    if any(y not in (0, 1, False, True) for y in ys):
        raise ValueError("outcomes must be binary")
    try:
        ps = [float(p) for p in ps]
    except (TypeError, ValueError) as exc:
        raise ValueError("probabilities must be numeric") from exc
    if any(not math.isfinite(p) or p < 0 or p > 1 for p in ps):
        raise ValueError("probabilities must be finite values in [0,1]")
    return [int(y) for y in ys], ps


def _auroc(ys: List[int], ps: List[float]) -> Optional[float]:
    pos = [p for y, p in zip(ys, ps) if y == 1]
    neg = [p for y, p in zip(ys, ps) if y == 0]
    if not pos or not neg:
        return None
    wins = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 6)


def score_probabilities(outcomes: Iterable[Any], probabilities: Iterable[Any],
                        release_attested: bool = False) -> Dict[str, Any]:
    ys, ps = _validate(outcomes, probabilities)
    n = len(ys)
    brier = sum((p - y) ** 2 for p, y in zip(ps, ys)) / n
    eps = 1e-12
    log_loss = -sum(y * math.log(max(p, eps)) + (1 - y) * math.log(max(1 - p, eps))
                    for p, y in zip(ps, ys)) / n

    # Exact-probability reliability bins are deterministic and appropriate for the frozen fixtures.
    bins: Dict[float, List[int]] = defaultdict(list)
    for y, p in zip(ys, ps):
        bins[round(p, 6)].append(y)
    reliability = []
    ece = 0.0
    for p, values in sorted(bins.items()):
        observed = sum(values) / len(values)
        ece += len(values) / n * abs(observed - p)
        reliability.append({"confidence": p, "n": len(values),
                            "observed_frequency": round(observed, 6),
                            "absolute_gap": round(abs(observed - p), 6)})
    sample_eligible = n >= MIN_RELEASE_CASES and len(set(ys)) == 2
    release_reasons = ((["fewer_than_%d_labeled_outcomes" % MIN_RELEASE_CASES]
                        if n < MIN_RELEASE_CASES else [])
                       + (["single_class_outcomes"] if len(set(ys)) < 2 else [])
                       + (["release_provenance_not_attested"] if not release_attested else []))
    return {
        "n": n,
        "positive_rate": round(sum(ys) / n, 6),
        "brier": round(brier, 6),
        "log_loss": round(log_loss, 6),
        "ece_exact_bins": round(ece, 6),
        "auroc": _auroc(ys, ps),
        "reliability": reliability,
        "valid_for_meta_eval": n >= MIN_META_CASES and len(set(ys)) == 2,
        "meets_minimum_release_sample": sample_eligible,
        "release_provenance_attested": release_attested,
        "valid_for_release_claim": sample_eligible and release_attested,
        "release_invalid_reasons": release_reasons,
    }


def score_selective_risk(outcomes: Iterable[Any], confidence: Iterable[Any],
                         release_attested: bool = False) -> Dict[str, Any]:
    ys, cs = _validate(outcomes, confidence)
    ordered = sorted(zip(cs, ys), key=lambda item: item[0], reverse=True)
    curve = []
    errors = 0
    risk_sum = 0.0
    for rank, (conf, y) in enumerate(ordered, 1):
        errors += 1 - y
        risk = errors / rank
        risk_sum += risk
        curve.append({"coverage": round(rank / len(ordered), 6), "retained": rank,
                      "abstention_rate": round(1 - rank / len(ordered), 6),
                      "threshold": conf, "risk": round(risk, 6),
                      "accuracy": round(1 - risk, 6)})
    sample_eligible = len(ys) >= MIN_RELEASE_CASES and len(set(ys)) == 2
    release_reasons = ((["fewer_than_%d_labeled_outcomes" % MIN_RELEASE_CASES]
                        if len(ys) < MIN_RELEASE_CASES else [])
                       + (["single_class_outcomes"] if len(set(ys)) < 2 else [])
                       + (["release_provenance_not_attested"] if not release_attested else []))
    return {"n": len(ys), "aurc_discrete": round(risk_sum / len(ordered), 6), "curve": curve,
            "valid_for_meta_eval": len(ys) >= MIN_META_CASES and len(set(ys)) == 2,
            "meets_minimum_release_sample": sample_eligible,
            "release_provenance_attested": release_attested,
            "valid_for_release_claim": sample_eligible and release_attested,
            "release_invalid_reasons": release_reasons}


def score_batch(row: Dict[str, Any]) -> Dict[str, Any]:
    outcomes = row.get("outcomes") or []
    release_attested = bool(row.get("release_attested", False))
    result: Dict[str, Any] = {"id": row.get("id"), "dimension": row.get("dimension")}
    systems = row.get("systems")
    if isinstance(systems, dict):
        scored = {name: score_probabilities(outcomes, probs, release_attested)
                  for name, probs in systems.items()}
        result["systems"] = scored
        result["best_brier"] = min(scored, key=lambda name: scored[name]["brier"]) if scored else None
        result["release_trusted"] = bool(scored) and all(
            value["valid_for_release_claim"] for value in scored.values())
        if not result["release_trusted"]:
            result["status"] = "meta-eval-only: insufficient calibration sample for release claim"
    elif "confidence" in row:
        result["selective_risk"] = score_selective_risk(
            outcomes, row.get("confidence") or [], release_attested)
        result["release_trusted"] = result["selective_risk"]["valid_for_release_claim"]
        if not result["release_trusted"]:
            result["status"] = "meta-eval-only: insufficient selective-risk sample for release claim"
    else:
        raise ValueError("batch %s has neither systems nor confidence" % row.get("id"))
    return result


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("%s line %d is not an object" % (path, lineno))
            rows.append(value)
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Score calibration batches with proper metrics")
    ap.add_argument("batches")
    ap.add_argument("--expect-sha256", default="")
    ap.add_argument("--output", default="")
    args = ap.parse_args(argv)
    actual = _sha256(args.batches)
    if args.expect_sha256 and actual != args.expect_sha256:
        sys.stderr.write("calibration-score: fixture SHA mismatch: %s\n" % actual)
        return 2
    try:
        results = [score_batch(row) for row in load_jsonl(args.batches)]
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write("calibration-score: %s\n" % exc)
        return 2
    payload = {"schema_version": 2, "fixture_sha256": actual, "batches": results,
               "release_trusted": bool(results) and all(r["release_trusted"] for r in results)}
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        os.makedirs(os.path.dirname(os.path.realpath(args.output)) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
