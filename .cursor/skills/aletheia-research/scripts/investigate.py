#!/usr/bin/env python3
"""Deep Aletheia — LEAF investigation pipeline (the DOK 1-2 engine).

Given a leaf node (a directory with a focused question + budget), do the full treatment and
write artifacts INTO the node dir:
  route channels -> retrieve (parallel) -> tag class -> dedupe -> authority-rank ->
  class-budgeted read IN FULL -> write sources.jsonl, notes/<h>.md, evidence.md, decisions.

The worker subagent then reads evidence.md/notes and writes findings.md (DOK 2-3: the compressed
claims-with-citations that bubble up). Run standalone it still produces a complete evidence pack.

Usage:
  investigate.py --node NODE_DIR [--query "..."] [--reads K] [--limit 8] [--channels a,b]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.realpath(__file__))
CH = os.path.join(HERE, "..", "..", "channel-retrieval", "scripts")
PROV = os.path.join(HERE, "..", "..", "provenance-audit", "scripts")
for p in (HERE, CH, PROV):
    sys.path.insert(0, p)

import re  # noqa: E402

import treestate  # noqa: E402
import router  # noqa: E402
import rank as rankmod  # noqa: E402
import dedupe  # noqa: E402
import read as readmod  # noqa: E402
import _http  # noqa: E402  (keywordize, for 0-result relaxation)

MAX_READ_CHARS = 40000   #: read cap; a read that hits it is flagged `_truncated` (no silent cut-off)
_ARXIV = re.compile(
    r"arxiv\.org/(?:abs|html|pdf)/((?:[0-9]{4}\.[0-9]{4,5}|[a-z-]+(?:\.[a-z-]+)?/[0-9]{7})(?:v[0-9]+)?)",
    re.I,
)
_STOP = set("the a an of for and or to in on is are be was were with without vs versus more "
            "than better best effect effects does do did how what why which when who into over "
            "real world results side its their your our materially measurably significantly "
            "reduce reduces reduced reducing improve improves improved improving increase increases "
            "increased increasing decrease decreases decreased decreasing affect affects affected "
            "affecting cause causes caused causing impact impacts impacted impacting".split())
#: generic/self-referential terms that never make a useful subject anchor (a topic that is a coined
#: artifact — "the X agent/skill/system" — anchored on these just injects self-reference).
_SELFREF = set("agent agents tool tools skill skills system systems framework frameworks design "
               "designs decision decisions assumption assumptions approach approaches project "
               "projects pipeline pipelines model models itself every core loop".split())
#: generic research/structure meta words — they describe HOW something is studied, not WHAT. On a
#: coined "deep per-component per-step survey" topic these are all that survive the proper-noun/
#: self-ref drop, so anchoring on them prepends pure fragment noise ("deep component step ..."). Dropped.
_META = set("deep survey research study studies review reviews analysis analyses overview summary "
            "comparison comparisons component components step steps phase phases stage stages part "
            "parts section sections aspect aspects factor factors general overall audit self".split())


def _run_topic(node: str) -> str:
    run = treestate._find_run(node)
    cfg = treestate._read_json(os.path.join(run, "run.json"), {}) or {}
    return cfg.get("topic", "") if run else ""


def _proper_nouns(topic: str) -> set:
    """Tokens that look like a PROPER NOUN / coined name in the ORIGINAL topic string — a
    capitalized word that is either not sentence-initial or part of a Capitalized run (e.g.
    'Aletheia Research', 'OpenAI Deep Research'). Anchoring on these returns self-referential junk,
    so they're dropped. Sentence-initial single caps (a Title-cased common noun) are NOT flagged."""
    words = re.findall(r"[A-Za-z][A-Za-z-]*", topic)
    proper = set()
    for i, w in enumerate(words):
        if len(w) >= 4 and w[:1].isupper():
            prev_cap = i > 0 and words[i - 1][:1].isupper()
            next_cap = i + 1 < len(words) and words[i + 1][:1].isupper()
            if i > 0 or prev_cap or next_cap:      # not a lone sentence-initial capital
                proper.add(w.lower())
    return proper


