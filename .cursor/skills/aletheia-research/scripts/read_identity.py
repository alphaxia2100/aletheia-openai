#!/usr/bin/env python3
"""Semantic identity and content-state gate for persisted research reads.

Readability is not identity. A resolver/browser can return a long, plausible document that is not
the candidate requested by the retrieval manifest. This module compares the manifest's expected
identifiers/title with high-confidence identity material in the fetched body before the artifact is
allowed into synthesis.

The gate is deliberately typed rather than binary:

* verified_identifier -- a trusted expected DOI/arXiv/PMID/registry identifier is present;
* verified_title      -- no trusted identifier match, but a high-confidence title matches;
* unverified_identity -- readable content without enough identity evidence (persist, do not cite);
* mismatch            -- a decisive title or strong-identifier conflict (persist, never cite).

Content quality is orthogonal: complete, truncated, blocked, shell, image_only, or unreadable.
"""
from __future__ import annotations

from collections import Counter
import difflib
import hashlib
import html
import re
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urlparse


IDENTITY_STATES = ("verified_identifier", "verified_title", "unverified_identity", "mismatch")
CONTENT_STATES = ("complete", "truncated", "blocked", "shell", "image_only", "unreadable")

_DOI = re.compile(r"(?<![A-Za-z0-9])10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
_ARXIV = re.compile(
    r"(?:arxiv\s*:\s*|arxiv\.org/(?:abs|html|pdf)/)"
    r"((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z-]+)?/\d{7})(?:v\d+)?)",
    re.I,
)
_PMID = re.compile(r"(?:PMID\s*:\s*|pubmed\.ncbi\.nlm\.nih\.gov/)(\d{5,10})", re.I)
_NCT = re.compile(r"\b(NCT\d{8})\b", re.I)
_ISRCTN = re.compile(r"\b(ISRCTN\d{8})\b", re.I)
_YOUTUBE = re.compile(r"(?:youtu\.be/|[?&]v=)([A-Za-z0-9_-]{6,})", re.I)
_REDDIT = re.compile(r"reddit\.com/r/[^/]+/comments/([A-Za-z0-9]+)", re.I)

_BLOCK_MARKERS = (
    "are you a robot", "just a moment", "enable javascript", "captcha",
    "verify you are human", "confirm you are human", "please confirm you are a human", "access denied",
    "checking your browser", "request unsuccessful", "please enable cookies",
    "attention required",
)
_SHELL_MARKERS = ("target url returned error", "no html for", "page not found",
                  "document not found", "content unavailable")
_GENERIC_TITLES = {
    "home", "sign in", "log in", "access denied", "just a moment", "page not found",
    "journal of clinical epidemiology", "researchgate", "semantic scholar", "arxiv",
}
_TITLE_STOP = {
    "a", "an", "and", "article", "for", "from", "full", "in", "of", "on", "pdf",
    "the", "to", "with",
}


def _clean_doi(value: str) -> str:
    value = html.unescape(str(value or "")).strip().lower()
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)", "", value)
    match = _DOI.search(value)
    if not match:
        return ""
    doi = match.group(0).rstrip(".,;:)]}\"").lower()
    # Publisher asset routes commonly append `/asset/...` to a DOI path. That suffix identifies a
    # figure rendition, not a different DOI (observed on ACM full-text pages).
    doi = re.sub(r"/(?:assets?|figures?|images?|metrics|pdf)(?:/.*)?$", "", doi, flags=re.I)
    return doi


def _clean_arxiv(value: str) -> str:
    match = _ARXIV.search(str(value or ""))
    return re.sub(r"v\d+$", "", match.group(1).lower()) if match else ""


def _clean_pmid(value: str) -> str:
    match = _PMID.search(str(value or ""))
    return match.group(1) if match else ""


