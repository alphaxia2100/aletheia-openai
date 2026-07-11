#!/usr/bin/env python3
"""Perform a direct/full/decisive read without escaping run-wide caps or provenance."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
CHANNEL = os.path.join(HERE, "..", "..", "channel-retrieval", "scripts")
for path in (HERE, CHANNEL):
    sys.path.insert(0, path)
import treestate  # noqa: E402
import read as readmod  # noqa: E402


def _artifact(node: str, kind: str, url: str, text: str, method: str) -> str:
    directory = os.path.join(node, "notes", kind)
    os.makedirs(directory, exist_ok=True)
    name = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10] + ".md"
    path = os.path.join(directory, name)
    treestate._write_text(path, "<!-- source: %s (via %s; tracked=%s) -->\n\n%s" %
                          (url, method, kind, text))
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--node", required=True)
    ap.add_argument("--kind", choices=["manual", "full", "decisive", "verification"],
                    default="manual")
    ap.add_argument("--why", required=True)
    ap.add_argument("--max-chars", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=40.0)
    ap.add_argument("--browser", action="store_true")
    args = ap.parse_args(argv)
    node = os.path.abspath(args.node)
    run = treestate._find_run(node)
    if not run:
        ap.error("--node must be inside an initialized run")
    failed = False
    for url in args.urls:
        if not url.lower().startswith(("http://", "https://")):
            sys.stderr.write("tracked-read: non-HTTP URL %s\n" % url)
            failed = True
            continue
        treestate.runtime_checkpoint(node, "before tracked %s read" % args.kind,
                                     fail_if_expired=True)
        treestate.reserve_runtime(node, "read", 1,
                                  "tracked %s read: %s" % (args.kind, url))
        start = time.time()
        try:
            text, method = readmod.read_url(url, args.timeout, args.max_chars, args.browser)
            if not text.strip():
                raise RuntimeError("reader returned no usable content")
            path = _artifact(node, args.kind, url, text, method)
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            row = {"schema_version": 1, "timestamp": treestate._now(), "url": url,
                   "kind": args.kind, "why": args.why, "method": method,
                   "chars": len(text), "ok": True, "seconds": round(time.time() - start, 3),
                   "artifact": os.path.relpath(path, run), "content_sha256": digest}
            treestate._append_jsonl(os.path.join(node, "tracked-reads.jsonl"), row)
            treestate.log_run_event(node, "source_read_completed", actor="orchestrator",
                                    component="tracked-reader", data=row)
            print(json.dumps(row, sort_keys=True))
        except Exception as exc:  # noqa: BLE001
            row = {"url": url, "kind": args.kind, "why": args.why, "ok": False,
                   "error": type(exc).__name__, "message": str(exc)[:240],
                   "seconds": round(time.time() - start, 3)}
            treestate.log_run_event(node, "source_read_failed", actor="orchestrator",
                                    component="tracked-reader", data=row)
            sys.stderr.write("tracked-read: %s: %s\n" % (url, type(exc).__name__))
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
