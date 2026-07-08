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

# Platform domains where different authors are different voices (merge only w/ author).
# Includes blogging/social platforms AND academic repositories/aggregators, which
# host many INDEPENDENT authors — merging them by bare domain would wrongly collapse
# distinct works into one "voice".
PLATFORM_DOMAINS = {
    # blogging / social / q&a
    "medium.com", "substack.com", "github.com", "gitlab.com", "youtube.com",
    "youtu.be", "reddit.com", "twitter.com", "x.com", "dev.to", "wordpress.com",
    "blogspot.com", "tumblr.com", "linkedin.com", "facebook.com", "quora.com",
    "stackexchange.com", "stackoverflow.com", "news.ycombinator.com",
    "hashnode.dev", "notion.site", "google.com", "sites.google.com",
    # academic repositories / aggregators (many independent authors)
    "arxiv.org", "doi.org", "semanticscholar.org", "openalex.org", "ssrn.com",
    "biorxiv.org", "medrxiv.org", "researchgate.net", "ncbi.nlm.nih.gov",
    "europepmc.org", "ebi.ac.uk", "nih.gov", "springer.com", "sciencedirect.com",
    "nature.com", "acm.org", "ieee.org", "wiley.com", "tandfonline.com",
    "gutenberg.org", "archive.org", "openlibrary.org",
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
    - otherwise a distinct author on a domain is a distinct voice;
    - only truly undifferentiated same-domain items (no doi, no author) merge by
      domain (e.g. several anonymous posts on one small blog).

    (canonical_url identity is handled separately in build_clusters, so literal
    duplicates still collapse regardless of this key.)
    """
    doi = (record.get("doi") or "").strip().lower()
    if doi:
        return "doi::" + doi
    dom = record.get("domain") or registrable_domain(record.get("url", ""))
    author = _primary_author_key(record)
    if author:
        return "%s::%s" % (dom, author)
    if dom:
        return "dom::" + dom
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