def _ids_from_values(values: Iterable[str]) -> Dict[str, List[str]]:
    found: Dict[str, set] = {"doi": set(), "arxiv": set(), "pmid": set(), "registry": set()}
    for raw in values:
        value = html.unescape(str(raw or ""))
        for match in _DOI.finditer(value):
            doi = _clean_doi(match.group(0))
            if doi:
                found["doi"].add(doi)
        for match in _ARXIV.finditer(value):
            found["arxiv"].add(re.sub(r"v\d+$", "", match.group(1).lower()))
        for match in _PMID.finditer(value):
            found["pmid"].add(match.group(1))
        found["registry"].update(m.group(1).upper() for m in _NCT.finditer(value))
        found["registry"].update(m.group(1).upper() for m in _ISRCTN.finditer(value))
    return {kind: sorted(vals) for kind, vals in found.items() if vals}


def expected_identifiers(record: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extract strong expected identifiers from manifest fields and the requested URL."""
    values = [record.get("url", ""), record.get("doi", ""), record.get("arxiv_id", ""),
              record.get("pmid", ""), record.get("registry_id", "")]
    ids = _ids_from_values(values)
    # Some adapters provide a bare PMID rather than a labeled value.
    pmid = re.sub(r"\D", "", str(record.get("pmid") or ""))
    if pmid:
        ids.setdefault("pmid", [])
        if pmid not in ids["pmid"]:
            ids["pmid"].append(pmid)
            ids["pmid"].sort()
    return ids


def _strip_markdown(value: str) -> str:
    value = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[`*_~]", "", value)
    return html.unescape(value).strip(" #\t:-|")


def _title_tokens(value: str) -> List[str]:
    value = _strip_markdown(value)
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[0-9])(?=[A-Za-z])", " ", value)
    value = value.replace("_", " ").lower()
    return [token for token in re.findall(r"[a-z0-9]+", value)
            if token not in _TITLE_STOP and len(token) > 1]


def _normalized_title(value: str) -> str:
    return " ".join(_title_tokens(value))


def _candidate_titles(text: str) -> List[Tuple[str, str]]:
    """Return high-confidence (title, evidence-kind) candidates near the document front."""
    front = str(text or "")[:12000]
    lines = front.splitlines()[:140]
    candidates: List[Tuple[str, str]] = []
    for line in lines:
        match = re.match(r"\s*Title\s*:\s*(.+?)\s*$", line, re.I)
        if match:
            candidates.append((_strip_markdown(match.group(1)), "metadata_title"))
        match = re.match(r"\s*<title[^>]*>(.+?)</title>\s*$", line, re.I)
        if match:
            candidates.append((_strip_markdown(match.group(1)), "html_title"))
        match = re.match(r"\s*#\s+(.+?)\s*$", line)
        if match:
            candidates.append((_strip_markdown(match.group(1)), "h1"))
    # Browser extraction occasionally emits a standalone '#' followed by the real article title.
    for idx, line in enumerate(lines[:-1]):
        if line.strip() != "#":
            continue
        for nxt in lines[idx + 1:idx + 12]:
            if re.match(r"\s*##\s+", nxt):
                break
            cleaned = _strip_markdown(nxt)
            if cleaned and not cleaned.lower().startswith("author links"):
                candidates.append((cleaned, "h1_following_line"))
    unique, seen = [], set()
    for title, kind in candidates:
        norm = _normalized_title(title)
        if (len(norm.split()) < 3 or norm in _GENERIC_TITLES or norm in seen
                or "guest editors" in norm or norm.endswith("guidance series")
                or norm.startswith("under creative commons license")):
            continue
        seen.add(norm)
        unique.append((title, kind))
    return unique


def _title_similarity(expected: str, observed: str, expected_truncated: bool = False) -> Dict[str, Any]:
    exp, obs = _title_tokens(expected), _title_tokens(observed)
    if not exp or not obs:
        return {"ratio": 0.0, "jaccard": 0.0, "coverage": 0.0, "prefix": False,
                "match": False, "decisive_mismatch": False}
    exp_s, obs_s = " ".join(exp), " ".join(obs)
    ratio = difflib.SequenceMatcher(None, exp_s, obs_s).ratio()
    exp_set, obs_set = set(exp), set(obs)
    overlap = len(exp_set & obs_set)
    jaccard = overlap / max(len(exp_set | obs_set), 1)
    coverage = overlap / max(min(len(exp_set), len(obs_set)), 1)
    shorter, longer = (exp, obs) if len(exp) <= len(obs) else (obs, exp)
    prefix = len(shorter) >= 5 and longer[:len(shorter)] == shorter
    match = bool(
        exp_s == obs_s
        or ratio >= 0.88
        or (coverage >= 0.85 and jaccard >= 0.65)
        or (prefix and (expected_truncated or len(shorter) / max(len(longer), 1) >= 0.55))
    )
    decisive = bool(len(exp) >= 5 and len(obs) >= 5 and not match
                    and ratio < 0.38 and coverage < 0.35)
    return {"ratio": round(ratio, 3), "jaccard": round(jaccard, 3),
            "coverage": round(coverage, 3), "prefix": prefix, "match": match,
            "decisive_mismatch": decisive}


def _best_title(expected: str, text: str) -> Dict[str, Any]:
    best = {"observed_title": "", "title_evidence": "", "ratio": 0.0, "jaccard": 0.0,
            "coverage": 0.0, "prefix": False, "match": False, "decisive_mismatch": False}
    truncated = str(expected or "").rstrip().endswith(("...", "…"))
    candidates = _candidate_titles(text)
    for observed, evidence in candidates:
        score = _title_similarity(expected, observed, truncated)
        if (score["match"], score["ratio"], score["coverage"]) > \
                (best["match"], best["ratio"], best["coverage"]):
            best = dict(score, observed_title=observed, title_evidence=evidence)
    if candidates and not best["observed_title"]:
        observed, evidence = candidates[0]
        best = dict(_title_similarity(expected, observed, truncated), observed_title=observed,
                    title_evidence=evidence)
    return best


def _trusted_identity_text(text: str) -> str:
    """Restrict identifier evidence to front matter, not a paper's reference list."""
    front = str(text or "")[:8000]
    boundary = re.search(r"(?im)^#{0,3}\s*(references|bibliography|works cited)\s*$", front)
    return front[:boundary.start()] if boundary else front


def _direct_tool_identifier(record: Dict[str, Any], resolved_url: str, method: str) -> Dict[str, List[str]]:
    """Trust IDs returned by tools that address the named object directly, not generic browsers."""
    requested = str(record.get("url") or "")
    resolved = str(resolved_url or requested)
    method_l = str(method or "").lower()
    if "youtube" in method_l and "caption" in method_l:
        left, right = _YOUTUBE.search(requested), _YOUTUBE.search(resolved)
        if left and right and left.group(1) == right.group(1):
            return {"registry": ["YOUTUBE:" + left.group(1)]}
    if "reddit-read" in method_l:
        left, right = _REDDIT.search(requested), _REDDIT.search(resolved)
        if left and right and left.group(1).lower() == right.group(1).lower():
            return {"registry": ["REDDIT:" + left.group(1).lower()]}
    return {}


def assess_identity(record: Dict[str, Any], text: str, resolved_url: str = "",
                    method: str = "") -> Dict[str, Any]:
    expected = expected_identifiers(record)
    lower_front = str(text or "")[:3000].lower()
    if str(method or "").lower() == "blocked" or any(marker in lower_front for marker in _BLOCK_MARKERS):
        return {
            "state": "unverified_identity",
            "reason": "blocked/interstitial content contains no trusted document identity",
            "expected_identifiers": expected,
            "observed_identifiers": {},
            "matched_identifiers": {},
            "conflicting_identifiers": {},
            "expected_title": html.unescape(str(record.get("title") or "")).strip(),
            "observed_title": "",
            "title_evidence": "",
            "title_similarity": {"ratio": 0.0, "jaccard": 0.0, "coverage": 0.0,
                                 "prefix": False, "match": False,
                                 "decisive_mismatch": False},
        }
    observed = _ids_from_values([_trusted_identity_text(text)])
    direct = _direct_tool_identifier(record, resolved_url, method)
    for kind, values in direct.items():
        observed.setdefault(kind, [])
        observed[kind] = sorted(set(observed[kind]) | set(values))

    matched, conflicts = {}, {}
    for kind in sorted(set(expected) | set(observed)):
        exp, obs = set(expected.get(kind, [])), set(observed.get(kind, []))
        if exp & obs:
            matched[kind] = sorted(exp & obs)
        if exp and obs - exp:
            conflicts[kind] = sorted(obs - exp)

    expected_title = html.unescape(str(record.get("title") or "")).strip()
    title = _best_title(expected_title, text) if expected_title else {
        "observed_title": "", "title_evidence": "", "ratio": 0.0, "jaccard": 0.0,
        "coverage": 0.0, "prefix": False, "match": False, "decisive_mismatch": False,
    }

    # A trusted direct-object tool supplies a URL-level identifier even when a transcript/thread body
    # does not repeat the title. Add the corresponding expected registry identity for the comparison.
    if direct and not expected.get("registry"):
        expected = dict(expected)
        expected["registry"] = list(direct.get("registry", []))
        matched["registry"] = list(direct.get("registry", []))

    if title.get("decisive_mismatch"):
        state, reason = "mismatch", "high-confidence fetched title conflicts with manifest title"
    elif matched:
        state, reason = "verified_identifier", "expected identifier occurs in trusted identity material"
    elif title.get("match"):
        state, reason = "verified_title", "normalized manifest and fetched titles match"
    elif conflicts and sum(len(values) for values in observed.values()) == 1:
        state, reason = "mismatch", "single trusted strong identifier conflicts with manifest identifier"
    else:
        state, reason = "unverified_identity", "insufficient trusted identifier or title evidence"

    return {
        "state": state,
        "reason": reason,
        "expected_identifiers": expected,
        "observed_identifiers": observed,
        "matched_identifiers": matched,
        "conflicting_identifiers": conflicts,
        "expected_title": expected_title,
        "observed_title": title.get("observed_title", ""),
        "title_evidence": title.get("title_evidence", ""),
        "title_similarity": {key: title.get(key) for key in
                             ("ratio", "jaccard", "coverage", "prefix", "match",
                              "decisive_mismatch")},
    }


def classify_content(text: str, method: str = "", truncated: bool = False) -> str:
    body = str(text or "")
    lower = body[:3000].lower()
    if str(method or "").lower() == "blocked" or any(marker in lower for marker in _BLOCK_MARKERS):
        return "blocked"
    if not body.strip():
        return "unreadable"
    if any(marker in lower for marker in _SHELL_MARKERS):
        return "shell"
    if truncated:
        return "truncated"
    if "caption" in str(method or "").lower():
        return "complete"
    words = re.findall(r"[A-Za-z][A-Za-z'-]+", _strip_markdown(body))
    images = len(re.findall(r"!\[[^]]*\]\([^)]*\)", body))
    links = len(re.findall(r"\[[^]]+\]\([^)]*\)", body))
    if images >= 3 and len(words) < 120:
        return "image_only"
    if len(body.strip()) < 1500 or (len(words) < 180 and links + images >= 12):
        return "shell"
    return "complete"


def assess_read(record: Dict[str, Any], text: str, resolved_url: str = "", method: str = "",
                truncated: bool = False) -> Dict[str, Any]:
    identity = assess_identity(record, text, resolved_url, method)
    content_state = classify_content(text, method, truncated)
    content_ok = content_state in {"complete", "truncated"}
    identity_ok = identity["state"] in {"verified_identifier", "verified_title"}
    return {
        "identity_state": identity["state"],
        "content_state": content_state,
        "content_ok": content_ok,
        "identity_ok": identity_ok,
        "read_ok": content_ok and identity_ok,
        "identity": identity,
        "content_sha256": hashlib.sha256(str(text or "").encode("utf-8", "replace")).hexdigest(),
    }


def state_counts(rows: Iterable[Dict[str, Any]], field: str) -> Dict[str, int]:
    return dict(sorted(Counter(str(row.get(field) or "unknown") for row in rows).items()))
