#!/usr/bin/env python3
"""Adversarial concurrency probe for Aletheia's global source index.

This is an audit-only reproduction attempt. It never changes the checkout: each trial uses a
TemporaryDirectory, creates multiple leaf nodes, then concurrently asks them to add the same canonical
URL to the shared index. A duplicate index row demonstrates that add_sources has no transactional
deduplication boundary across workers.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SK = ROOT / ".cursor" / "skills" / "aletheia-research" / "scripts"
sys.path.insert(0, str(SK))
import treestate  # noqa: E402

URL = "https://example.org/audit-canonical-source"


def worker(node: str, gate) -> None:
    gate.wait()
    treestate.add_sources(node, [{
        "url": URL,
        "title": "Concurrent source-index probe",
        "channel_class": "evidence",
        "_class": "evidence",
        "_index_group": "probe",
    }])


def one_trial(workers: int) -> dict:
    base = tempfile.mkdtemp(prefix="aletheia-source-race-")
    try:
        run = treestate.init_run(
            "source index race probe",
            base=base,
            budget=40.0,
            unit=4.0,
            max_depth=1,
            max_children=workers,
            max_nodes=workers + 1,
        )
        root = os.path.join(run, "tree", "root")
        nodes = treestate.split_node(
            root,
            [[f"worker-{i}", f"concurrent source add {i}"] for i in range(workers)],
        )
        ctx = mp.get_context("fork")
        gate = ctx.Barrier(workers)
        ps = [ctx.Process(target=worker, args=(node, gate)) for node in nodes]
        for proc in ps:
            proc.start()
        for proc in ps:
            proc.join(10)
        bad_exit = [proc.exitcode for proc in ps if proc.exitcode != 0]
        index = os.path.join(run, "index", "sources.jsonl")
        with open(index, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        return {
            "rows": len(rows),
            "duplicates": max(0, len(rows) - 1),
            "worker_exit_codes": [proc.exitcode for proc in ps],
            "failed_workers": bad_exit,
        }
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=50)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.workers < 2 or args.workers > 8:
        raise SystemExit("--workers must be 2..8 (the custom probe allocates one leaf per worker)")
    outcomes = [one_trial(args.workers) for _ in range(args.trials)]
    duplicate_trials = sum(1 for result in outcomes if result["duplicates"])
    payload = {
        "probe": "concurrent_add_sources_duplicate_index",
        "trials": args.trials,
        "workers_per_trial": args.workers,
        "duplicate_trials": duplicate_trials,
        "duplicate_rate": round(duplicate_trials / args.trials, 4) if args.trials else 0,
        "max_rows": max((result["rows"] for result in outcomes), default=0),
        "all_worker_exits_zero": all(not result["failed_workers"] for result in outcomes),
        "outcomes": outcomes,
        "interpretation": (
            "A positive duplicate rate demonstrates an index-level race in the unmodified "
            "add_sources implementation. A zero rate is only a non-reproduction under this host/load, "
            "not proof of synchronization."
        ),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print(json.dumps({key: value for key, value in payload.items() if key != "outcomes"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
