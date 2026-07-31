#!/usr/bin/env python3
"""Diagnose adapter/query and identity behavior after the frozen primary run.

This is deliberately *not* part of the preregistered primary endpoint.  It
does not alter ``tasks.json`` or re-score ``observed-1.json``.  Its narrow
purpose is to distinguish a genuinely unavailable source from a failure in
query translation, endpoint canonicalization, or the primary URL-only matcher.

The output contains volatile public metadata and belongs below ``raw/``.  A
separate checked-in summary records only the derived observations and hashes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


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


def load_runtime(runtime_root: Path):
    scripts = runtime_root / ".cursor" / "skills" / "channel-retrieval" / "scripts"
    if not scripts.is_dir():
        raise SystemExit("runtime root does not contain channel-retrieval scripts")
    sys.path[:0] = [str(scripts)]
    http = importlib.import_module("_http")
    return {
        "_http": http,
        "europepmc": importlib.import_module("europepmc"),
        "arxiv": importlib.import_module("arxiv"),
        "github": importlib.import_module("github"),
        "openalex": importlib.import_module("openalex"),
    }


CASES: tuple[dict[str, Any], ...] = (
    {
        "id": "europepmc-aligned-topic-query",
        "channel": "europepmc",
        "query": "creatine cognition EFSA",
        "expect": {
            "url_contains_any": ["39564533"],
            "title_contains_all": ["creatine", "improvement", "cognitive", "function"],
        },
        "purpose": "Check whether a concise topic query reaches the predeclared biomedical work even when the adapter emits a PMC URL instead of a PubMed URL.",
    },
    {
        "id": "europepmc-exact-pmid",
        "channel": "europepmc",
        "query": "39564533",
        "expect": {
            "url_contains_any": ["39564533"],
            "title_contains_all": ["creatine", "improvement", "cognitive", "function"],
        },
        "purpose": "Check the adapter's exact-identifier route and reveal whether the normalized record preserves the requested PMID.",
    },
    {
        "id": "arxiv-exact-id",
        "channel": "arxiv",
        "query": "2604.02460",
        "expect": {
            "url_contains_any": ["2604.02460"],
            "title_contains_all": ["single-agent", "multi-agent", "equal", "thinking"],
        },
        "purpose": "Check whether the arXiv adapter itself can retrieve the predeclared work under its stable identifier.",
    },
    {
        "id": "github-natural-question",
        "channel": "github",
        "query": "What does Karpathy autoresearch constrain agents to change during its experiments?",
        "expect": {
            "url_contains_any": ["github.com/karpathy/autoresearch"],
            "title_contains_all": ["karpathy/autoresearch"],
        },
        "purpose": "Expose the adapter's four-keyword compaction and its effect on a realistic natural-language request.",
    },
    {
        "id": "github-exact-slug",
        "channel": "github",
        "query": "karpathy/autoresearch",
        "expect": {
            "url_contains_any": ["github.com/karpathy/autoresearch"],
            "title_contains_all": ["karpathy/autoresearch"],
        },
        "purpose": "Check whether the GitHub adapter can retrieve the repository once an exact slug is already known.",
    },
    {
        "id": "openalex-natural-question-error",
        "channel": "openalex",
        "query": "Does creatine monohydrate supplementation improve cognition in healthy adults?",
        "expect": {},
        "capture_http_error": True,
        "purpose": "Capture the provider error produced by the literal natural-language question, including punctuation handling.",
    },
    {
        "id": "openalex-sanitized-concept-query",
        "channel": "openalex",
        "query": "creatine cognition",
        "expect": {},
        "purpose": "Confirm that the same endpoint is reachable with a punctuation-free compact query; this is a health/query-formulation diagnostic, not a landmark lookup.",
    },
)


def effective_query(case: dict[str, Any], modules: dict[str, Any]) -> str:
    channel, query = case["channel"], case["query"]
    if channel == "github":
        return modules["_http"].keywordize(query, 4)
    if channel == "openalex":
        return modules["openalex"]._search_query(query)
    return query


def match_rows(rows: list[dict[str, Any]], expect: dict[str, Any]) -> list[dict[str, Any]]:
    url_needles = [str(v).lower() for v in expect.get("url_contains_any", [])]
    title_needles = [str(v).lower() for v in expect.get("title_contains_all", [])]
    matches = []
    for rank, row in enumerate(rows, start=1):
        url, title = str(row.get("url") or "").lower(), str(row.get("title") or "").lower()
        url_hit = bool(url_needles) and any(needle in url for needle in url_needles)
        title_hit = bool(title_needles) and all(needle in title for needle in title_needles)
        if url_hit or title_hit:
            matches.append({
                "rank": rank,
                "url_match": url_hit,
                "title_match": title_hit,
                "url": row.get("url"),
                "title": row.get("title"),
                "doi": row.get("doi"),
            })
    return matches


def public_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = ("url", "title", "doi", "published", "snippet", "id", "index_of_origin")
    return [{field: row.get(field) for field in fields if field in row} for row in rows]


def capture_openalex_error(query: str, modules: dict[str, Any], timeout: float) -> dict[str, Any] | None:
    """Persist the provider's public error explanation for this one diagnostic."""
    openalex, http = modules["openalex"], modules["_http"]
    rendered = openalex._search_query(query)
    url = "https://api.openalex.org/works?per_page=8&search=" + http.quote(rendered)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": http.UA})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=timeout) as response:
            return {"status": response.status, "body": response.read(2000).decode("utf-8", "replace")}
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "body": exc.read(2000).decode("utf-8", "replace")}
    except Exception as exc:  # Retain failure as diagnostic evidence, never hide it.
        return {"status": None, "error": f"{type(exc).__name__}: {str(exc)[:300]}"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--out", required=True, help="ignored raw JSON output path")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    if args.limit < 1 or args.timeout <= 0:
        raise SystemExit("limit and timeout must be positive")

    runtime_root, out_path = Path(args.runtime_root).resolve(), Path(args.out).resolve()
    modules = load_runtime(runtime_root)
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "post_hoc_diagnostic_not_primary_endpoint",
        "started_at_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "runtime_root": str(runtime_root),
        "runtime_commit": runtime_commit(runtime_root),
        "limit": args.limit,
        "timeout_seconds": args.timeout,
        "cases": [],
    }
    for case in CASES:
        module = modules[case["channel"]]
        started = time.monotonic()
        try:
            rows = module.search(case["query"], args.limit, args.timeout) or []
            error = None
        except Exception as exc:  # The error is an observed result, not a script failure.
            rows = []
            error = f"{type(exc).__name__}: {str(exc)[:300]}"
        item = {
            "id": case["id"],
            "channel": case["channel"],
            "purpose": case["purpose"],
            "input_query": case["query"],
            "effective_query": effective_query(case, modules),
            "returned": len(rows),
            "latency_s": round(time.monotonic() - started, 3),
            "error": error,
            "matches": match_rows(rows, case.get("expect") or {}),
            "records": public_rows(rows),
        }
        if case.get("capture_http_error"):
            item["provider_response"] = capture_openalex_error(case["query"], modules, args.timeout)
        result["cases"].append(item)
        first = item["matches"][0] if item["matches"] else None
        print(f"{item['id']}: n={item['returned']} error={bool(error)} first_match={first and first['rank']}")
    result["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    result["result_sha256"] = digest({key: value for key, value in result.items() if key != "result_sha256"})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"result_sha256={result['result_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
