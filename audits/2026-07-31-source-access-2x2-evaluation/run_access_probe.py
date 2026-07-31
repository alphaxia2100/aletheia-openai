#!/usr/bin/env python3
"""Run the preregistered retrieval/candidate-replay source-access pilot.

The script calls only a frozen runtime's connector adapters. It makes no model
calls and no full-document reads. Write volatile public retrieval metadata to an
ignored path; commit only the derived result and audit interpretation.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def runtime_commit(root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def configure_imports(runtime_root: Path):
    channel_scripts = runtime_root / ".cursor" / "skills" / "channel-retrieval" / "scripts"
    research_scripts = runtime_root / ".cursor" / "skills" / "aletheia-research" / "scripts"
    if not channel_scripts.is_dir() or not research_scripts.is_dir():
        raise SystemExit("runtime root does not contain expected channel/research scripts")
    # Prepend the clean runtime to prevent accidental use of the dirty checkout.
    sys.path[:0] = [str(research_scripts), str(channel_scripts)]
    config = importlib.import_module("_config")
    investigate = importlib.import_module("investigate")
    rank = importlib.import_module("rank")
    return config, investigate, rank


def annotate(records: list[dict[str, Any]], channel: str, config) -> list[dict[str, Any]]:
    indexes = config.load_channels()["indexes"]
    meta = indexes.get(channel, {})
    out: list[dict[str, Any]] = []
    for ordinal, record in enumerate(records, start=1):
        row = copy.deepcopy(record)
        row.setdefault("_channel", channel)
        row["_raw_rank"] = ordinal
        row["_class"] = row.get("channel_class") or meta.get("class", "?")
        row["_index_group"] = meta.get("index_group", channel)
        out.append(row)
    return out


def direct_lane(query: str, channels: list[str], limit: int, timeout: float, config, investigate) -> dict[str, Any]:
    """Make one request per channel and preserve native adapter rank/error state."""
    per: dict[str, Any] = {}
    records: list[dict[str, Any]] = []
    for channel in channels:
        started = time.monotonic()
        try:
            config.require_enabled(channel)
            fetched = investigate.DISPATCH[channel](query, limit, timeout) or []
            rows = annotate(fetched, channel, config)
            records.extend(rows)
            per[channel] = {
                "returned": len(rows),
                "latency_s": round(time.monotonic() - started, 3),
                "error": None,
            }
        except Exception as exc:  # retain connector failures as observations
            per[channel] = {
                "returned": 0,
                "latency_s": round(time.monotonic() - started, 3),
                "error": f"{type(exc).__name__}: {str(exc)[:180]}",
            }
    return {"records": records, "per_channel": per}


def pipeline_replay(query: str, records: list[dict[str, Any]], investigate, rank) -> list[dict[str, Any]]:
    """Replay v0.5 work-level dedupe/rank without another live connector call."""
    unique = investigate._dedupe_records(copy.deepcopy(records))
    subject_terms = investigate._subject_terms(query, include_proper=True)[:3]
    proper_terms = investigate._proper_nouns(query)
    required_subject_terms = [term for term in subject_terms if term in proper_terms]
    return rank.rank(query, unique, subject_terms=subject_terms, required_subject_terms=required_subject_terms)


def matches(record: dict[str, Any], landmark: dict[str, Any]) -> bool:
    url = str(record.get("url") or "").lower()
    return any(str(token).lower() in url for token in landmark.get("url_contains_any", []))


def raw_hit(records: list[dict[str, Any]], landmark: dict[str, Any]) -> dict[str, Any]:
    hits = [record for record in records if matches(record, landmark)]
    if not hits:
        return {"hit": False, "best_raw_rank": None, "matching_records": []}
    ordered = sorted(hits, key=lambda row: (int(row.get("_raw_rank", 10**9)), str(row.get("_channel", ""))))
    return {
        "hit": True,
        "best_raw_rank": int(ordered[0].get("_raw_rank", 0)),
        "matching_records": [
            {"channel": row.get("_channel"), "raw_rank": row.get("_raw_rank"),
             "url": row.get("url"), "title": row.get("title")} for row in ordered
        ],
    }


def replay_hit(ranked: list[dict[str, Any]], landmark: dict[str, Any], top_k: int) -> dict[str, Any]:
    hits = [(position, record) for position, record in enumerate(ranked, start=1) if matches(record, landmark)]
    if not hits:
        return {"hit": False, "rank": None, "retained_top_k": False, "matching_records": []}
    return {
        "hit": True,
        "rank": hits[0][0],
        "retained_top_k": hits[0][0] <= top_k,
        "matching_records": [
            {"rank": position, "channel": record.get("_channel"), "url": record.get("url"),
             "title": record.get("title"), "score": record.get("score")} for position, record in hits
        ],
    }


def public_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Persist only adapter metadata; this probe never obtains body text."""
    fields = ("_channel", "_raw_rank", "_class", "_index_group", "url", "title", "doi", "published", "snippet")
    return [{field: record.get(field) for field in fields if field in record} for record in records]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, help="clean frozen Aletheia checkout")
    parser.add_argument("--tasks", default=str(HERE / "tasks.json"))
    parser.add_argument("--out", required=True, help="ignored raw observation JSON path")
    args = parser.parse_args()

    runtime_root = Path(args.runtime_root).resolve()
    tasks_path = Path(args.tasks).resolve()
    out_path = Path(args.out).resolve()
    tasks_doc = json.loads(tasks_path.read_text(encoding="utf-8"))
    policy = tasks_doc["network_policy"]
    config, investigate, rank = configure_imports(runtime_root)

    result: dict[str, Any] = {
        "schema_version": 1,
        "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "runtime_root": str(runtime_root),
        "runtime_commit": runtime_commit(runtime_root),
        "tasks_sha256": digest(tasks_doc),
        "channel_config": config.active_metadata(),
        "policy": policy,
        "cells": [],
    }
    for task in tasks_doc["tasks"]:
        lanes = {
            "generic_web": list(policy["generic_web"]),
            "specialist": list(task["specialist_channels"]),
        }
        for access, channels in lanes.items():
            lane = direct_lane(task["query"], channels, int(policy["limit_per_channel"]),
                               float(policy["timeout_seconds"]), config, investigate)
            unique = investigate._dedupe_records(copy.deepcopy(lane["records"]))
            ranked = pipeline_replay(task["query"], lane["records"], investigate, rank)
            result["cells"].append({
                "task_id": task["id"],
                "source_stratum": task["source_stratum"],
                "query": task["query"],
                "access": access,
                "channels": channels,
                "landmark": task["landmark"],
                "direct_raw": {
                    "per_channel": lane["per_channel"],
                    "returned": len(lane["records"]),
                    "landmark": raw_hit(lane["records"], task["landmark"]),
                    "records": public_records(lane["records"]),
                },
                "candidate_replay": {
                    "unique": len(unique),
                    "ranked": len(ranked),
                    "landmark": replay_hit(ranked, task["landmark"], int(policy["limit_per_channel"])),
                    "top_candidates": public_records(ranked[:int(policy["limit_per_channel"])]),
                },
            })
    result["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    result["result_sha256"] = digest({key: value for key, value in result.items() if key != "result_sha256"})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for cell in result["cells"]:
        raw = cell["direct_raw"]["landmark"]["hit"]
        replay = cell["candidate_replay"]["landmark"]["retained_top_k"]
        errors = sum(1 for outcome in cell["direct_raw"]["per_channel"].values() if outcome["error"])
        print(f"{cell['task_id']} {cell['access']}: raw_hit={raw} replay_top8={replay} errors={errors}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