def _subject_terms(topic: str, include_proper: bool = False) -> List[str]:
    """Return an ordered root-topic signature.

    Anchoring defaults to common nouns so coined tool names cannot inject self-reference. Ranking
    opts into proper nouns because named subjects such as Carnegie or the French Revolution are
    often the most discriminating relevance signal.
    """
    proper = _proper_nouns(topic)
    terms = []
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", topic):
        low = raw.lower()
        parts = [p for p in low.split("-") if p]
        is_acronym = raw.isupper() and 2 <= len(raw) <= 10
        is_distinctive_hyphen = "-" in raw and any(
            len(p) >= 4 and p not in _STOP and p not in _SELFREF and p not in _META for p in parts)
        is_common_subject = ("-" not in low and len(low) >= 3 and (include_proper or low not in proper)
                             and low not in _STOP
                             and low not in _SELFREF and low not in _META)
        if (is_acronym or is_distinctive_hyphen or is_common_subject) and low not in terms:
            terms.append(low)
    return terms


def _anchor(question: str, topic: str) -> str:
    """Keep an UNDER-SPECIFIED sub-question tied to the ROOT SUBJECT — a bare leaf like
    'real-world adherence' must still be about *intermittent fasting*, not medication adherence.
    But do NOT anchor when it would only pollute (the audited '_anchor injected Aletheia papers'
    bug): skip if the question already carries the subject or is self-contained, and build the
    anchor from COMMON-NOUN subject terms only (drop proper nouns + generic self-referential words)."""
    if not topic:
        return question
    # Build a compact subject signature in topic order. Named subjects are vital for entity-centered
    # work (Carnegie, NIST, the French Revolution). Exclude them only for prompts that combine a
    # tool/system term WITH research-meta language—the narrow self-referential class that caused
    # Aletheia to search for itself.
    root_tokens = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z-]*", topic)}
    meta_hits = len(root_tokens.intersection(_META))
    self_referential = bool(
        (root_tokens.intersection(_SELFREF) and meta_hits) or meta_hits >= 2)
    subj_terms = _subject_terms(topic, include_proper=not self_referential)
    if not subj_terms:
        return question
    qnorm = re.sub(r"[^a-z0-9]+", " ", question.lower()).strip()
    # A subject mentioned only late in a long orchestration prompt is still lost when keyword APIs
    # compact the query. Treat it as already anchored only when it appears near the front.
    # Keyword APIs compact to roughly six units, so a subject appearing after that window is not
    # operationally front-loaded even if it looks early in a prose sentence.
    early = " ".join(qnorm.split()[:6])
    if any(re.search(r"(?:^|\s)%s(?:\s|$)" % re.escape(
            re.sub(r"[^a-z0-9]+", " ", term).strip()), early) for term in subj_terms[:2]):
        return question
    subj = " ".join(subj_terms[:3])[:60]
    return (subj + " " + question).strip()


def _work_key(r: Dict[str, Any]) -> str:
    """Collapse the SAME work across URL variants so it never eats multiple read slots
    (arXiv abs/html/pdf + vN -> one id; DOI -> one)."""
    url = r.get("url", "") or ""
    m = _ARXIV.search(url)
    if m:
        return "arxiv:" + re.sub(r"v\d+$", "", m.group(1).lower())
    doi = dedupe.doi_from_record(r)
    if doi:
        return "doi:" + doi
    return "url:" + dedupe.canonical_url(url)


def _strong_keys(r: Dict[str, Any]) -> set[str]:
    """Return every work-level identifier present; one record may carry arXiv + DOI aliases."""
    keys: set[str] = set()
    doi = dedupe.doi_from_record(r)
    if doi:
        keys.add("doi:" + doi)
    m = _ARXIV.search(str(r.get("url") or ""))
    if m:
        keys.add("arxiv:" + re.sub(r"v\d+$", "", m.group(1).lower()))
    pmid = str(r.get("pmid") or "").strip()
    if not pmid:
        m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", str(r.get("url") or ""), re.I)
        pmid = m.group(1) if m else ""
    if pmid:
        keys.add("pmid:" + re.sub(r"\D", "", pmid))
    return keys


def _strong_key(r: Dict[str, Any]) -> str:
    """Backward-compatible single identity view; internal dedup uses all aliases."""
    keys = _strong_keys(r)
    return sorted(keys)[0] if keys else ""


