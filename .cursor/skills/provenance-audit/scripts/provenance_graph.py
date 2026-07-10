#!/usr/bin/env python3
"""Provenance / independence graph — the core of Aletheia.

Computes, per claim, how many *independent* sources support it vs. how many raw
mentions there are (the "40 blogs echoing 1 paper = 1 data point" test), and
flags single-origin claims, circular citation, and discovery monoculture.

Subcommands:
  audit     Independence audit over {claims, sources}.
  citations Citation-independence for one paper given its citers
            (self-citation + same-lab collapse).

Usage:
  provenance_graph.py audit BUNDLE.json [--json]
  provenance_graph.py audit --sources sources.jsonl --claims claims.json [--json]
  provenance_graph.py citations CITERS.json [--json]

Pure Python 3.9+ stdlib (plus optional tldextract via dedupe.py).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(__file__))
import dedupe  # noqa: E402

_SHINGLE_K = 4
_NEARDUP_THRESHOLD = 0.8


def _shingles(text: str, k: int = _SHINGLE_K) -> Set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    if len(words) < k:
        return set(words)
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


# strong-identifier canonicalization — so the SAME work in different notations (arXiv: prefix vs
# bare id, doi.org URL vs bare DOI, .pdf, vN) is recognized as one work, while genuinely DISTINCT
# ids veto the near-duplicate text merge (rule 4). Fixes the audited false-merge of distinct DOIs.
_ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|html|pdf)/([a-z0-9][a-z0-9.\-]*(?:/\d+)?)", re.I)
_ARXIV_PREFIX_RE = re.compile(r"^arxiv:\s*", re.I)


def _norm_doi(raw: Any) -> str:
    # strip the doi.org/dx./www. prefix or a "doi:" label, then any ?query / #fragment / trailing
    # slash — so 10.1/x, https://doi.org/10.1/x/, www.doi.org/10.1/x?y=1 all canonicalize the same.
    return dedupe.normalize_doi(raw)


def _arxiv_id(record: Dict[str, Any]) -> str:
    val = _ARXIV_PREFIX_RE.sub("", str(record.get("arxiv_id") or record.get("arxiv") or "").strip().lower())
    if not val:
        m = _ARXIV_RE.search(str(record.get("url") or ""))
        if m:
            val = m.group(1).lower()
    val = re.sub(r"\.pdf$", "", val)
    return re.sub(r"v\d+$", "", val) if val else ""


def _pmid(record: Dict[str, Any]) -> str:
    raw = str(record.get("pmid") or "")
    if not raw:
        m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", str(record.get("url") or ""), re.I)
        raw = m.group(1) if m else ""
    return re.sub(r"\D", "", raw)


def _work_identity(record: Dict[str, Any]) -> Dict[str, str]:
    ids: Dict[str, str] = {}
    doi = dedupe.doi_from_record(record)
    if doi:
        ids["doi"] = doi
    ax = _arxiv_id(record)
    if ax:
        ids["arxiv"] = ax
    pm = _pmid(record)
    if pm:
        ids["pmid"] = pm
    return ids


def _distinct_works(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """True iff a strong identifier PROVES a and b are different works (distinct DOI / arXiv id /
    PMID). Canonicalized first, so the SAME work in different notations is not seen as distinct. A
    MATCHING strong id dominates: if any shared id type is equal the works are the same, so we never
    block their merge (even if another id type differs)."""
    ia, ib = _work_identity(a), _work_identity(b)
    shared = ia.keys() & ib.keys()
    if any(ia[k] == ib[k] for k in shared):     # a matching strong id => same work; never veto
        return False
    return any(ia[k] != ib[k] for k in shared)


# ---------- shared ----------

class UnionFind:
    def __init__(self) -> None:
        self.parent: Dict[str, str] = {}

    def add(self, x: str) -> None:
        self.parent.setdefault(x, x)

    def find(self, x: str) -> str:
        self.add(x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _index_group_map() -> Dict[str, str]:
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "channel-retrieval", "channels.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:  # noqa: BLE001
        return {}
    return {k: v.get("index_group", k) for k, v in data.get("indexes", {}).items()}


def _norm_name(name: str) -> str:
    return " ".join(str(name).lower().replace(".", " ").split())


def load_sources(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read().strip()
    if not text:
        return []
    # Try whole-file JSON (array, or object with "sources", or a single record).
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        obj = None  # likely JSONL -> fall through
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return obj.get("sources", [obj])
    # JSONL: one record per line
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def load_claims(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        obj = json.load(fh)
    if isinstance(obj, list):
        return obj
    return obj.get("claims", [])


# ---------- audit ----------

def build_clusters(sources: List[Dict[str, Any]]) -> Tuple[UnionFind, Dict[str, Dict[str, Any]]]:
    uf = UnionFind()
    by_id: Dict[str, Dict[str, Any]] = {}
    by_canon: Dict[str, str] = {}
    by_voice: Dict[str, str] = {}
    by_work: Dict[str, str] = {}

    for i, s in enumerate(sources):
        dedupe.annotate(s)
        sid = s.get("id") or dedupe.canonical_url(s.get("url", "")) or ("src-%d" % i)
        if sid in by_id:  # collision: don't silently overwrite a distinct source
            sys.stderr.write("warning: duplicate source id %r; disambiguating\n" % sid)
            sid = "%s#%d" % (sid, i)
        s["id"] = sid
        by_id[sid] = s
        uf.add(sid)

    for sid, s in by_id.items():
        # rule 0: a matching DOI/arXiv/PMID is direct work identity. Do not require shared snippets:
        # claim verification often cites abs/html/pdf variants whose index records have different or
        # empty text fields.
        for kind, value in _work_identity(s).items():
            key = "%s:%s" % (kind, value)
            if key in by_work:
                uf.union(sid, by_work[key])
            else:
                by_work[key] = sid
        # rule 1: same canonical url (literal duplicate)
        canon = s.get("canonical_url") or ""
        if canon:
            if canon in by_canon:
                uf.union(sid, by_canon[canon])
            else:
                by_canon[canon] = sid
        # rule 2: same voice (distinct works never merge; see dedupe.voice_key)
        vk = dedupe.voice_key(s)
        if vk:
            if vk in by_voice:
                uf.union(sid, by_voice[vk])
            else:
                by_voice[vk] = sid
        # rule 3: echo — derives_from collapses into the origin
        for d in (s.get("derives_from") or []):
            if d in by_id:
                uf.union(sid, d)

    # rule 4: content near-duplicate — auto-detect UN-annotated echoes/syndication
    # (a wire story reprinted on N domains, press-release copy-paste) that the
    # agent never tagged with derives_from. Independence must not trust tags alone.
    ids = list(by_id)
    shingles = {sid: _shingles(by_id[sid].get("title", "") + " " + by_id[sid].get("snippet", ""))
                for sid in ids}
    for a_i in range(len(ids)):
        a = ids[a_i]
        sa = shingles[a]
        if len(sa) < 5:  # too little text to judge (e.g. boilerplate "score=5" snippets)
            continue
        for b_i in range(a_i + 1, len(ids)):
            b = ids[b_i]
            sb = shingles[b]
            if len(sb) < 5 or uf.find(a) == uf.find(b):
                continue
            # distinct DOIs/arXiv ids/PMIDs prove different works -> veto the text merge (fixes the
            # false-merge of distinct primaries). A matching id, or no ids, lets the shingle test run
            # (so genuine title/lede echoes still collapse — no over-count of independence).
            if _distinct_works(by_id[a], by_id[b]):
                continue
            inter = len(sa & sb)
            if inter and inter / len(sa | sb) >= _NEARDUP_THRESHOLD:
                uf.union(a, b)

    return uf, by_id


def _citation_edges(by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Set[str]]:
    # Map any ref token (id / doi / canonical url) to a known node id.
    key_to_id: Dict[str, str] = {}
    for sid, s in by_id.items():
        key_to_id[sid] = sid
        if s.get("doi"):
            key_to_id[str(s["doi"]).lower()] = sid
        if s.get("canonical_url"):
            key_to_id[s["canonical_url"]] = sid
    edges: Dict[str, Set[str]] = {sid: set() for sid in by_id}
    for sid, s in by_id.items():
        for r in (s.get("refs") or []):
            tgt = key_to_id.get(str(r).lower()) or key_to_id.get(str(r))
            if tgt and tgt != sid:
                edges[sid].add(tgt)
    return edges


def _find_cycles(edges: Dict[str, Set[str]]) -> List[List[str]]:
    """Iterative DFS back-edge detection (no recursion limit on large graphs)."""
    cycles: List[List[str]] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in edges}

    for start in edges:
        if color[start] != WHITE:
            continue
        color[start] = GRAY
        path: List[str] = [start]
        work: List[Tuple[str, Any]] = [(start, iter(edges.get(start, ())))]
        while work:
            node, it = work[-1]
            advanced = False
            for m in it:
                c = color.get(m, WHITE)
                if c == GRAY and m in path:  # back edge -> cycle
                    cycles.append(path[path.index(m):] + [m])
                elif c == WHITE:
                    color[m] = GRAY
                    path.append(m)
                    work.append((m, iter(edges.get(m, ()))))
                    advanced = True
                    break
            if not advanced:
                color[node] = BLACK
                work.pop()
                if path and path[-1] == node:
                    path.pop()
    return cycles


def audit(sources: List[Dict[str, Any]], claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    uf, by_id = build_clusters(sources)
    igmap = _index_group_map()
    edges = _citation_edges(by_id)
    cycles = _find_cycles(edges)

    results = []
    for c in claims:
        support = [sid for sid in (c.get("support") or []) if sid in by_id]
        missing = [sid for sid in (c.get("support") or []) if sid not in by_id]
        roots = {}
        primary_roots: Set[str] = set()
        index_groups: Set[str] = set()
        for sid in support:
            r = uf.find(sid)
            roots.setdefault(r, []).append(sid)
            s = by_id[sid]
            if s.get("primary"):
                primary_roots.add(r)
            io = s.get("index_of_origin", "")
            index_groups.add(igmap.get(io, io))

        raw = len(support)
        independent = len(roots)
        echo_ratio = round(raw / independent, 2) if independent else 0.0

        claim_cycles = [cy for cy in cycles if any(sid in cy for sid in support)]

        flags = []
        if len(primary_roots) == 0:
            flags.append("no_primary_source")
        elif len(primary_roots) == 1:
            flags.append("single_primary_origin")
        if independent and echo_ratio >= 2.0:
            flags.append("echo_dominated")
        # only meaningful when there IS real corroboration reached via a single
        # discovery channel (not the normal single-channel case) -> add a channel
        if independent > 1 and len(index_groups) <= 1:
            flags.append("discovery_monoculture")
        if claim_cycles:
            flags.append("circular_citation")

        clusters_out = []
        for root, members in sorted(roots.items(), key=lambda kv: -len(kv[1])):
            rep = next((m for m in members if by_id[m].get("primary")), members[0])
            clusters_out.append({
                "representative": rep,
                "representative_url": by_id[rep].get("url", ""),
                "domain": by_id[rep].get("domain", ""),
                "index_of_origin": by_id[rep].get("index_of_origin", ""),
                "primary": bool(by_id[rep].get("primary")),
                "member_count": len(members),
                "members": members,
            })

        results.append({
            "id": c.get("id"),
            "text": c.get("text", ""),
            "raw_mentions": raw,
            "independent_sources": independent,
            "echo_ratio": echo_ratio,
            "primary_origins": len(primary_roots),
            "index_groups": sorted(index_groups),
            "flags": flags,
            "missing_support": missing,
            "clusters": clusters_out,
            "cycles": claim_cycles,
        })

    return {
        "summary": {
            "claims": len(claims),
            "sources": len(sources),
            "global_cycles": cycles,
            "flagged_claims": [r["id"] for r in results if r["flags"]],
        },
        "claims": results,
    }


def audit_markdown(report: Dict[str, Any]) -> str:
    out = ["# Provenance audit\n"]
    s = report["summary"]
    out.append("Sources: %d | Claims: %d | Flagged: %d\n" %
               (s["sources"], s["claims"], len(s["flagged_claims"])))
    for r in report["claims"]:
        out.append("## %s" % (r["id"]))
        if r["text"]:
            out.append("> %s" % r["text"])
        verdict = "**%d independent source(s)** across %d mention(s)" % (
            r["independent_sources"], r["raw_mentions"])
        if r["echo_ratio"] >= 2.0:
            verdict += "  (echo ratio %sx)" % r["echo_ratio"]
        out.append("- " + verdict)
        out.append("- Primary origins: %d | Discovery index-groups: %s" %
                   (r["primary_origins"], ", ".join(r["index_groups"]) or "none"))
        if r["flags"]:
            out.append("- FLAGS: " + ", ".join(r["flags"]))
        if r["missing_support"]:
            out.append("- Missing support ids (not in sources): " + ", ".join(r["missing_support"]))
        for cl in r["clusters"]:
            tag = "primary" if cl["primary"] else "secondary"
            extra = (" — collapses %d mentions: %s" % (cl["member_count"], ", ".join(cl["members"]))
                     if cl["member_count"] > 1 else "")
            out.append("  - [%s] %s (%s) %s%s" %
                       (tag, cl["representative"], cl["index_of_origin"], cl["domain"], extra))
        for cy in r["cycles"]:
            out.append("  - circular citation: " + " -> ".join(cy))
        out.append("")
    return "\n".join(out)


# ---------- citations ----------

def citation_independence(payload: Dict[str, Any]) -> Dict[str, Any]:
    target = payload.get("target", {})
    citers = payload.get("citers", [])

    t_author_keys = {(_norm_name(a.get("name", "")) or a.get("id", "")).strip()
                     for a in (target.get("authors") or []) if (a.get("name") or a.get("id"))}

    self_citations = 0
    external = []
    for cit in citers:
        c_author_keys = {(_norm_name(a.get("name", "")) or a.get("id", "")).strip()
                         for a in (cit.get("authors") or []) if (a.get("name") or a.get("id"))}
        if t_author_keys & c_author_keys:
            self_citations += 1
        else:
            external.append((c_author_keys, cit))

    # Collapse external citers only when they SHARE AN AUTHOR (a genuine correlation).
    # Sharing a bare institution ("MIT") is NOT an echo — many independent groups sit
    # at the same big institution — so institution-merge was removed (it fabricated
    # false "NOT independent" verdicts).
    uf = UnionFind()
    idx = {i: i for i in range(len(external))}
    for i in idx:
        uf.add(str(i))
    author_to_i: Dict[str, int] = {}
    for i, (aks, _c) in enumerate(external):
        for ak in aks:
            if ak in author_to_i:
                uf.union(str(i), str(author_to_i[ak]))
            else:
                author_to_i[ak] = i

    groups = {}
    for i in idx:
        groups.setdefault(uf.find(str(i)), []).append(i)

    total = len(citers)
    independent = len(groups)
    return {
        "total_citers": total,
        "self_citations": self_citations,
        "self_citation_rate": round(self_citations / total, 3) if total else 0.0,
        "independent_citer_groups": independent,
        "verdict": _citation_verdict(total, self_citations, independent),
    }


def _citation_verdict(total: int, self_c: int, independent: int) -> str:
    if total == 0:
        return "no citers provided"
    if independent <= 1:
        return "NOT independent: all external citations trace to one author/lab (echo)"
    if self_c / total >= 0.4:
        return "high self-citation (>=40%): treat citation count with caution"
    return "%d independent citing groups (of %d citers, %d self-citations)" % (
        independent, total, self_c)


# ---------- cli ----------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Provenance / independence graph.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("audit", help="independence audit over {claims, sources}")
    a.add_argument("bundle", nargs="?", help="bundle JSON with claims+sources")
    a.add_argument("--sources", help="sources JSONL/JSON")
    a.add_argument("--claims", help="claims JSON")
    a.add_argument("--json", action="store_true")

    c = sub.add_parser("citations", help="citation-independence for one paper")
    c.add_argument("citers", help="JSON {target, citers}")
    c.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "audit":
        if args.bundle:
            with open(args.bundle, "r", encoding="utf-8") as fh:
                obj = json.load(fh)
            sources = obj.get("sources", [])
            claims = obj.get("claims", [])
        elif args.sources and args.claims:
            sources = load_sources(args.sources)
            claims = load_claims(args.claims)
        else:
            ap.error("audit needs BUNDLE.json or both --sources and --claims")
            return 2
        report = audit(sources, claims)
        if args.json:
            json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            sys.stdout.write(audit_markdown(report) + "\n")
        return 0

    if args.cmd == "citations":
        with open(args.citers, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        result = citation_independence(payload)
        if args.json:
            json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
        else:
            sys.stdout.write("# Citation independence\n\n")
            for k, v in result.items():
                sys.stdout.write("- %s: %s\n" % (k, v))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
