#!/usr/bin/env python3
"""Grade whether an Aletheia Accuracy run executed its promised architecture.

This is a structural/runtime grade, not a truth oracle. Semantic factual accuracy, answer recall,
source-role quality, temporal correctness, and contradiction recall require independent rubrics.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(REPO, ".cursor", "skills", "aletheia-research-accuracy")
REPORT = os.path.join(SKILL, "scripts", "report.py")
LEDGER = os.path.join(SKILL, "scripts", "ledger.py")
TREESTATE = os.path.join(SKILL, "scripts", "treestate.py")


def _json(path: str, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    value = json.loads(line)
                    if isinstance(value, dict):
                        rows.append(value)
    except (OSError, ValueError):
        return []
    return rows


def _tool_json(script: str, command: str, run: str) -> Dict[str, Any]:
    raw = subprocess.check_output([sys.executable, script, command, "--run", run], text=True)
    return json.loads(raw)


def grade(run: str) -> Dict[str, Any]:
    run = os.path.realpath(run)
    cfg = _json(os.path.join(run, "run.json"), {}) or {}
    runtime_ledger = _json(os.path.join(run, "runtime-ledger.json"), {}) or {}
    runtime_events = _jsonl(os.path.join(run, "runtime-events.jsonl"))
    score = _tool_json(REPORT, "score", run)
    ledger_audit = _tool_json(LEDGER, "audit", run)
    ledger_state = _tool_json(LEDGER, "show", run)
    run_log = _tool_json(TREESTATE, "audit-log", run)
    telemetry = score.get("runtime") or {}
    observability = score.get("observability") or {}
    limits = cfg.get("limits") or {}
    evidence = ledger_state.get("evidence") or {}
    verdicts = ledger_state.get("verdicts") or {}
    elapsed = float(observability.get("elapsed_seconds", 0) or 0)

    gates = []
    def gate(gid: str, weight: int, passed: bool, detail: Any) -> None:
        gates.append({"id": gid, "weight": weight, "passed": bool(passed), "detail": detail})

    version = str(cfg.get("version") or "")
    gate("accuracy_identity", 5,
         version.startswith("aletheia-research-accuracy 0.6.") and cfg.get("thoroughness") == "accuracy",
         {"version": version, "thoroughness": cfg.get("thoroughness")})
    limits_ok = (0 < float(limits.get("max_seconds", 0) or 0) <= 3600
                 and 0 < int(limits.get("max_reads_per_round", 0) or 0) <= 40
                 and 0 < int(limits.get("max_read_attempts", 0) or 0) <= 640)
    gate("hard_ceilings", 5, limits_ok, limits)
    gate("unified_run_log", 10,
         run_log.get("chain_valid") is True
         and not run_log.get("missing_required_events")
         and observability.get("request_preserved") is True
         and observability.get("channel_health_preserved") is True
         and (observability.get("agent_lifecycle") or {}).get("valid") is True,
         {"run_log": run_log, "request_preserved": observability.get("request_preserved"),
          "channel_health_preserved": observability.get("channel_health_preserved"),
          "agent_lifecycle": observability.get("agent_lifecycle")})
    read_accounting = observability.get("read_accounting") or {}
    gate("runtime_and_read_accounting", 15,
         bool(runtime_events) and int(runtime_ledger.get("search_attempts", 0) or 0) > 0
         and read_accounting.get("valid") is True
         and elapsed <= float(limits.get("max_seconds", 0) or 0)
         and (int(telemetry.get("reads_ok", 0) or 0) == 0
              or int(telemetry.get("engine_read_artifacts", 0) or 0) > 0),
         {"reservation_events": len(runtime_events), "ledger": runtime_ledger,
          "elapsed_seconds": elapsed, "read_accounting": read_accounting})
    log_counts = run_log.get("event_counts") or {}
    gate("research_trace", 10,
         int(telemetry.get("retrieval_passes", 0) or 0) > 0
         and int(telemetry.get("read_artifacts", 0) or 0) > 0
         and (observability.get("manifest_integrity") or {}).get("valid") is True,
         {"retrieval_passes": telemetry.get("retrieval_passes"),
          "read_artifacts": telemetry.get("read_artifacts"),
          "candidate_manifests": log_counts.get("candidate_manifest_persisted", 0),
          "manifest_integrity": observability.get("manifest_integrity"),
          "selection_events": int(log_counts.get("sources_selected", 0) or 0)
                              + int(log_counts.get("sources_rejected", 0) or 0)})
    # A trace with no retained choice menu cannot support a source-selection audit.
    gates[-1]["passed"] = bool(gates[-1]["passed"]
                                and int(log_counts.get("candidate_manifest_persisted", 0) or 0) > 0
                                and (int(log_counts.get("sources_selected", 0) or 0)
                                     + int(log_counts.get("sources_rejected", 0) or 0)) > 0)
    gate("claim_ledger_activation", 15,
         int(ledger_audit.get("claims", 0) or 0) > 0
         and ledger_audit.get("ready_for_synthesis") is True
         and ledger_audit.get("epistemically_complete") is True,
         ledger_audit)
    evidence_ok = bool(evidence) and bool(verdicts) and all(
        isinstance(e, dict) and e.get("artifact_valid") is True for e in evidence.values())
    gate("artifact_bound_evidence", 10, evidence_ok,
         {"evidence_rows": len(evidence), "verdict_rows": len(verdicts),
          "all_artifacts_valid": evidence_ok})
    gate("final_claim_verification", 20,
         score.get("citation_complete") is True
         and (score.get("claim_scope_audit") or {}).get("valid") is True
         and (score.get("final_claim_reconciliation") or {}).get("valid") is True,
         {"citation_accuracy": score.get("citation_accuracy"),
          "citation_coverage": score.get("citation_coverage"),
          "citation_denominator": score.get("citation_denominator"),
          "claim_scope_audit": score.get("claim_scope_audit"),
          "claim_recall": score.get("claim_recall"),
          "final_claim_reconciliation": score.get("final_claim_reconciliation")})
    implementation = cfg.get("implementation") or {}
    gate("clean_runtime_fingerprint", 5,
         bool(implementation.get("runtime_sha256")) and implementation.get("git_dirty") is False,
         implementation)
    gate("lifecycle_and_deliverables", 5,
         os.path.isfile(os.path.join(run, "brief.md"))
         and os.path.isfile(os.path.join(run, "score.json"))
         and cfg.get("state") == "complete"
         and (score.get("completion") or {}).get("ready") is True,
         {"brief": os.path.isfile(os.path.join(run, "brief.md")),
          "score": os.path.isfile(os.path.join(run, "score.json")),
          "bundle": os.path.isfile(os.path.join(run, "bundle.md")),
          "run_state": cfg.get("state"), "completion": score.get("completion")})

    points = sum(g["weight"] for g in gates if g["passed"])
    letter = "A" if points >= 90 else "B" if points >= 80 else "C" if points >= 70 else "D" if points >= 60 else "F"
    return {
        "schema_version": 1,
        "run": run,
        "structural_score": points,
        "structural_grade": letter,
        "gates": gates,
        "score": score,
        "ledger_audit": ledger_audit,
        "run_log_audit": run_log,
        "cap_usage": {"elapsed_seconds": elapsed,
                      "read_attempts_reserved": runtime_ledger.get("read_attempts_reserved", 0),
                      "read_artifacts": telemetry.get("read_artifacts", 0),
                      "termination_reason": runtime_ledger.get("termination_reason")},
        "not_measured": ["real_world_factual_truth", "answer_recall", "topic_relative_source_quality",
                         "temporal_correctness", "contradiction_recall", "decision_utility"],
        "note": "A high structural grade proves mechanism execution and artifact integrity, not answer truth.",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--output", default="")
    args = ap.parse_args(argv)
    try:
        result = grade(args.run)
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        sys.stderr.write("grade-accuracy-run: %s\n" % exc)
        return 2
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