def _title_info(r: Dict[str, Any]) -> tuple[str, bool]:
    """Normalize title decorations while retaining whether an index visibly truncated the title."""
    raw = str(r.get("title") or "").strip()
    truncated = raw.endswith(("...", "…"))
    title = raw.lower()
    title = re.sub(r"^\s*(?:\[[^]]+\]|\(pdf\)|pdf\s*[:\-]?|full article\s*[:\-]?)\s*", "", title)
    # Search engines commonly decorate the real title with the index, publisher, or author line.
    # Only strip recognizable templates; arbitrary subtitles remain part of the identity.
    title = re.sub(r"\s*[|]\s*(?:request pdf|semantic scholar)\s*$", "", title)
    title = re.sub(
        r"\s+-\s+(?:fingerprint(?:\s+-\s+.*)?|pmc|pubmed|sciencedirect|sleep health(?::.*)?)\s*$",
        "", title)
    title = re.sub(r"\s+-\s+[^-]{1,160},\s*(?:19|20)\d{2}\s*$", "", title)
    title = re.sub(r":\s*[^:]{3,100}:\s*vol\s+\d+.*$", "", title)
    title = re.sub(r"(?:\.{3}|…)\s*$", "", title)
    words = [w for w in re.findall(r"[a-z0-9]+", title) if w not in {"pdf", "full", "article"}]
    return (" ".join(words) if len(words) >= 5 else "", truncated)


def _title_key(r: Dict[str, Any]) -> str:
    """Conservative normalized-title key for cross-domain copies lacking shared identifiers."""
    return _title_info(r)[0]


def _titles_match(a: tuple[str, bool], b: tuple[str, bool]) -> bool:
    """Match exact cleaned titles, plus explicit search-result truncations of >=8 words."""
    a_key, a_truncated = a
    b_key, b_truncated = b
    if not a_key or not b_key:
        return False
    if a_key == b_key:
        return True
    a_words, b_words = a_key.split(), b_key.split()
    if len(a_words) <= len(b_words):
        short, long, visibly_cut = a_words, b_words, a_truncated
    else:
        short, long, visibly_cut = b_words, a_words, b_truncated
    return visibly_cut and len(short) >= 8 and long[:len(short)] == short


def _strong_conflict(strong: set[str], identities: set[str]) -> bool:
    """Different IDs of the same kind prove distinct works; DOI-vs-PMID does not."""
    if not strong:
        return False
    new_by_kind: Dict[str, set] = {}
    old_by_kind: Dict[str, set] = {}
    for value in strong:
        new_by_kind.setdefault(value.split(":", 1)[0], set()).add(value)
    for value in identities:
        old_by_kind.setdefault(value.split(":", 1)[0], set()).add(value)
    shared = new_by_kind.keys() & old_by_kind.keys()
    if any(new_by_kind[k] & old_by_kind[k] for k in shared):
        return False  # one matching typed identity proves equivalence, even if metadata conflicts
    return bool(shared)


