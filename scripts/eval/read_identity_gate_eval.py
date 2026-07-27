#!/usr/bin/env python3
"""Deterministic mechanism A/B for the semantic read-identity gate.

This is not a general research-quality benchmark. It asks one falsifiable question: compared with
production's effective length/readability predicate, does the candidate reject the exact observed
wrong bodies while retaining deliberately difficult valid controls?
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AR = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts")
sys.path.insert(0, AR)
import read_identity  # noqa: E402

DEFAULT_FIXTURE = os.path.join(ROOT, "tests", "fixtures", "read_identity_cases.json")
PAD = (" This portable fixture retains the observed identity front matter while adding neutral "
       "article prose so it crosses the production length-only success threshold. Evidence methods "
       "results limitations and discussion are represented without adding another title or identifier.")


def load_cases(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        cases = json.load(fh)
    for case in cases:
        case["body"] = case["front"] + (PAD * 12 if case.get("pad") else "")
    return cases


def baseline_read_ok(case: Dict[str, Any]) -> bool:
    """Production's effective success predicate after the reader returns a body."""
    body = case["body"]
    method = str(case.get("method") or "jina").lower()
    return method != "blocked" and len(body.strip()) >= 1500


def evaluate(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for case in cases:
        candidate = read_identity.assess_read(
            case["record"], case["body"], case.get("resolved_url", ""),
            case.get("method", "jina"), False)
        expected_ok = bool(case["expected_read_ok"])
        baseline_ok = baseline_read_ok(case)
        row = {
            "id": case["id"],
            "expected_identity": case["expected_identity"],
            "expected_read_ok": expected_ok,
            "baseline_read_ok": baseline_ok,
            "candidate_identity": candidate["identity_state"],
            "candidate_content": candidate["content_state"],
            "candidate_read_ok": candidate["read_ok"],
            "baseline_correct": baseline_ok == expected_ok,
            "candidate_correct": (candidate["read_ok"] == expected_ok
                                  and candidate["identity_state"] == case["expected_identity"]
                                  and (not case.get("expected_content")
                                       or candidate["content_state"] == case["expected_content"])),
        }
        rows.append(row)
    positives = [row for row in rows if row["expected_read_ok"]]
    negatives = [row for row in rows if not row["expected_read_ok"]]
    mismatches = [row for row in rows if row["expected_identity"] == "mismatch"]
    return {
        "schema_version": 1,
        "fixture_cases": len(rows),
        "baseline_correct": sum(row["baseline_correct"] for row in rows),
        "candidate_correct": sum(row["candidate_correct"] for row in rows),
        "baseline_false_accepts": sum(row["baseline_read_ok"] for row in negatives),
        "candidate_false_accepts": sum(row["candidate_read_ok"] for row in negatives),
        "baseline_false_rejects": sum(not row["baseline_read_ok"] for row in positives),
        "candidate_false_rejects": sum(not row["candidate_read_ok"] for row in positives),
        "candidate_mismatch_sensitivity": (
            sum(row["candidate_identity"] == "mismatch" for row in mismatches) / len(mismatches)
            if mismatches else None),
        "rows": rows,
        "interpretation_limit": (
            "Portable exact-defect reproductions plus hand-built boundary controls; this establishes "
            "mechanism behavior, not open-web prevalence or end-to-end research-quality improvement."),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE)
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)
    result = evaluate(load_cases(args.fixture))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload)
    sys.stdout.write(payload)
    return 0 if result["candidate_correct"] == result["fixture_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
