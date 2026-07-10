#!/usr/bin/env python3
"""Aletheia evaluator v2: fail-closed, semantics-explicit run scoring.

This module is deliberately smaller than a universal factuality evaluator.  It provides the
release-gating guarantees that can be made deterministically today:

* one canonical citation scorer (the scorer shipped with ``aletheia-research``);
* a mandatory final-brief claim-scope attestation, including for legacy runs;
* names that do not misrepresent citation entailment as real-world factual truth; and
* explicit ``None`` values for dimensions that need a frozen rubric or labeled outcomes.

``defect_meta_eval.py`` is only a provenance-aware calibration harness, and
``calibration_score.py`` scores labeled probabilities. Neither supplies the unimplemented semantic
dimensions above. Keeping these layers separate prevents a convenient proxy or self-authored target
artifact from silently turning into a headline accuracy number.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Tuple

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REPORT_PATH = os.path.join(
    REPO, ".cursor", "skills", "aletheia-research", "scripts", "report.py"
)


def _canonical_skill_score(run: str) -> Dict[str, Any]:
    """Call the skill scorer across a process boundary.

    Aletheia generations intentionally retain scripts with generic module names such as
    ``treestate``, ``router``, and ``rank``. Importing the current scorer into a process that also
    evaluates a frozen baseline can therefore replace the baseline's modules through
    ``sys.modules``. The scorer CLI is the canonical public interface and a subprocess keeps those
    incompatible module namespaces isolated.
    """
    if not os.path.isfile(REPORT_PATH):
        raise FileNotFoundError("canonical Aletheia scorer is missing: %s" % REPORT_PATH)
    proc = subprocess.run(
        [sys.executable, REPORT_PATH, "score", "--run", run],
        capture_output=True,
        text=True,
    )
    if proc.returncode:
        detail = (proc.stderr or proc.stdout or "unknown scorer failure").strip()
        raise ValueError("canonical Aletheia scorer failed: %s" % detail)
    value = json.loads(proc.stdout)
    if not isinstance(value, dict):
        raise ValueError("canonical Aletheia scorer returned a non-object")
    return value


def _sha256(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return ""


def _word_count(path: str) -> int:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return 0
    # URLs and Markdown punctuation should not dominate the diagnostic length measure.
    text = re.sub(r"https?://\S+", " ", text)
    return len(re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE))


def _jsonl_rows(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("line %d is not an object" % lineno)
                rows.append(value)
    except OSError:
        return []
    return rows


def _strict_scope(run: str, score: Dict[str, Any], require_scope: bool) -> Dict[str, Any]:
    """Require a valid content-hashed semantic scope attestation for an eval headline.

    The skill scorer preserves read-only compatibility for pre-0.5 runs.  A release evaluator must
    not: otherwise an old output and a new output have different denominator guarantees while both
    display ``1.0``.  This wrapper therefore requires an actual claim_audit.json for every run unless
    an explicitly diagnostic ``require_scope=False`` call is made.
    """
    state = dict(score.get("claim_scope_audit") or {})
    present = os.path.isfile(os.path.join(run, "claim_audit.json"))
    valid = bool(state.get("valid")) and present
    reasons = list(state.get("reasons") or [])
    if require_scope and not present:
        reasons.append("strict_eval_requires_claim_scope_audit")
    if require_scope and present and not state.get("valid"):
        reasons.append("strict_eval_rejects_invalid_claim_scope_audit")
    reasons = list(dict.fromkeys(reasons))
    state.update({
        "required_by_evaluator_v2": require_scope,
        "artifact_present": present,
        "valid_for_evaluator_v2": (valid if require_scope else bool(state.get("valid"))),
        "reasons": reasons,
    })
    score["claim_scope_audit"] = state
    score["scope_gate_passed"] = state["valid_for_evaluator_v2"]
    if require_scope and not valid:
        score["citation_accuracy"] = None
        score["citation_complete"] = False
    elif not require_scope:
        # Diagnostic compatibility only: expose row-level precision even when the skill scorer's
        # version gate required a missing audit.  The CLI labels this mode legacy/no-scope.
        row_complete = bool(score.get("row_verification_complete"))
        score["citation_complete"] = row_complete
        score["citation_accuracy"] = score.get("citation_precision") if row_complete else None
    return score


def score_run(run: str, require_scope: bool = True) -> Dict[str, Any]:
    """Score ``run`` with the skill's canonical scorer and v2's stricter release semantics."""
    run = os.path.realpath(run)
    raw = _canonical_skill_score(run)
    raw = _strict_scope(run, raw, require_scope)
    raw["eval_schema_version"] = 2
    raw["evaluator"] = {
        "name": "aletheia-evaluator-v2",
        "evaluator_sha256": _sha256(os.path.realpath(__file__)),
        "canonical_scorer": os.path.relpath(REPORT_PATH, REPO),
        "canonical_scorer_sha256": _sha256(REPORT_PATH),
        "canonical_scorer_invocation": "isolated-subprocess",
        "python_version": sys.version.split()[0],
        "require_scope_audit": require_scope,
    }
    raw["brief_word_count"] = _word_count(os.path.join(run, "brief.md"))
    raw["extracted_claim_rows"] = len(_jsonl_rows(os.path.join(run, "claims.jsonl")))

    # Precision against cited source text is valuable, but it is not a truth oracle.
    raw["citation_entailment_precision"] = raw.get("citation_precision")
    raw["factual_accuracy"] = None
    raw["answer_recall"] = None
    raw["source_quality"] = None
    raw["probabilistic_calibration"] = None
    raw["temporal_correctness"] = None
    raw["contradiction_recall"] = None
    raw["unmeasured_dimensions"] = {
        "factual_accuracy": "requires independent truth/decisive-evidence adjudication",
        "answer_recall": "requires a frozen topic-specific information rubric",
        "source_quality": "requires a topic-relative cited-source rubric",
        "probabilistic_calibration": "requires labeled outcomes and confidence predictions",
        "temporal_correctness": "requires dated claims and a supersession check",
        "contradiction_recall": "requires internal scanning plus known-dispute rubrics",
    }
    raw["metric_semantics"] = {
        "citation_entailment_precision": (
            "supported submitted citation rows / finally judged readable submitted rows"
        ),
        "citation_coverage": "verification completion over submitted rows; not answer recall",
        "citation_accuracy_compat": (
            "compatibility alias for entailment precision, exposed only after strict scope passes"
        ),
    }
    return raw


def parse_labeled_runs(value: str) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for item in value.split(","):
        if not item.strip():
            continue
        if "=" not in item:
            raise ValueError("run must be label=path: %s" % item)
        label, path = item.split("=", 1)
        if not label.strip() or not path.strip():
            raise ValueError("run must be label=path: %s" % item)
        pairs.append((label.strip(), path.strip()))
    return pairs


def score_runs(pairs: Iterable[Tuple[str, str]], require_scope: bool = True) -> Dict[str, Any]:
    runs = []
    for label, path in pairs:
        runs.append({"label": label, "run": os.path.realpath(path), "score": score_run(path, require_scope)})
    return {"eval_schema_version": 2, "require_scope_audit": require_scope, "runs": runs}


def _atomic_json(path: str, value: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.realpath(path)) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".eval-v2-", dir=os.path.dirname(os.path.realpath(path)) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aletheia evaluator v2")
    sub = ap.add_subparsers(dest="cmd", required=True)
    one = sub.add_parser("score-run", help="score one run, requiring a valid scope audit")
    one.add_argument("--run", required=True)
    one.add_argument("--legacy-no-scope", action="store_true", help="diagnostic only; never release-gating")
    one.add_argument("--output", default="")
    many = sub.add_parser("score-runs", help="score label=path pairs")
    many.add_argument("--runs", required=True, help="comma-separated label=path pairs")
    many.add_argument("--legacy-no-scope", action="store_true", help="diagnostic only")
    many.add_argument("--output", default="")
    args = ap.parse_args(argv)

    require = not args.legacy_no_scope
    try:
        if args.cmd == "score-run":
            result = score_run(args.run, require_scope=require)
        else:
            result = score_runs(parse_labeled_runs(args.runs), require_scope=require)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write("evaluator-v2: %s\n" % exc)
        return 2
    if args.output:
        _atomic_json(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
