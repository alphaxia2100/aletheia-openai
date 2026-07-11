#!/usr/bin/env python3
"""Persist the channel doctor result inside a run and link it into the unified audit log."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
DOCTOR = os.path.join(HERE, "..", "..", "channel-retrieval", "scripts", "doctor.py")
sys.path.insert(0, HERE)
import treestate  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--timeout", type=float, default=6.0)
    args = ap.parse_args(argv)
    run = os.path.abspath(args.run)
    if not os.path.isfile(os.path.join(run, "run.json")):
        ap.error("--run must contain run.json")
    treestate.runtime_checkpoint(run, "before channel health snapshot", fail_if_expired=True)
    proc = subprocess.run([sys.executable, DOCTOR, "--json", "--timeout", str(args.timeout)],
                          capture_output=True, text=True, timeout=max(30.0, args.timeout * 8))
    try:
        rows = json.loads(proc.stdout) if proc.stdout.strip() else []
    except ValueError as exc:
        sys.stderr.write("capture-health: doctor emitted invalid JSON\n")
        return 2
    counts = {}
    for row in rows:
        status = str(row.get("status") or "unknown") if isinstance(row, dict) else "invalid"
        counts[status] = counts.get(status, 0) + 1
    payload = {"schema_version": 1, "captured_at": treestate._now(),
               "doctor_exit_code": proc.returncode, "status_counts": counts,
               "channels": rows, "stderr": proc.stderr[-2000:]}
    path = os.path.join(run, "channel-health.json")
    treestate._write_json(path, payload)
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    treestate.log_run_event(run, "channel_health_captured", actor="runtime",
                            component="channel-doctor",
                            data={"artifact": "channel-health.json", "sha256": digest,
                                  "status_counts": counts, "doctor_exit_code": proc.returncode})
    print(path)
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
