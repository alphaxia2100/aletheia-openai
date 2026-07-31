#!/usr/bin/env python3
"""Derive a small checked-in result from ignored live-observation files.

The raw files are intentionally excluded from Git because provider results are
volatile public metadata.  This script makes the derivation explicit: it checks
the recorded result hash, summarizes the literal preregistered endpoint, and
links separately labelled post-hoc diagnostics without silently changing the
primary score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_observation(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    actual = digest({key: value for key, value in doc.items() if key != "result_sha256"})
    if doc.get("result_sha256") != actual:
        raise ValueError(f"{path}: result_sha256 does not verify")
    if not isinstance(doc.get("cells"), list) or len(doc["cells"]) != 6:
        raise ValueError(f"{path}: expected six 3-task × 2-lane cells")
    return doc


def summarize_observation(doc: dict[str, Any], path: Path) -> dict[str, Any]:
    lanes: dict[str, dict[str, Any]] = {}
    for cell in doc["cells"]:
        access = str(cell["access"])
        raw = cell["direct_raw"]["landmark"]
        replay = cell["candidate_replay"]["landmark"]
        row = {
            "task_id": cell["task_id"],
            "raw_hit": bool(raw["hit"]),
            "best_raw_rank": raw["best_raw_rank"],
            "replay_retained_top_8": bool(replay["retained_top_k"]),
            "replay_rank": replay["rank"],
            "channel_errors": sorted(
                channel for channel, result in cell["direct_raw"]["per_channel"].items() if result["error"]
            ),
            "returned": int(cell["direct_raw"]["returned"]),
        }
        lanes.setdefault(access, {"tasks": []})["tasks"].append(row)
    for lane in lanes.values():
        tasks = lane["tasks"]
        lane["raw_hit_count"] = sum(item["raw_hit"] for item in tasks)
        lane["replay_top_8_count"] = sum(item["replay_retained_top_8"] for item in tasks)
        lane["task_count"] = len(tasks)
        lane["channel_error_count"] = sum(len(item["channel_errors"]) for item in tasks)
    return {
        "started_at_utc": doc["started_at_utc"],
        "finished_at_utc": doc["finished_at_utc"],
        "runtime_commit": doc["runtime_commit"],
        "tasks_sha256": doc["tasks_sha256"],
        "recorded_result_sha256": doc["result_sha256"],
        "raw_file_sha256": file_digest(path),
        "lanes": lanes,
    }


def summarize_diagnostic(doc: dict[str, Any], path: Path) -> dict[str, Any]:
    actual = digest({key: value for key, value in doc.items() if key != "result_sha256"})
    if doc.get("result_sha256") != actual:
        raise ValueError(f"{path}: result_sha256 does not verify")
    cases = []
    for item in doc.get("cases", []):
        matches = item.get("matches") or []
        cases.append({
            "id": item["id"],
            "channel": item["channel"],
            "input_query": item["input_query"],
            "effective_query": item["effective_query"],
            "returned": item["returned"],
            "error": item["error"],
            "first_url_match_rank": next((m["rank"] for m in matches if m["url_match"]), None),
            "first_title_match_rank": next((m["rank"] for m in matches if m["title_match"]), None),
            "provider_http_status": (item.get("provider_response") or {}).get("status"),
        })
    return {
        "status": doc["status"],
        "started_at_utc": doc["started_at_utc"],
        "finished_at_utc": doc["finished_at_utc"],
        "runtime_commit": doc["runtime_commit"],
        "recorded_result_sha256": doc["result_sha256"],
        "raw_file_sha256": file_digest(path),
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", required=True)
    parser.add_argument("--replication", required=True)
    parser.add_argument("--diagnostic", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    primary_path, replication_path, diagnostic_path = (
        Path(args.primary).resolve(), Path(args.replication).resolve(), Path(args.diagnostic).resolve()
    )
    primary = load_observation(primary_path)
    replication = load_observation(replication_path)
    diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    result = {
        "schema_version": 1,
        "audit_id": "2026-07-31-source-access-2x2-evaluation",
        "status": "completed_operational_retrieval_pilot_not_answer_quality_benchmark",
        "claimed_primary_contract": {
            "tasks_sha256": primary["tasks_sha256"],
            "rule": "literal URL-substring landmark hit; unchanged after the run",
            "primary_observation": summarize_observation(primary, primary_path),
        },
        "post_hoc_replication": summarize_observation(replication, replication_path),
        "post_hoc_adapter_diagnostic": summarize_diagnostic(diagnostic, diagnostic_path),
        "validity_findings": {
            "preexecution_freeze": "not independently established: the protocol, tasks, and runner were untracked at review time",
            "execution_units": "two adapter invocations per task x access lane (six per aggregate lane; 12 across the three-task run), not two physical HTTP requests; connector-internal retries were not fully logged",
            "network_snapshot": "raw and replay share records within an access lane; generic and specialist retrieval calls were sequential, not a common simultaneous snapshot",
            "rank_comparability": "channel-local raw rank and pooled replay rank are different ordinals and are not a measured rank improvement",
            "semantic_landmark_interpretation": {
                "creatine-cognition": "not_evaluable_under_url_only_matcher: Europe PMC can normalize the PubMed work to a PMC URL while omitting PMID from the record",
                "multiagent-research": "operational miss only: OpenAlex failed on query punctuation and arXiv natural-language retrieval was off target",
                "autoresearch-program": "literal URL score is mechanically valid for the observed generic hit, but one live snapshot is not an access-rate estimate",
            },
            "candidate_replay": "in-memory replay is a narrow deterministic projection; saved public records omit ranker inputs and do not reproduce all specialist replay orders",
        },
        "interpretation_guardrails": [
            "The first live observation is preserved as the claimed-preregistered literal result; timing was not independently auditable.",
            "The replication and adapter diagnostic are post-hoc diagnostics, not pooled primary data.",
            "A candidate hit is neither full-text identity verification nor an answer-quality result.",
            "Literal URL matching is not a valid cross-adapter source-identity layer; Europe PMC demonstrates this directly.",
        ],
    }
    result["result_sha256"] = digest(result)
    out = Path(args.out).resolve()
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"result_sha256={result['result_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
