#!/usr/bin/env python3
"""Replay the candidate identity gate over a completed production run without refetching."""
from __future__ import annotations

from collections import Counter
import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AR = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts")
sys.path.insert(0, AR)
import read_identity  # noqa: E402


def _rows(path: str):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    row = json.loads(line)
                    if isinstance(row, dict):
                        yield row
    except (OSError, ValueError):
        return


def audit(run: str) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for directory, _subdirs, files in os.walk(os.path.join(run, "tree")):
        if "sources.jsonl" not in files:
            continue
        for source in _rows(os.path.join(directory, "sources.jsonl")):
            if not source.get("_read_ok") or not source.get("_read_file"):
                continue
            note = os.path.join(directory, source["_read_file"])
            if not os.path.isfile(note):
                continue
            with open(note, encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
            first = raw.splitlines()[0] if raw else ""
            body = re.sub(r"^<!--.*?-->\s*", "", raw, count=1, flags=re.S)
            method_match = re.search(r"\(via ([^)]+)\)", first)
            method = method_match.group(1) if method_match else ""
            assessed = read_identity.assess_read(
                source, body, source.get("_resolved_url", ""), method,
                bool(source.get("_truncated")))
            results.append({
                "node": os.path.relpath(directory, run),
                "url": source.get("url", ""),
                "title": source.get("title", ""),
                "note": os.path.relpath(note, run),
                "production_read_ok": True,
                "candidate_read_ok": assessed["read_ok"],
                "identity_state": assessed["identity_state"],
                "content_state": assessed["content_state"],
                "identity_reason": assessed["identity"]["reason"],
                "observed_title": assessed["identity"]["observed_title"],
                "expected_identifiers": assessed["identity"]["expected_identifiers"],
                "observed_identifiers": assessed["identity"]["observed_identifiers"],
                "content_sha256": assessed["content_sha256"],
            })
    identity = Counter(row["identity_state"] for row in results)
    content = Counter(row["content_state"] for row in results)
    return {
        "schema_version": 1,
        "run": os.path.abspath(run),
        "production_successful_reads": len(results),
        "candidate_successful_reads": sum(row["candidate_read_ok"] for row in results),
        "candidate_rejections": sum(not row["candidate_read_ok"] for row in results),
        "identity_states": dict(sorted(identity.items())),
        "content_states": dict(sorted(content.items())),
        "rejected": [row for row in results if not row["candidate_read_ok"]],
        "rows": results,
        "interpretation_limit": (
            "Offline replay over persisted production artifacts. It measures gate activation on one "
            "run; it does not estimate open-web failure prevalence or resolver recovery rate."),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--run-label", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args(argv)
    result = audit(args.run)
    if args.run_label:
        result["run"] = args.run_label
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload)
    sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
