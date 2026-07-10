#!/usr/bin/env python3
"""Compare evaluator judgments on a frozen known-defect suite.

The fixture contains gold relations, not executable natural-language truth.  A judge (model or
human) must produce a separate evidence-bearing JSONL artifact.  This scorer validates that every
case was persisted, compares predictions with gold, and gates catastrophic defects and bias controls.
It never copies the fixture's expected label into a prediction.  Crucially, fixture conformance is
not an implementation-efficacy result unless the judgments are independently produced and the case
set meets the declared release-size and balance requirements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

EXPECTED_FIXTURE_SHA256 = "2ac645d111a7e3ae8c8bcef78cb536833d3321b9eaf64ae6dffb3ecb2e449202"
MIN_RELEASE_CASES = 30
MIN_CASES_PER_DIMENSION = 3
IMPLEMENTATION_OUTPUT_PROVENANCE = {
    "implementation-output-independent-human",
    "implementation-output-independent-model",
    "implementation-output-independent-mixed",
}
CATASTROPHIC_IDS = {
    "kd-01-entity-swap", "kd-02-number-swap", "kd-03-polarity-flip", "kd-04-unit-error",
    "kd-05-stale-current-claim", "kd-06-false-premise", "kd-13-critical-omission",
    "kd-14-trivial-high-precision", "kd-15-internal-contradiction",
    "kd-16-evidence-disagreement-smoothed", "kd-22-prior-scope-regression",
}
CONTROL_IDS = {"kd-19-repetitive-padding", "kd-20-order-swap", "kd-21-identical-order-control"}


def _sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _load_jsonl(path: str) -> List[Dict[str, Any]]:
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


def _indexed(rows: List[Dict[str, Any]], label: str) -> Dict[str, Dict[str, Any]]:
    out = {}
    for row in rows:
        case_id = str(row.get("id") or "").strip()
        if not case_id:
            raise ValueError("%s judgment missing id" % label)
        if case_id in out:
            raise ValueError("%s has duplicate id %s" % (label, case_id))
        if not str(row.get("judge") or "").strip():
            raise ValueError("%s %s missing judge identity" % (label, case_id))
        if not str(row.get("rationale") or "").strip():
            raise ValueError("%s %s missing rationale" % (label, case_id))
        out[case_id] = row
    return out


def _matches(expected: str, judgment: Dict[str, Any]) -> bool:
    relation = str(judgment.get("relation") or "").strip()
    if expected == "clean_or_tie_never_mutated":
        return relation in ("clean_better", "tie")
    if expected == "clean_better_in_both_orders":
        orders = judgment.get("orders") or {}
        return (relation == "clean_better" and isinstance(orders, dict)
                and orders.get("candidate_first") == "clean_better"
                and orders.get("baseline_first") == "clean_better")
    if expected == "tie_in_both_orders":
        orders = judgment.get("orders") or {}
        return (relation == "tie" and isinstance(orders, dict)
                and orders.get("candidate_first") == "tie"
                and orders.get("baseline_first") == "tie")
    if expected == "hardened_null_legacy_false_pass":
        return relation == "hardened_null_legacy_false_pass"
    if expected == "new_metric_agrees_with_human_source_choice_or_abstains":
        return relation in ("candidate_better", "abstain")
    if expected == "report_length_and_padding_sensitivity_without_assuming_length_causes_quality":
        return relation == "confounded_reported"
    return relation == expected


def score(fixture_rows: List[Dict[str, Any]], judgments: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
    by_id = _indexed(judgments, label)
    fixture_ids = [str(row.get("id")) for row in fixture_rows]
    missing = sorted(set(fixture_ids) - set(by_id))
    extra = sorted(set(by_id) - set(fixture_ids))
    cases = []
    by_dimension: Dict[str, List[bool]] = defaultdict(list)
    for item in fixture_rows:
        case_id = str(item.get("id"))
        judgment = by_id.get(case_id)
        correct = bool(judgment) and _matches(str(item.get("expected_relation") or ""), judgment)
        dimension = str(item.get("dimension") or "unknown")
        by_dimension[dimension].append(correct)
        cases.append({"id": case_id, "dimension": dimension, "correct": correct,
                      "expected": item.get("expected_relation"),
                      "predicted": judgment.get("relation") if judgment else None})
    n = len(fixture_rows)
    correct_n = sum(1 for case in cases if case["correct"])
    catastrophic = [case for case in cases if case["id"] in CATASTROPHIC_IDS]
    controls = [case for case in cases if case["id"] in CONTROL_IDS]
    return {
        "label": label,
        "judgment_count": len(judgments),
        "missing": missing,
        "extra": extra,
        "correct": correct_n,
        "total": n,
        "accuracy": round(correct_n / n, 3) if n else None,
        "catastrophic_recall": round(sum(c["correct"] for c in catastrophic) / len(catastrophic), 3)
                               if catastrophic else None,
        "controls_retained": all(c["correct"] for c in controls) if controls else False,
        "by_dimension": {dim: {"correct": sum(values), "total": len(values),
                                "accuracy": round(sum(values) / len(values), 3)}
                         for dim, values in sorted(by_dimension.items())},
        "cases": cases,
        "fixture_conformance_passed": (not missing and not extra and correct_n == n
                                       and all(c["correct"] for c in catastrophic)
                                       and all(c["correct"] for c in controls)),
    }


def compare(fixture: str, old: str, new: str, old_provenance: str = "unspecified",
            new_provenance: str = "unspecified", provenance_note: str = "") -> Dict[str, Any]:
    fixture_hash = _sha256(fixture)
    if fixture_hash != EXPECTED_FIXTURE_SHA256:
        raise ValueError("fixture SHA mismatch: %s" % fixture_hash)
    fixture_rows = _load_jsonl(fixture)
    old_rows, new_rows = _load_jsonl(old), _load_jsonl(new)
    old_score, new_score = score(fixture_rows, old_rows, "old"), score(fixture_rows, new_rows, "v2")
    dimension_counts = Counter(str(row.get("dimension") or "unknown") for row in fixture_rows)
    independent = new_provenance in IMPLEMENTATION_OUTPUT_PROVENANCE
    enough_cases = len(fixture_rows) >= MIN_RELEASE_CASES
    balanced = bool(dimension_counts) and min(dimension_counts.values()) >= MIN_CASES_PER_DIMENSION
    release_reasons = []
    if not new_score["fixture_conformance_passed"]:
        release_reasons.append("known_defect_fixture_not_passed")
    if not independent:
        release_reasons.append("new_judgments_not_independent")
    if not enough_cases:
        release_reasons.append("fewer_than_%d_known_defect_cases" % MIN_RELEASE_CASES)
    if not balanced:
        release_reasons.append("fewer_than_%d_cases_in_at_least_one_dimension" %
                               MIN_CASES_PER_DIMENSION)
    release_passed = not release_reasons
    return {
        "schema_version": 2,
        "fixture_sha256": fixture_hash,
        "fixture_case_count": len(fixture_rows),
        "fixture_dimension_counts": dict(sorted(dimension_counts.items())),
        "judgment_sha256": {"old": _sha256(old), "v2": _sha256(new)},
        "judgment_provenance": {
            "old": old_provenance,
            "v2": new_provenance,
            "v2_is_independently_adjudicated_implementation_output": independent,
            "note": provenance_note,
        },
        "old": old_score,
        "v2": new_score,
        "delta_accuracy_v2_minus_old": round(new_score["accuracy"] - old_score["accuracy"], 3),
        "calibration_target_conformance_passed": new_score["fixture_conformance_passed"],
        "implementation_validated": release_passed,
        "meta_eval_passed": release_passed,
        "release_gate": {
            "passed": release_passed,
            "reasons": release_reasons,
            "requirements": {
                "independently_adjudicated_implementation_output": True,
                "min_cases": MIN_RELEASE_CASES,
                "min_cases_per_dimension": MIN_CASES_PER_DIMENSION,
                "complete_catastrophic_and_control_conformance": True,
            },
        },
        "limitation": ("Fixture conformance shows that a judgment artifact encodes the design target. "
                       "It does not show that evaluator code produced those judgments. Self-authored or "
                       "design-target labels cannot validate implementation efficacy or release readiness."),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compare old and v2 judgments on frozen defect cases")
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--old-provenance", default="unspecified")
    ap.add_argument("--new-provenance", default="unspecified",
                    choices=sorted(IMPLEMENTATION_OUTPUT_PROVENANCE |
                                   {"self-authored-design-target", "unspecified"}))
    ap.add_argument("--provenance-note", default="")
    ap.add_argument("--output", default="")
    args = ap.parse_args(argv)
    try:
        result = compare(args.fixture, args.old, args.new, args.old_provenance,
                         args.new_provenance, args.provenance_note)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write("defect-meta-eval: %s\n" % exc)
        return 2
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        os.makedirs(os.path.dirname(os.path.realpath(args.output)) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    sys.stdout.write(text)
    return 0 if result["meta_eval_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