def _dedupe_records(records: List[Dict[str, Any]], existing: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Deduplicate exact works and conservative title copies while preserving distinct strong IDs.

    This closes the read-budget leak where arXiv and ResearchGate variants of one paper consumed two
    slots. Equal long titles merge when either copy lacks a strong ID; two different DOI/arXiv/PMID
    values remain distinct even if their titles happen to match.
    """
    strong_seen, weak_seen = set(), set()
    title_clusters: List[Dict[str, Any]] = []

    def remember(r: Dict[str, Any]) -> None:
        strong = _strong_keys(r)
        if strong:
            strong_seen.update(strong)
        else:
            weak_seen.add(_work_key(r))
        title = _title_info(r)
        if not title[0]:
            return
        for cluster in title_clusters:
            if _titles_match(title, cluster["title"]) and not _strong_conflict(strong, cluster["ids"]):
                if strong:
                    cluster["ids"].update(strong)
                return
        title_clusters.append({"title": title, "ids": set(strong)})

    for row in existing or []:
        remember(row)

    out = []
    for row in records:
        strong, weak, title = _strong_keys(row), _work_key(row), _title_info(row)
        duplicate = bool(strong & strong_seen) or bool(not strong and weak in weak_seen)
        matched_cluster = None
        for cluster in title_clusters:
            if _titles_match(title, cluster["title"]) and not _strong_conflict(strong, cluster["ids"]):
                matched_cluster = cluster
                duplicate = True
                break
        if duplicate:
            # Record a newly discovered cross-index alias even when this copy is not returned.  That
            # lets a later, genuinely different DOI with the same generic title pass the veto.
            if matched_cluster is not None and strong:
                matched_cluster["ids"].update(strong)
            continue
        out.append(row)
        remember(row)
    return out


def _search(mod: str, q: str, n: int, t: float):
    return getattr(importlib.import_module(mod), "search")(q, n, t)


DISPATCH = {
    "brave": lambda q, n, t: _search("brave", q, n, t),
    "marginalia": lambda q, n, t: _search("web_marginalia", q, n, t),
    "duckduckgo": lambda q, n, t: _search("web_ddg", q, n, t),
    "openalex": lambda q, n, t: _search("openalex", q, n, t),
    "arxiv": lambda q, n, t: _search("arxiv", q, n, t),
    "hackernews": lambda q, n, t: _search("hn", q, n, t),
    "stackexchange": lambda q, n, t: _search("stackexchange", q, n, t),
    "github": lambda q, n, t: _search("github", q, n, t),
    "reddit": lambda q, n, t: importlib.import_module("reddit").search(q, n, t),
    "europepmc": lambda q, n, t: _search("europepmc", q, n, t),          # biomed/clinical primary
    "wikipedia": lambda q, n, t: _search("wikipedia", q, n, t),          # orientation / humanities
    "openlibrary": lambda q, n, t: _search("openlibrary", q, n, t),      # books / catalog leads
    "crossref": lambda q, n, t: _search("crossref", q, n, t),            # DOI metadata / references
    "semanticscholar": lambda q, n, t: _search("semanticscholar", q, n, t),  # CS/ML citation graph
    "googlebooks": lambda q, n, t: _search("googlebooks", q, n, t),      # books / history / humanities
    "gutenberg": lambda q, n, t: _search("gutendex", q, n, t),           # public-domain full texts
    "youtube": lambda q, n, t: [{"index_of_origin": "youtube",
                                 "url": "https://www.youtube.com/watch?v=" + v, "title": ""}
                                for v in importlib.import_module("youtube").yt_search(q, n, t)],
    "x": lambda q, n, t: _search("x", q, n, t),
}


def _cfg_classes() -> Dict[str, Dict[str, Any]]:
    with open(os.path.join(os.path.dirname(CH), "channels.json"), encoding="utf-8") as fh:
        return json.load(fh)["indexes"]


def retrieve(query: str, channels: List[str], limit: int, timeout: float):
    idx = _cfg_classes()
    per, recs = {}, []

    def one(ch):
        start = time.time()
        used = query
        try:
            out = DISPATCH[ch](query, limit, timeout) or []
            # 0-result relaxation: many free indexes AND their terms, so a long compound query returns
            # NOTHING (the audited AND-cliff). On a TRUE zero, retry with progressively fewer MOST-
            # SALIENT terms until non-empty — capped at 2 retries, and never when the query already
            # returned results (so it can't broaden a working query into noise).
            if not out and len(query.split()) > 3:
                for k in (3, 2):
                    relaxed = _http.keywordize(query, k)
                    if len(relaxed.split()) >= len(used.split()):
                        continue
                    used = relaxed
                    out = DISPATCH[ch](relaxed, limit, timeout) or []
                    if out:
                        break
            for r in out:
                r.setdefault("_channel", ch)
            return ch, out, time.time() - start, None, used
        except Exception as e:  # noqa: BLE001
            return ch, [], time.time() - start, "%s: %s" % (type(e).__name__, str(e)[:80]), query

    with ThreadPoolExecutor(max_workers=max(len(channels), 1)) as ex:
        for f in as_completed([ex.submit(one, c) for c in channels]):
            ch, out, dt, err, used = f.result()
            per[ch] = {"n": len(out), "latency_s": round(dt, 2), "error": err}
            if used != query:                      # surface that this channel needed relaxation
                per[ch]["relaxed_to"] = used
            recs += out
    for r in recs:
        meta = idx.get(r.get("index_of_origin") or r.get("_channel"), {})
        r["_class"] = r.get("channel_class") or meta.get("class", "?")
        r["_index_group"] = meta.get("index_group", r.get("_channel"))
    return recs, per


def _save_read(node: str, url: str, text: str, method: str, truncated: bool = False,
               resolved_url: str = "") -> str:
    d = os.path.join(node, "notes")
    os.makedirs(d, exist_ok=True)
    h = hashlib.sha1(url.encode()).hexdigest()[:10]
    path = os.path.join(d, h + ".md")
    trunc = " TRUNCATED at %d chars — re-read with a larger cap if a claim rests on the tail" % \
        MAX_READ_CHARS if truncated else ""
    resolved = " resolved=%s" % resolved_url if resolved_url and resolved_url != url else ""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("<!-- %s (via %s)%s%s -->\n\n%s" % (url, method, resolved, trunc, text))
    return path


def _read_source(url: str, timeout: float):
    """Read a source, resolving arXiv abstract pages to full HTML then PDF.

    A 9KB arXiv metadata/abstract page previously passed the generic character threshold and was
    mislabeled "read in full." For `/abs/` URLs, only a successful HTML/PDF body is accepted.
    """
    if "youtube.com/" in (url or "") or "youtu.be/" in (url or ""):
        youtube = importlib.import_module("youtube")
        text = youtube.captions(youtube.video_id(url))
        if not text.strip():
            raise RuntimeError("empty YouTube caption transcript for %s" % url)
        # A short video can have a complete transcript below the general 1,500-character evidence
        # threshold. Return the captions anyway so the caller can mark it as a short read; never
        # fall through to Jina's generic video page and mistake navigation chrome for full evidence.
        return text, "youtube captions full-text", url

    m = _ARXIV.search(url or "")
    candidates = [url]
    is_abs = bool(m and "/abs/" in (url or "").lower())
    if is_abs:
        aid = m.group(1)
        candidates = ["https://arxiv.org/html/" + aid, "https://arxiv.org/pdf/" + aid]
    last_error = None
    for candidate in candidates:
        try:
            text, method = readmod.read_url(candidate, timeout, MAX_READ_CHARS, False)
            if len(text.strip()) < 1500:
                last_error = RuntimeError("short read from %s" % candidate)
                continue
            label = str(method or "read") + (" full-text" if m else "")
            return text, label, candidate
        except Exception as exc:  # noqa: BLE001 - try arXiv PDF after HTML failure
            last_error = exc
    raise last_error or RuntimeError("no readable full text for %s" % url)


def _note_exists(node: str, url: str) -> bool:
    if not url:
        return False
    h = hashlib.sha1(url.encode()).hexdigest()[:10]
    return os.path.exists(os.path.join(node, "notes", h + ".md"))


def _existing_work_keys(node: str) -> set:
    """Work keys already in this node's sources.jsonl (for cross-round node-level dedup)."""
    keys = set()
    p = os.path.join(node, "sources.jsonl")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    try:
                        keys.add(_work_key(json.loads(line)))
                    except ValueError:
                        pass
    return keys


def _existing_records(node: str) -> List[Dict[str, Any]]:
    p = os.path.join(node, "sources.jsonl")
    if not os.path.exists(p):
        return []
    rows = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        rows.append(row)
                except ValueError:
                    pass
    return rows


def _merge_existing_read_metadata(node: str, records: List[Dict[str, Any]]) -> int:
    """Persist a later-round read when the source record was indexed in an earlier round."""
    existing = _existing_records(node)
    updates = [r for r in records if r.get("_read_file")]
    changed = 0
    for old in existing:
        for new in updates:
            if _dedupe_records([new], [old]):       # still present => distinct work
                continue
            for key in ("_read_file", "_read_ok", "_truncated", "_resolved_url"):
                if key in new and old.get(key) != new.get(key):
                    old[key] = new[key]
                    changed += 1
            break
    if changed:
        with open(os.path.join(node, "sources.jsonl"), "w", encoding="utf-8") as fh:
            for row in existing:
                fh.write(json.dumps(row) + "\n")
    return changed


def _run_cfg(node: str) -> Dict[str, Any]:
    run = treestate._find_run(node)
    return (treestate._read_json(os.path.join(run, "run.json"), {}) or {}) if run else {}


def _round_cap(status: Dict[str, Any], cfg: Dict[str, Any]):
    """Bounded tiers spend one scrutiny unit per round; unlimited/max converge without a cap."""
    if cfg.get("thoroughness") in ("unlimited", "max"):
        return None
    unit = max(float(cfg.get("unit", 4) or 4), 1e-9)
    return max(1, int(float(status.get("budget", unit) or unit) // unit))


def investigate(node: str, query: str = "", reads: int = 0, limit: int = 8,
                channels: List[str] = None, timeout: float = 30.0) -> dict:
    """ONE deepening round on a node. The worker calls this repeatedly (round 1 = the node
    question; later rounds = the top gap from reflection), so evidence ACCUMULATES across rounds
    (append to evidence.md, accumulate n_read, bump the rounds counter) — that is where depth
    comes from. Reads/round default to ~one scrutiny unit; the worker sequences the rounds."""
    st = treestate._read_json(os.path.join(node, "status.json"), {}) or {}
    cfg = _run_cfg(node)
    unit = float(cfg.get("unit", 4))
    cap = _round_cap(st, cfg)
    completed_rounds = int(st.get("rounds", 0) or 0)
    if cap is not None and completed_rounds >= cap:
        raise SystemExit("bounded %s leaf exhausted its %d investigation round(s); use a deeper tier "
                         "instead of silently overrunning the requested budget" % (
                             cfg.get("thoroughness", "custom"), cap))
    query = query or st.get("question", "")
    query = _anchor(query, cfg.get("topic", ""))   # keep the leaf tied to the root subject
    round_no = completed_rounds + 1
    prev_read = int(st.get("n_read", 0) or 0)
    reads = reads or max(3, round(unit))           # ~one scrutiny unit per round, not the whole budget
    treestate.set_status(node, state="active")

    # router is only a DEFAULT; the worker may override channels after seeing round-1 evidence
    chans = channels or router.route(query, framing=st.get("question", ""), enabled_only=True)["channels"]
    treestate.log_decision(node, "investigate", "round %d channels=%s" % (round_no, ",".join(chans)),
                           "router category=%s (default; worker may override)" % router.classify(query))

    recs, per = retrieve(query, chans, limit, timeout)
    # dedupe at the WORK level (arXiv id / DOI / canonical url) so versions don't duplicate
    uniq = _dedupe_records(recs)
    root_topic = cfg.get("topic", "")
    subject_terms = _subject_terms(root_topic, include_proper=True)[:3]
    proper_terms = _proper_nouns(root_topic)
    required_terms = [term for term in subject_terms if term in proper_terms]
    ranked = rankmod.rank(query, uniq, subject_terms=subject_terms,
                          required_subject_terms=required_terms)
    existing = _existing_records(node)
    already_read = [r for r in existing if r.get("_read_ok")]
    # Don't spend read slots re-reading the same work under another domain/title variant.
    read_pool = _dedupe_records(ranked, already_read)
    sel = [r for r in rankmod.select_reads(read_pool, reads) if not _note_exists(node, r.get("url", ""))]
    if not sel and read_pool:
        # SAFE READ FLOOR: a subject-signature bug must not turn clearly relevant results into an
        # ungrounded zero-read round (observed on the Even Realities run), but an actually irrelevant
        # result set should still be allowed to abstain.  Only bypass the subject/entity gate for
        # candidates that already passed the lexical relevance floor; never fall back to arbitrary
        # top-ranked noise merely because some URL exists.
        eligible = [r for r in read_pool
                    if float(r.get("_relnorm", 0) or 0) >= rankmod.REL_READ
                    and str(r.get("url", "")).lower().startswith(("http://", "https://"))
                    and not _note_exists(node, r.get("url", ""))]
        sel = eligible[:max(1, reads)]
        if sel:
            treestate.log_decision(
                node, "investigate",
                "safe read-floor engaged: subject/entity gate returned 0; reading %d candidates "
                "that still passed lexical relevance" % len(sel),
                "recover a grounded round without spending reads on a wholly irrelevant pool")
    treestate.log_decision(node, "investigate",
                           "round %d: retrieved %d -> %d unique; reading %d new" % (
                               round_no, len(recs), len(uniq), len(sel)),
                           "per-channel: %s" % {k: v["n"] for k, v in per.items()})

    # read selected in full
    read_meta = []
    for r in sel:
        u = r.get("url", "")
        if not u.lower().startswith(("http://", "https://")):
            continue
        t0 = time.time()
        try:
            txt, method, resolved_url = _read_source(u, timeout)
            truncated = len(txt) >= MAX_READ_CHARS      # hit the cap -> tail may be missing
            path = _save_read(node, u, txt, method, truncated, resolved_url)
            ok = len(txt.strip()) >= 1500
            r["_read_file"] = os.path.relpath(path, node)
            r["_read_ok"] = ok
            r["_truncated"] = truncated
            r["_resolved_url"] = resolved_url
            read_meta.append({"url": u, "chars": len(txt), "method": method, "ok": ok,
                              "truncated": truncated,
                              "resolved_url": resolved_url,
                              "t": round(time.time() - t0, 1), "title": r.get("title", "")})
        except Exception as e:  # noqa: BLE001
            read_meta.append({"url": u, "chars": 0, "method": "FAIL", "ok": False,
                              "err": type(e).__name__})

    # node-level dedup across rounds: add_sources only deduped the GLOBAL index, so repeated
    # rounds duplicated this node's sources.jsonl and corrupted independence math. Add only
    # work-keys this node hasn't seen yet.
    _merge_existing_read_metadata(node, ranked)
    existing = _existing_records(node)
    new_for_node = _dedupe_records(ranked, existing)
    treestate.add_sources(node, new_for_node)
    _write_evidence(node, query, ranked, sel, per, read_meta, round_no)
    this_ok = sum(1 for m in read_meta if m.get("ok"))
    treestate.set_status(node, state="investigated", n_sources=len(_dedupe_records(_existing_records(node))),
                         n_read=prev_read + this_ok, rounds=round_no)
    return {"node": node, "round": round_no, "query": query, "channels": chans, "unique": len(uniq),
            "reads_ok": this_ok, "reads_total": prev_read + this_ok, "per_channel": per}


def _write_evidence(node, query, ranked, sel, per, read_meta, round_no=1):
    """Append a `## Round N` section to evidence.md so the pack ACCUMULATES across deepening
    rounds (it used to clobber, erasing prior rounds)."""
    path = os.path.join(node, "evidence.md")
    first = round_no <= 1 or not os.path.exists(path)
    lines = []
    if first:
        st = treestate._read_json(os.path.join(node, "status.json"), {}) or {}
        lines += ["# Evidence pack", "", "**Node question:** %s" % (st.get("question", "") or query), ""]
    lines += ["## Round %d — query: %s" % (round_no, query), "",
              "**Channels:** " + ", ".join("%s(%d)" % (k, v["n"]) for k, v in per.items()), "",
              "### Read in full this round (%d)" % len(read_meta), ""]
    rf = {m["url"]: m for m in read_meta}
    for r in sel:
        m = rf.get(r.get("url", ""), {})
        flag = "ok" if m.get("ok") else "MISS(%s)" % m.get("method", "?")
        if m.get("truncated"):
            flag += " ⚠TRUNCATED"
        excerpt = ""
        if r.get("_read_file"):
            try:
                with open(os.path.join(node, r["_read_file"]), encoding="utf-8") as fh:
                    body = fh.read()
                excerpt = " ".join(body.split()[:80])
            except OSError:
                pass
        lines += ["#### [%s] %s" % (r.get("_class", "?"), (r.get("title") or r.get("url"))[:90]),
                  "- url: %s" % r.get("url", ""),
                  "- score=%.3f rel=%.2f authority=%.1f  read=%s (%d ch)" % (
                      r.get("score", 0), r.get("_relnorm", 0), r.get("_authority", 0),
                      flag, m.get("chars", 0)),
                  "", "> " + (excerpt[:600] or "_(no excerpt)_"), ""]
    lines += ["### Other ranked sources this round (not read)", ""]
    for r in ranked:
        if r.get("_read_file") or _note_exists(node, r.get("url", "")):
            continue
        lines.append("- [%.3f][%s] %s — %s" % (r.get("score", 0), r.get("_class", "?"),
                                               (r.get("title") or "")[:70], r.get("url", "")))
    with open(path, "w" if first else "a", encoding="utf-8") as fh:
        fh.write(("" if first else "\n") + "\n".join(lines) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deep Aletheia leaf investigation.")
    ap.add_argument("--node", required=True)
    ap.add_argument("--query", default="")
    ap.add_argument("--reads", type=int, default=0)
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--channels", default="")
    ap.add_argument("--timeout", type=float, default=30.0)
    args = ap.parse_args(argv)
    chans = [c.strip() for c in args.channels.split(",") if c.strip()] or None
    res = investigate(args.node, args.query, args.reads, args.limit, chans, args.timeout)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
