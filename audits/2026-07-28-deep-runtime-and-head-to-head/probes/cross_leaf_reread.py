#!/usr/bin/env python3
"""Hermetic audit probe: prove cross-leaf full reads are not run-globally deduplicated.

This audit-only script never contacts the network and never changes the checkout. It creates a
temporary quick Aletheia run, gives two leaves the same local stub candidate, and replaces the
full-text reader with an in-memory response. The frozen runtime should make two reader calls and
create one note per leaf while writing only one row to the global source index.

Run from any working directory:
  python3 audits/2026-07-28-deep-runtime-and-head-to-head/probes/cross_leaf_reread.py \
    --out /tmp/cross_leaf_reread-result.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SKILL_SCRIPTS = ROOT / ".cursor" / "skills" / "aletheia-research" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

import investigate  # noqa: E402
import treestate  # noqa: E402

URL = "https://example.com/shared-paper"
RECORD = {
    "url": URL,
    "title": "Shared Evidence Paper",
    "snippet": "shared evidence paper",
    "index_of_origin": "openalex",
    "channel_class": "evidence",
    "primary": True,
}


def _note_count(node: str) -> int:
    notes = Path(node) / "notes"
    return sum(1 for path in notes.iterdir() if path.is_file() and path.suffix == ".md")


def run_probe() -> dict[str, Any]:
    """Run against a TemporaryDirectory only and return a deterministic assertion record."""
    reader_urls: list[str] = []
    previous_dispatch = investigate.DISPATCH.get("audit_stub")
    previous_require_enabled = investigate.channel_config.require_enabled
    previous_read_source = investigate._read_source

    try:
        investigate.DISPATCH["audit_stub"] = lambda _q, _n, _t: [dict(RECORD)]
        investigate.channel_config.require_enabled = lambda _channel: None

        def fake_read_source(url: str, _timeout: float):
            reader_urls.append(url)
            return ("EVIDENCE " * 250, "audit-stub", url)

        investigate._read_source = fake_read_source

        with tempfile.TemporaryDirectory(prefix="aletheia-cross-leaf-reread-") as base:
            run = treestate.init_run("shared evidence paper", base=base, thoroughness="quick")
            root = os.path.join(run, "tree", "root")
            left, right = treestate.split_node(root, [
                ["left", "shared evidence paper lens left"],
                ["right", "shared evidence paper lens right"],
            ])
            for node in (left, right):
                investigate.investigate(node, channels=["audit_stub"])

            index_path = Path(run) / "index" / "sources.jsonl"
            with index_path.open(encoding="utf-8") as fh:
                index_rows = [json.loads(line) for line in fh if line.strip()]
            note_counts = [_note_count(left), _note_count(right)]

        assertions = {
            "reader_calls_exactly_two": len(reader_urls) == 2,
            "reader_urls_are_same_shared_url": reader_urls == [URL, URL],
            "global_index_rows_exactly_one": len(index_rows) == 1,
            "one_note_per_leaf": note_counts == [1, 1],
        }
        if not all(assertions.values()):
            raise AssertionError("cross-leaf reread probe failed: %s" % assertions)

        return {
            "probe": "cross_leaf_reread_despite_global_index_dedup",
            "network": "not attempted; retrieval and reader were local in-process stubs",
            "reader_calls": len(reader_urls),
            "reader_urls": reader_urls,
            "global_index_rows": len(index_rows),
            "global_index_urls": [row.get("url") for row in index_rows],
            "per_leaf_note_counts": note_counts,
            "assertions": assertions,
            "result": "pass",
            "interpretation": (
                "The global index deduplicated its row, but node-local read selection still read the "
                "same URL once in each leaf. This is a cost/latency scaling property, not a claim "
                "that independent re-reads are always epistemically wrong."
            ),
        }
    finally:
        investigate._read_source = previous_read_source
        investigate.channel_config.require_enabled = previous_require_enabled
        if previous_dispatch is None:
            investigate.DISPATCH.pop("audit_stub", None)
        else:
            investigate.DISPATCH["audit_stub"] = previous_dispatch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="write deterministic JSON result here")
    args = parser.parse_args()

    payload = run_probe()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
