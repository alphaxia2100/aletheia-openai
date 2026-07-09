#!/usr/bin/env python3
"""URL canonicalization + registrable-domain extraction for source dedup.

Standalone importable util used by provenance_graph.py. Also runnable:
    python3 dedupe.py < sources.jsonl   # adds canonical_url + domain, prints JSONL

Registrable-domain uses `tldextract` if installed (correct), else a curated
multi-label-suffix heuristic. Pure stdlib otherwise.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from typing import Any, Dict, List, Optional

# Tracking params to drop when canonicalizing.
_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"ref", "ref_src", "ref_url", "fbclid", "gclid", "mc_cid", "mc_eid",
                  "igshid", "source", "spm", "yclid", "_hsenc", "_hsmi"}

# Curated multi-label public suffixes (heuristic; install tldextract for the full PSL).
_MULTI_SUFFIXES = {
    "co.uk", "ac.uk", "gov.uk", "org.uk", "me.uk", "co.jp", "ac.jp", "go.jp",
    "co.kr", "com.au", "net.au", "org.au", "edu.au", "gov.au", "co.nz", "co.in",
    "ac.in", "co.za", "com.br", "com.cn", "com.mx", "com.tr", "com.sg", "com.hk",
    "com.tw", "com.ar", "com.sa", "co.il", "org.il", "ac.il", "edu.cn", "gov.cn",
}

try:  # optional correctness upgrade
    import tldextract as _tldextract  # type: ignore
except Exception:  # noqa: BLE001
    _tldextract = None


def registrable_domain(host_or_url: str) -> str:
    host = host_or_url.strip().lower()
    if "://" in host or host.startswith("//"):
        host = urllib.parse.urlparse(host if "://" in host else "http:" + host).netloc
    host = host.split("@")[-1].split(":")[0]  # strip creds/port
    if not host:
        return ""
    if _tldextract is not None:
        ext = _tldextract(host)
        return ".".join(p for p in (ext.domain, ext.suffix) if p)
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    last2 = ".".join(labels[-2:])
    last3 = ".".join(labels[-3:])
    if last2 in _MULTI_SUFFIXES:
        return ".".join(labels[-3:])
    if last3 in _MULTI_SUFFIXES:  # rare 3-label suffix
        return ".".join(labels[-4:])
    return last2


def canonical_url(url: str) -> str:
    if not url:
        return ""
    try:
        p = urllib.parse.urlparse(url.strip())
    except Exception:  # noqa: BLE001
        return url.strip()
    scheme = p.scheme.lower() or "https"
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    # drop tracking params
    kept = []
    for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=False):
        kl = k.lower()
        if kl in _TRACKING_KEYS or any(kl.startswith(pre) for pre in _TRACKING_PREFIXES):
            continue
        kept.append((k, v))
    kept.sort()
    query = urllib.parse.urlencode(kept)
    path = p.path.rstrip("/") if p.path != "/" else "/"
    rebuilt = urllib.parse.urlunparse((scheme, host, path, "", query, ""))
    return rebuilt


def annotate(record: Dict[str, Any]) -> Dict[str, Any]:
    url = record.get("url", "") or ""
    record["canonical_url"] = canonical_url(url)
    record["domain"] = registrable_domain(url)
    return record


def _primary_author_key(record: Dict[str, Any]) -> str:
    authors = record.get("authors") or []
    if authors:
        a0 = authors[0]
        if isinstance(a0, dict):
            return (a0.get("id") or a0.get("name") or "").strip().lower()
        return str(a0).strip().lower()
    # tolerate a singular "author" string
    single = record.get("author")
    if single:
        return str(single).strip().lower()
    return ""


def voice_key(record: Dict[str, Any]) -> str:
    """A stable key for 'the same voice'. Distinct WORKS must never merge:

    - a DOI identifies a distinct work -> two papers on ONE publisher/journal are
      two voices, not one (this is the fix for the publisher-domain over-merge);
    - a distinct author on a domain is a distinct voice;
    - author-less items (no doi, no author) key on their canonical URL, so two
      distinct anonymous pages on one domain stay distinct voices; genuine
      exact-dups and copy-paste echoes are still collapsed downstream by
      build_clusters rule 1 (canonical url) and rule 4 (content shingles).

    (canonical_url identity is handled separately in build_clusters, so literal
    duplicates still collapse regardless of this key.)
    """
    doi = (record.get("doi") or "").strip().lower()
    if doi:
        return "doi::" + doi
    author = _primary_author_key(record)
    if author:
        dom = record.get("domain") or registrable_domain(record.get("url", ""))
        return "%s::%s" % (dom, author)
    # author-less (common for web scrapes, e.g. Brave records): key on the canonical
    # URL, NOT the bare domain — two distinct anonymous pages on one domain are two
    # voices. True exact-dups / echoes are still collapsed by build_clusters rule 1
    # (canonical url) & rule 4 (content shingles).
    return "url::" + (record.get("canonical_url") or canonical_url(record.get("url", "")))


def _main() -> int:
    n = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        sys.stdout.write(json.dumps(annotate(rec), ensure_ascii=False) + "\n")
        n += 1
    sys.stderr.write("annotated %d records\n" % n)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
