#!/usr/bin/env python3
"""Offline, deterministic Aletheia runtime microbenchmark.

This audit fixture never calls a connector, reader, browser, or model API.  It imports the
checked-out 0.5 runtime and replaces the in-memory connector dispatch and reader with sleep-based
stand-ins.  Its purpose is narrow: measure the scheduler's retrieval fan-out and read execution
shape, not research quality or real-network latency.

Example:
  python3 audits/2026-07-28-independent-project-audit/benchmarks/runtime_microbenchmark.py \
    --base audits/2026-07-28-independent-project-audit/benchmarks/fixtures/microbenchmark
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from typing import Any, Dict, List


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RESEARCH = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts")
CHANNELS = os.path.join(ROOT, ".cursor", "skills", "channel-retrieval", "scripts")
PROVENANCE = os.path.join(ROOT, ".cursor", "skills", "provenance-audit", "scripts")
for path in (RESEARCH, CHANNELS, PROVENANCE):
    if path not in sys.path:
        sys.path.insert(0, path)

import investigate  # noqa: E402
import treestate  # noqa: E402


def _median(rows: List[float]) -> float:
    return round(statistics.median(rows), 4)


def run_trial(base: str, number: int, channels: List[str], retrieval_delay: float,
              read_delay: float) -> Dict[str, Any]:
    """Run one synthetic one-round quick leaf and return scheduler measurements."""
    run = treestate.init_run(
        "offline performance benchmark",
        slug="trial-%02d" % number,
        base=base,
        thoroughness="quick",
    )
    node = os.path.join(run, "tree", "root")
    retrieval_events: List[Dict[str, float]] = []
    read_events: List[Dict[str, float]] = []

    def make_search(channel: str):
        def search(_query: str, limit: int, _timeout: float) -> List[Dict[str, Any]]:
            started = time.perf_counter()
            time.sleep(retrieval_delay)
            finished = time.perf_counter()
            retrieval_events.append({"channel": channel, "start": started, "end": finished})
            # The synthetic documents are deliberately relevant, unique, evidence-class, and long
            # enough to exercise the real rank/select/read path rather than a no-op branch.
            return [{
                "index_of_origin": channel,
                "channel_class": "evidence",
                "primary": True,
                "url": "https://example.org/%s/%d" % (channel, i),
                "title": "Offline performance benchmark evidence %s %d" % (channel, i),
                "snippet": "Offline performance benchmark evidence about retrieval and reading.",
            } for i in range(limit)]
        return search

    def fake_read(url: str, _timeout: float, _max_chars: int, _browser: bool = False):
        started = time.perf_counter()
        time.sleep(read_delay)
        finished = time.perf_counter()
        read_events.append({"url": url, "start": started, "end": finished})
        return ("Synthetic full-text evidence. " * 100, "synthetic")

    old_dispatch = dict(investigate.DISPATCH)
    old_require_enabled = investigate.channel_config.require_enabled
    old_read_url = investigate.readmod.read_url
    try:
        investigate.DISPATCH.clear()
        investigate.DISPATCH.update({channel: make_search(channel) for channel in channels})
        # The fictitious connector names are not in the user capability overlay.  This in-memory
        # replacement isolates scheduling from capability/configuration policy; no real connector
        # can be invoked because every dispatch entry is synthetic.
        investigate.channel_config.require_enabled = lambda _channel: None
        investigate.readmod.read_url = fake_read
        started = time.perf_counter()
        result = investigate.investigate(
            node,
            channels=channels,
            limit=4,
            reads=4,
            timeout=1.0,
        )
        finished = time.perf_counter()
    finally:
        investigate.DISPATCH.clear()
        investigate.DISPATCH.update(old_dispatch)
        investigate.channel_config.require_enabled = old_require_enabled
        investigate.readmod.read_url = old_read_url

    if result["reads_ok"] != 4:
        raise RuntimeError("expected four successful synthetic reads, got %r" % result)
    search_start = min(event["start"] for event in retrieval_events)
    search_end = max(event["end"] for event in retrieval_events)
    read_start = min(event["start"] for event in read_events)
    read_end = max(event["end"] for event in read_events)
    reads_overlap = any(
        latter["start"] < former["end"]
        for former, latter in zip(read_events, read_events[1:])
    )
    return {
        "trial": number,
        "run": os.path.relpath(run, ROOT),
        "total_wall_s": round(finished - started, 4),
        "retrieval_wall_s": round(search_end - search_start, 4),
        "retrieval_sum_s": round(sum(event["end"] - event["start"] for event in retrieval_events), 4),
        "read_wall_s": round(read_end - read_start, 4),
        "read_sum_s": round(sum(event["end"] - event["start"] for event in read_events), 4),
        "read_calls": len(read_events),
        "reads_overlapped": reads_overlap,
        "reads_ok": result["reads_ok"],
    }


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="audit-owned output directory for synthetic run artifacts")
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--retrieval-delay", type=float, default=0.10)
    parser.add_argument("--read-delay", type=float, default=0.05)
    args = parser.parse_args(argv)
    if args.trials < 1 or args.retrieval_delay <= 0 or args.read_delay <= 0:
        parser.error("trials and both delays must be positive")
    base = os.path.abspath(args.base)
    if not base.startswith(os.path.abspath(HERE) + os.sep):
        parser.error("--base must stay under this audit benchmark directory")
    os.makedirs(base, exist_ok=True)
    channels = ["synthetic-a", "synthetic-b", "synthetic-c"]
    trials = [run_trial(base, i + 1, channels, args.retrieval_delay, args.read_delay)
              for i in range(args.trials)]
    payload = {
        "kind": "offline scheduler microbenchmark",
        "repository": ROOT,
        "configuration": {
            "trials": args.trials,
            "channels": len(channels),
            "retrieval_delay_s_each": args.retrieval_delay,
            "read_delay_s_each": args.read_delay,
            "reads_per_round": 4,
        },
        "summary_median_s": {
            "total_wall_s": _median([row["total_wall_s"] for row in trials]),
            "retrieval_wall_s": _median([row["retrieval_wall_s"] for row in trials]),
            "retrieval_sum_s": _median([row["retrieval_sum_s"] for row in trials]),
            "read_wall_s": _median([row["read_wall_s"] for row in trials]),
            "read_sum_s": _median([row["read_sum_s"] for row in trials]),
        },
        "trials": trials,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
