#!/usr/bin/env python3
"""Aletheia correctness tests (stdlib unittest, no deps).

Run: python3 -m unittest discover -s tests   (or: python3 tests/test_aletheia.py)

These lock in the fixes for the independence-math bugs found in review — the
differentiator must never silently return wrong numbers again.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, ".cursor", "skills", "provenance-audit", "scripts"))
sys.path.insert(0, os.path.join(ROOT, ".cursor", "skills", "defensibility-judge", "scripts"))
sys.path.insert(0, os.path.join(ROOT, ".cursor", "skills", "deep-aletheia", "scripts"))
sys.path.insert(0, os.path.join(ROOT, ".cursor", "skills", "channel-retrieval", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "eval"))

import provenance_graph as pg  # noqa: E402
import judge_score as js  # noqa: E402  (eval measurement core: win-rate + judge-trust gate)
import _http  # noqa: E402  (shared channel helpers: keywordize)
import doctor  # noqa: E402  (channel health gate)
import dedupe  # noqa: E402
import rubric  # noqa: E402
import verify  # noqa: E402  (deep-aletheia citation gate)
import score_run  # noqa: E402  (deep-aletheia run scorer)
import treestate  # noqa: E402  (deep-aletheia blackboard)
import investigate  # noqa: E402  (deep-aletheia leaf engine)
import synthesize  # noqa: E402  (deep-aletheia synthesis + gate)
import router  # noqa: E402  (deep-aletheia channel router)


def audit_one(sources, support):
    return pg.audit(sources, [{"id": "c", "text": "t", "support": support}])["claims"][0]


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TestIndependence(unittest.TestCase):
    def test_echo_via_derives_from_collapses_to_one(self):
        srcs = [
            {"id": "s1", "url": "https://a.com/x", "authors": [{"name": "A"}], "derives_from": ["s5"], "primary": False},
            {"id": "s5", "url": "https://anthropic.com/p", "authors": [{"name": "Anthropic"}], "primary": True},
        ]
        r = audit_one(srcs, ["s1", "s5"])
        self.assertEqual(r["independent_sources"], 1)
        self.assertIn("single_primary_origin", r["flags"])

    def test_distinct_publisher_papers_stay_independent(self):
        # P0: two different PLOS papers (different DOIs) must NOT collapse to 1
        srcs = [
            {"id": "p1", "url": "https://journals.plos.org/plosone/article?id=1",
             "doi": "10.1371/journal.pone.0000001", "authors": [{"name": "Team A"}], "primary": True},
            {"id": "p2", "url": "https://journals.plos.org/plosone/article?id=2",
             "doi": "10.1371/journal.pone.0000002", "authors": [{"name": "Team B"}], "primary": True},
        ]
        r = audit_one(srcs, ["p1", "p2"])
        self.assertEqual(r["independent_sources"], 2)

    def test_same_author_same_domain_merges(self):
        srcs = [
            {"id": "a", "url": "https://blog.example/1", "authors": [{"name": "Sam"}], "primary": False},
            {"id": "b", "url": "https://blog.example/2", "authors": [{"name": "Sam"}], "primary": False},
        ]
        self.assertEqual(audit_one(srcs, ["a", "b"])["independent_sources"], 1)

    def test_near_duplicate_syndication_merges_without_annotation(self):
        # P1: same wire story on two domains, NO derives_from -> 1 independent
        text = ("the central bank raised interest rates by fifty basis points citing persistent "
                "inflation across the economy and signaled further tightening ahead next quarter")
        srcs = [
            {"id": "w1", "url": "https://site1.example/a", "title": "Bank raises rates",
             "snippet": text, "authors": [{"name": "AP"}], "primary": False},
            {"id": "w2", "url": "https://site2.example/b", "title": "Bank raises rates",
             "snippet": text, "authors": [{"name": "Wire desk"}], "primary": False},
        ]
        self.assertEqual(audit_one(srcs, ["w1", "w2"])["independent_sources"], 1)

    def test_id_collision_kept_distinct(self):
        # P0: two sources lacking id+url must remain 2 nodes, not overwrite
        srcs = [{"authors": [{"name": "X"}], "snippet": "alpha"},
                {"authors": [{"name": "Y"}], "snippet": "beta"}]
        self.assertEqual(pg.audit(srcs, [])["summary"]["sources"], 2)

    def test_discovery_monoculture_not_fired_on_single_source(self):
        srcs = [{"id": "a", "url": "https://x.example/1", "index_of_origin": "brave", "primary": True}]
        self.assertNotIn("discovery_monoculture", audit_one(srcs, ["a"])["flags"])

    def test_b2_shingle_rule_does_not_merge_distinct_dois(self):
        # B2: identical boilerplate title + empty snippet + DIFFERENT DOIs must stay 2 (false-merge fix)
        title = ("A Very Long Identical Title About The Metabolic Effects Of Prolonged Fasting In "
                 "Healthy Adults Across Multiple Cohorts")
        srcs = [{"id": "p1", "url": "https://j.org/1", "doi": "10.1/a", "title": title, "snippet": "", "primary": True},
                {"id": "p2", "url": "https://j.org/2", "doi": "10.1/b", "title": title, "snippet": "", "primary": True}]
        self.assertEqual(audit_one(srcs, ["p1", "p2"])["independent_sources"], 2)

    def test_b2_same_work_different_notation_still_merges(self):
        # B2 no-over-count control: same arXiv paper via url vs arxiv_id field (shared body) -> 1 origin
        body = ("we present a method that improves retrieval by reranking candidate passages with a "
                "learned model and report consistent gains across several benchmarks and ablations")
        srcs = [{"id": "a", "url": "https://arxiv.org/abs/2101.00001", "title": "Same Paper", "snippet": body,
                 "authors": [{"name": "Alpha"}]},
                {"id": "b", "url": "https://news.example/x", "arxiv_id": "arXiv:2101.00001", "title": "Same Paper",
                 "snippet": body, "authors": [{"name": "Beta"}]}]
        self.assertEqual(audit_one(srcs, ["a", "b"])["independent_sources"], 1)

    def test_matching_arxiv_id_merges_without_shared_text(self):
        # 0.4.2 claim scoring may see abs/html/pdf variants with no common snippet. A matching strong
        # identifier is sufficient identity evidence and must not depend on near-duplicate text.
        srcs = [
            {"id": "a", "url": "https://arxiv.org/abs/2503.13657", "title": ""},
            {"id": "b", "url": "https://arxiv.org/html/2503.13657v2", "title": ""},
        ]
        self.assertEqual(audit_one(srcs, ["a", "b"])["independent_sources"], 1)

    def test_publisher_doi_url_variants_merge_without_metadata(self):
        # 0.4.2 Codex forward test: publisher adapters omitted the doi field, but /doi/abs and
        # /doi/full still name the same work and must not inflate claim independence.
        srcs = [
            {"id": "a", "url": "https://www.tandfonline.com/doi/abs/10.1080/15368378.2024.2327432"},
            {"id": "b", "url": "https://www.tandfonline.com/doi/full/10.1080/15368378.2024.2327432"},
        ]
        self.assertEqual(audit_one(srcs, ["a", "b"])["independent_sources"], 1)

    def test_b3_authorless_distinct_pages_stay_distinct(self):
        # B3: two distinct anonymous pages on ONE domain must be 2 voices (voice_key over-merge fix)
        srcs = [{"id": "a", "url": "https://site.example/one", "title": "First distinct anonymous page"},
                {"id": "b", "url": "https://site.example/two", "title": "Second unrelated anonymous page"}]
        self.assertEqual(audit_one(srcs, ["a", "b"])["independent_sources"], 2)

    def test_b2_title_only_syndication_still_merges(self):
        # review regression: a real wire-story echo (identical long headline, no snippet, no ids,
        # different outlets) must STILL collapse to 1 — must not over-count independence.
        head = ("Central Bank Raises Benchmark Interest Rate By Fifty Basis Points Citing Persistent "
                "Inflation Across The Broader Economy This Quarter")
        srcs = [{"id": "w1", "url": "https://ap.example/a", "title": head, "snippet": "", "authors": [{"name": "AP"}]},
                {"id": "w2", "url": "https://reuters.example/b", "title": head, "snippet": "", "authors": [{"name": "Reuters"}]}]
        self.assertEqual(audit_one(srcs, ["w1", "w2"])["independent_sources"], 1)

    def test_b2_doi_notation_variants_are_same_work(self):
        # review regression: bare DOI vs doi.org URL with trailing slash/query must canonicalize equal
        body = ("this study reports that the intervention lowered the primary endpoint by a modest but "
                "statistically significant margin across the enrolled cohort over twelve months")
        srcs = [{"id": "a", "url": "https://j/a", "doi": "10.1/samework", "title": "Study", "snippet": body},
                {"id": "b", "url": "https://j/b", "doi": "https://doi.org/10.1/samework/", "title": "Study", "snippet": body}]
        self.assertEqual(audit_one(srcs, ["a", "b"])["independent_sources"], 1)


class TestCitations(unittest.TestCase):
    def test_shared_institution_is_not_echo(self):
        # P0: 4 distinct authors all at "MIT" -> 4 independent groups (not an echo)
        payload = {"target": {"authors": [{"name": "T"}]},
                   "citers": [{"authors": [{"name": n, "affiliation": "MIT"}]} for n in "ABCD"]}
        res = pg.citation_independence(payload)
        self.assertEqual(res["independent_citer_groups"], 4)
        self.assertNotIn("NOT independent", res["verdict"])

    def test_shared_author_collapses(self):
        payload = {"target": {"authors": [{"name": "T"}]},
                   "citers": [{"authors": [{"name": "Alice"}]}, {"authors": [{"name": "Alice"}]}]}
        self.assertEqual(pg.citation_independence(payload)["independent_citer_groups"], 1)

    def test_self_citation_counted(self):
        payload = {"target": {"authors": [{"name": "Alice"}]},
                   "citers": [{"authors": [{"name": "Alice"}]}, {"authors": [{"name": "Bob"}]}]}
        self.assertEqual(pg.citation_independence(payload)["self_citations"], 1)


class TestCycles(unittest.TestCase):
    def test_doi_cycle_detected(self):
        srcs = [
            {"id": "x", "doi": "10.1/x", "url": "https://doi.org/10.1/x", "refs": ["10.1/y"], "primary": True},
            {"id": "y", "doi": "10.1/y", "url": "https://doi.org/10.1/y", "refs": ["10.1/x"], "primary": True},
        ]
        rep = pg.audit(srcs, [{"id": "c", "support": ["x", "y"]}])
        self.assertTrue(rep["summary"]["global_cycles"])

    def test_large_chain_no_recursion_error(self):
        # P1: iterative DFS must handle 5000 nodes without RecursionError
        edges = {str(i): {str(i + 1)} for i in range(5000)}
        edges["5000"] = set()
        self.assertEqual(pg._find_cycles(edges), [])


class TestDedupe(unittest.TestCase):
    def test_canonical_url_strips_tracking(self):
        self.assertEqual(dedupe.canonical_url("https://www.Ex.com/a/?utm_source=x&id=5#f"),
                         "https://ex.com/a?id=5")

    def test_registrable_domain_multilabel(self):
        self.assertEqual(dedupe.registrable_domain("https://www.example.co.uk/x"), "example.co.uk")

    def test_voice_key_doi_distinguishes_works(self):
        a = dedupe.voice_key({"doi": "10.1/a", "url": "https://p.org/1"})
        b = dedupe.voice_key({"doi": "10.1/b", "url": "https://p.org/2"})
        self.assertNotEqual(a, b)

    def test_extracts_doi_from_publisher_paths(self):
        self.assertEqual(
            dedupe.doi_from_record({
                "url": "https://www.tandfonline.com/doi/abs/10.1080/15368378.2024.2327432"}),
            "10.1080/15368378.2024.2327432")
        self.assertEqual(
            dedupe.doi_from_record({
                "url": "https://www.frontiersin.org/articles/10.3389/fneur.2025.1699303/full"}),
            "10.3389/fneur.2025.1699303")


class TestDoctor(unittest.TestCase):
    def test_http_auth_error_is_not_healthy(self):
        err = urllib.error.HTTPError("https://example.test", 401, "Unauthorized", {}, None)
        with mock.patch.object(doctor.urllib.request, "urlopen", side_effect=err):
            ok, note = doctor.live("https://example.test", 1)
        self.assertFalse(ok)
        self.assertEqual(note, "HTTP 401")

    def test_invalid_brave_key_is_warn_not_false_green(self):
        with mock.patch.dict(os.environ, {"BRAVE_API_KEY": "invalid"}), \
                mock.patch.object(doctor, "live", return_value=(False, "HTTP 401")):
            row = doctor.p_brave(1)
        self.assertEqual(row[2], "warn")
        self.assertIn("HTTP 401", row[4])


class TestRubric(unittest.TestCase):
    def test_bare_claim_not_defensible(self):
        r = rubric.judge({"claim": "X is best", "falsifier": ""})
        self.assertEqual(r["verdict"], "not yet defensible")

    def test_full_belief_defensible(self):
        belief = {
            "claim": "c",
            "falsifier": "a controlled same-budget comparison showing no difference would sink it",
            "falsifier_search": {"performed": True, "found": "searched, found dissent of a different task type"},
            "evidence": {"independent_sources": 3, "primary": True},
            "steelman": {"opposing_view": "the opposite camp says Y", "why_unconvinced": "their case is a different regime"},
        }
        self.assertTrue(rubric.judge(belief)["verdict"].startswith("defensible"))


class TestVerifyGate(unittest.TestCase):
    """Deep Aletheia's deterministic verify layer certifies RELEVANCE only, never SUPPORT —
    lexical overlap can't see polarity/magnitude, so entailment is the LLM verifier's job.
    Regression for the dogfooded bug: a false "IF doubles fat loss" claim was scored 'supported'
    by lexical overlap alone; the fix is that this layer can NEVER emit 'supported'."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # kill the live-read fallback so tests are hermetic (broken == no readable source)
        self._orig = verify.readmod.read_url
        verify.readmod.read_url = lambda *a, **k: ("", None)

    def tearDown(self):
        verify.readmod.read_url = self._orig

    def _note(self, url, text):
        import hashlib
        h = hashlib.sha1(url.encode()).hexdigest()[:10]
        with open(os.path.join(self.tmp, h + ".md"), "w", encoding="utf-8") as fh:
            fh.write(text)

    def _verdict(self, claim, url):
        return verify.verify_claim(claim, [url], None, self.tmp, 1.0)

    def test_never_emits_supported_even_when_source_says_the_opposite(self):
        claim = "Intermittent fasting is dramatically superior and doubles fat loss."
        # on-topic + heavy word overlap, but the OPPOSITE polarity — lexical can't tell
        self._note("u://a", "Intermittent fasting is not superior; it does not double fat loss. " * 8)
        r = self._verdict(claim, "u://a")
        self.assertEqual(r["verdict"], "relevant")        # relevant, NOT supported
        self.assertNotEqual(r["verdict"], "supported")
        self.assertTrue(r["needs_llm_check"])             # entailment always deferred to the LLM

    def test_off_topic_when_no_overlap(self):
        self._note("u://b", "The migratory patterns of arctic terns span pole to pole. " * 8)
        r = self._verdict("Intermittent fasting beats caloric restriction for fat loss", "u://b")
        self.assertEqual(r["verdict"], "off_topic")

    def test_broken_when_source_unreadable(self):
        r = self._verdict("anything at all here", "u://missing")  # no note + no live read
        self.assertEqual(r["verdict"], "broken")
        self.assertFalse(r["link_works"])

    def test_run_summary_has_no_supported_bucket(self):
        self._note("u://c", "matched calorie intermittent fasting weight loss advantage comparison " * 8)
        out = verify.run([{"claim": "matched calorie intermittent fasting weight loss advantage",
                           "url": "u://c"}], None, self.tmp, 1.0)
        self.assertIn("on_topic_rate", out)
        self.assertEqual(set(out["counts"]), {"relevant", "borderline", "off_topic", "broken"})

    def test_stem_folds_morphological_variants(self):
        # B4: the light stemmer folds inflections so paraphrase overlap is not lost
        self.assertEqual(verify._stem("caloric"), verify._stem("calorie"))   # both -> calor
        self.assertEqual(verify._stem("fasting"), "fast")

    def test_readable_low_overlap_is_borderline_not_offtopic(self):
        # B4: a readable source that shares SOME (stemmed) terms but below the relevant threshold is
        # 'borderline' (still LLM-checked), never a terminal silent 'off_topic'
        claim = ("intermittent fasting substantially outperforms continuous caloric restriction for "
                 "long term adipose reduction in middle aged sedentary overweight adults everywhere")
        self._note("u://bl", "An editorial that only mentions fasting and adults in passing, with no "
                             "comparison, data, effect sizes, or restriction protocol reported here. " * 4)
        r = self._verdict(claim, "u://bl")
        self.assertNotEqual(r["verdict"], "off_topic")            # NOT silently dropped
        self.assertIn(r["verdict"], ("borderline", "relevant"))  # readable + on-topic -> LLM checks it
        self.assertTrue(r["needs_llm_check"])


class TestScoreRunVerdicts(unittest.TestCase):
    """score_run turns the LLM verdicts into citation_accuracy = supported/total, and exposes the
    full breakdown so a caught false claim (contradicted/unsupported) is visible in the score."""

    def _run_with_verify(self, verdicts, cfg=None):
        run = tempfile.mkdtemp()
        with open(os.path.join(run, "run.json"), "w", encoding="utf-8") as fh:
            json.dump(cfg or {"topic": "t", "version": "test"}, fh)
        os.makedirs(os.path.join(run, "tree"))
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            for v in verdicts:
                fh.write(json.dumps({"claim": "c", "verdict": v}) + "\n")
        return run

    def test_citation_accuracy_and_breakdown(self):
        run = self._run_with_verify(["supported", "supported", "contradicted", "unsupported"])
        s = score_run.score(run)
        self.assertEqual(s["citation_accuracy"], 0.5)
        self.assertEqual(s["verdicts"], {"supported": 2, "contradicted": 1, "unsupported": 1,
                                         "off_topic": 0, "broken": 0, "awaiting_llm_check": 0})

    def test_citation_accuracy_is_none_before_llm_pass(self):
        run = self._run_with_verify(["relevant", "relevant", "relevant"])
        s = score_run.score(run)
        self.assertIsNone(s["citation_accuracy"])          # not yet Fact-Checked
        self.assertEqual(s["verdicts"]["awaiting_llm_check"], 3)
        self.assertEqual(s["on_topic_rate"], 1.0)

    def test_offtopic_readable_counts_in_denominator_not_hidden(self):
        # B4: a readable off_topic citation is a FAILED citation, not a non-event — it must stay in
        # the precision denominator so a wrongly-dropped claim can't silently vanish & inflate precision.
        run = self._run_with_verify(["supported", "off_topic"])
        s = score_run.score(run)
        self.assertEqual(s["citation_denominator"], 2)     # supported + off_topic (NOT just supported)
        self.assertEqual(s["citation_precision"], 0.5)     # 1 supported / 2 judged (was 1.0 before the fix)
        self.assertTrue(s["citation_complete"])            # nothing awaiting the LLM
        self.assertEqual(s["citation_accuracy"], 0.5)

    def test_borderline_counts_as_awaiting_llm(self):
        run = self._run_with_verify(["supported", "borderline"])
        s = score_run.score(run)
        self.assertEqual(s["verdicts"]["awaiting_llm_check"], 1)   # borderline still needs the LLM
        self.assertFalse(s["citation_complete"])                   # so the pass is not complete
        self.assertIsNone(s["citation_accuracy"])

    def test_broken_link_blocks_completion(self):
        run = self._run_with_verify(["supported", "broken"])
        s = score_run.score(run)
        self.assertFalse(s["citation_complete"])
        self.assertEqual(s["citation_coverage"], 0.5)
        self.assertIsNone(s["citation_accuracy"])


class TestInvestigateRounds(unittest.TestCase):
    """v0.2 depth: investigate is ONE round that ACCUMULATES across calls (rounds counter, n_read),
    and must NOT duplicate node sources across rounds (the add_sources node-dedup bug)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run = treestate.init_run("intermittent fasting fat loss", budget=8, unit=4,
                                      base=os.path.join(self.tmp, "runs"))
        self.node = os.path.join(self.run, "tree", "root")
        self._orig_retrieve, self._orig_read = investigate.retrieve, investigate.readmod.read_url
        A = {"url": "https://arxiv.org/abs/1234.5678", "title": "Fasting RCT A",
             "index_of_origin": "arxiv", "_class": "evidence"}
        B = {"url": "https://pubmed.ncbi.nlm.nih.gov/111/", "title": "Fasting RCT B",
             "index_of_origin": "openalex", "_class": "evidence"}
        C = {"url": "https://pubmed.ncbi.nlm.nih.gov/222/", "title": "Fasting RCT C",
             "index_of_origin": "openalex", "_class": "evidence"}
        self._calls = {"n": 0}

        def fake_retrieve(q, ch, lim, to):
            self._calls["n"] += 1
            recs = [dict(A), dict(B)] if self._calls["n"] == 1 else [dict(B), dict(C)]  # B repeats
            return recs, {"stub": {"n": len(recs)}}

        investigate.retrieve = fake_retrieve
        investigate.readmod.read_url = lambda *a, **k: ("fasting caloric restriction weight " * 400, "stub")

    def tearDown(self):
        investigate.retrieve, investigate.readmod.read_url = self._orig_retrieve, self._orig_read

    def _node_sources(self):
        p = os.path.join(self.node, "sources.jsonl")
        if not os.path.exists(p):
            return []
        with open(p, encoding="utf-8") as fh:
            return [l for l in fh if l.strip()]

    def test_rounds_accumulate_and_no_source_duplication(self):
        investigate.investigate(self.node, channels=["stub"], reads=2)          # round 1: read A,B
        investigate.investigate(self.node, query="metabolic gap", channels=["stub"], reads=2)  # round 2: B dup, C new
        st = treestate._read_json(os.path.join(self.node, "status.json"), {})
        self.assertEqual(st["rounds"], 2)                       # accumulated, not overwritten
        self.assertEqual(st["n_read"], 3)                      # A,B (r1) + C (r2); B not re-read
        self.assertEqual(len(self._node_sources()), 3)         # A,B,C — B deduped, not duplicated
        ev = read_text(os.path.join(self.node, "evidence.md"))
        self.assertIn("## Round 1", ev)
        self.assertIn("## Round 2", ev)                        # evidence appended, not clobbered


class TestRouterClassify(unittest.TestCase):
    def test_nutrition_routes_to_science_not_products(self):
        self.assertEqual(router.classify(
            "Is intermittent fasting more effective than caloric restriction for fat loss?"),
            "science_medicine_quantitative")

    def test_camera_still_products(self):
        self.assertEqual(router.classify("best budget mirrorless camera 2026"),
                         "products_consumer_lived_experience")


class TestSynthesizeGate(unittest.TestCase):
    """v0.2 back-and-forth: the gate blocks authoring while a child is thin AND unanswered."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.run = treestate.init_run("t", budget=8, unit=4, base=os.path.join(self.tmp, "runs"))
        self.root = os.path.join(self.run, "tree", "root")
        treestate.split_node(self.root, [["a", "qa"], ["b", "qb"]])
        self.ca = os.path.join(self.root, "children", "a")
        self.cb = os.path.join(self.root, "children", "b")
        treestate.write_findings(self.ca, "x" * 200)   # substantial
        treestate.write_findings(self.cb, "y")         # thin (<120)

    def test_thin_unanswered_child_blocks_then_clears(self):
        res = synthesize.synthesis_input(self.root)
        self.assertEqual(res["unresolved"], ["b"])     # b is thin and unanswered -> blocked
        treestate.answer(self.cb, "q1", "specific answer drawn from the child's gathered sources")
        res2 = synthesize.synthesis_input(self.root)
        self.assertEqual(res2["unresolved"], [])       # answered -> gate clears


class TestScoreRunDepth(unittest.TestCase):
    def test_depth_metrics_reported(self):
        run = tempfile.mkdtemp()
        with open(os.path.join(run, "run.json"), "w", encoding="utf-8") as fh:
            json.dump({"topic": "t", "version": "deep-aletheia 0.2.0"}, fh)
        leaf = os.path.join(run, "tree", "root")
        os.makedirs(leaf)
        with open(os.path.join(leaf, "status.json"), "w", encoding="utf-8") as fh:
            json.dump({"qid": "root", "depth": 0, "rounds": 3, "n_read": 9}, fh)
        with open(os.path.join(leaf, "findings.md"), "w", encoding="utf-8") as fh:
            fh.write("substantial findings " * 20)
        d = score_run.score(run)["depth"]
        self.assertEqual(d["rounds_per_leaf"]["max"], 3)       # multi-round leaf visible
        self.assertEqual(d["reads_per_leaf"]["mean"], 9)
        self.assertIn("reads_by_depth", d)


class TestRouterScoping(unittest.TestCase):
    """aletheia-research-accuracy's router scopes channels to the question's domain and EXCLUDES off-topic
    ones (subprocess: avoids a module-name clash with the frozen deep-aletheia `router`)."""

    def _route(self, q):
        r = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "router.py")
        out = subprocess.check_output([sys.executable, r, q, "--json", "--max", "6"], text=True)
        return json.loads(out)

    def _route_env(self, q, **updates):
        r = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "router.py")
        env = dict(os.environ, **updates)
        out = subprocess.check_output([sys.executable, r, q, "--json", "--max", "6"],
                                      text=True, env=env)
        return json.loads(out)

    def test_biomed_routes_to_europepmc_not_arxiv(self):
        c = self._route("does intermittent fasting improve metabolic health and cognition")["channels"]
        self.assertIn("europepmc", c)
        self.assertNotIn("arxiv", c)          # arXiv has ~no clinical content

    def test_sleep_outcomes_route_to_biomed(self):
        c = self._route("do blue-light filters on smartphones improve sleep outcomes")["channels"]
        self.assertIn("europepmc", c)
        self.assertNotIn("arxiv", c)

    def test_cs_routes_to_arxiv_not_europepmc(self):
        c = self._route("how do transformer attention mechanisms scale in large language models")["channels"]
        self.assertIn("arxiv", c)
        self.assertNotIn("europepmc", c)

    def test_security_authentication_routes_to_technical_sources(self):
        r = self._route("do FIDO2 passkeys resist account takeover better than passwords and TOTP")
        self.assertEqual(r["category"], "cs_software")
        self.assertTrue({"github", "stackexchange", "arxiv"} & set(r["channels"]))

    def test_public_library_is_humanities_not_software(self):
        r = self._route("did Carnegie public libraries improve social mobility historically")
        self.assertEqual(r["category"], "humanities_history")
        self.assertIn("wikipedia", r["channels"])
        self.assertIn("openlibrary", r["channels"])
        self.assertNotIn("github", r["channels"])

    def test_urban_policy_is_not_general(self):
        r = self._route("should cities abolish minimum parking requirements through zoning reform")
        self.assertEqual(r["category"], "policy_econ")

    def test_transport_policy_with_health_outcome_stays_policy(self):
        # A live forward test was misrouted to biomed because "trial" + "health" outscored the
        # transport context.  Health can be an outcome without changing the question's domain.
        r = self._route(
            "Did Stockholm congestion pricing causally reduce traffic and emissions, and what "
            "primary evidence shows durable effects on ambient air or health?")
        self.assertEqual(r["category"], "policy_econ")
        self.assertNotIn("europepmc", r["channels"])

    def test_enabled_core_reset_preserves_no_key_routes(self):
        cfg = read_json(os.path.join(ROOT, ".cursor", "skills", "channel-retrieval", "channels.json"))
        self.assertEqual(set(cfg["core_default"]), set(cfg["enabled"]))
        self.assertIn("wikipedia", cfg["enabled"])
        self.assertIn("openlibrary", cfg["enabled"])

    def test_missing_brave_key_uses_two_working_web_fallbacks(self):
        channels = self._route_env("what is consilience", BRAVE_API_KEY="")["channels"]
        self.assertNotIn("brave", channels)
        self.assertIn("duckduckgo", channels)
        self.assertIn("marginalia", channels)

    def test_current_events_can_route_color_channels(self):
        channels = self._route("latest news trends announced today in 2026")["channels"]
        self.assertIn("x", channels)
        self.assertIn("youtube", channels)

    def test_disabled_channels_are_not_routed(self):
        # 0.4.2 dogfood: Semantic Scholar is hidden/disabled in channels.json, so enabled_only=True
        # must not route to it (the old parameter was accepted but ignored, causing a 43s 429 stall).
        c = self._route("how do multi-agent LLM research systems coordinate")["channels"]
        self.assertNotIn("semanticscholar", c)

    def test_products_excludes_academic(self):
        c = self._route("best budget mirrorless camera for a beginner 2026")["channels"]
        self.assertFalse({"arxiv", "openalex", "europepmc"} & set(c))  # no academic on a buying question
        self.assertTrue({"reddit", "hackernews"} & set(c))            # but community IS in scope

    def test_every_route_covers_web_and_is_small(self):
        for q in ("roman empire history", "tesla stock 10-k valuation", "what is consilience"):
            r = self._route(q)
            self.assertTrue(any(w in r["channels"] for w in ("brave", "duckduckgo", "marginalia")))
            self.assertLessEqual(len(r["channels"]), 6)   # scoped, not "all channels"

    def test_b5_word_boundary_match_and_abstain(self):
        # B5: 'gene' must NOT fire biomed inside 'general'; a lone weak/ambiguous signal -> abstain
        self.assertEqual(self._route("a general strategy for launching a company")["category"], "general")
        self.assertEqual(self._route("how to start a startup")["category"], "general")
        # a genuine multi-signal biomed query still routes correctly
        self.assertEqual(self._route("insulin resistance and glucose metabolism in diabetes")["category"],
                         "biomed")

    def test_b5_narrow_single_signal_keeps_domain_primary(self):
        # review regression: a narrow query with ONE strong domain signal must still hit its primary
        # (the earlier abstain<2 wrongly stripped europepmc/arxiv here). europepmc in-scope for biomed.
        self.assertIn("europepmc", self._route("cancer immunotherapy outcomes")["channels"])
        self.assertIn("arxiv", self._route("rust borrow checker explained")["channels"])


class TestAletheia03Thoroughness(unittest.TestCase):
    """Aletheia's thoroughness dial sets the tree budget/caps and records the current version.
    Run via subprocess to avoid a module-name clash with the frozen deep-aletheia `treestate`."""

    T = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "treestate.py")

    def _init(self, tier, base):
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "test topic", "--thoroughness", tier, "--base", base],
            text=True).strip()
        return read_json(os.path.join(run, "run.json"))

    def test_tiers_scale_and_version(self):
        base = tempfile.mkdtemp()
        q, dp = self._init("quick", base), self._init("deep", base)
        self.assertEqual(q["version"], "aletheia-research-accuracy 0.6.0-accuracy.2")
        self.assertEqual(q["thoroughness"], "quick")
        self.assertLess(q["budget"], dp["budget"])            # deeper tier spends more
        self.assertLess(q["max_depth"], dp["max_depth"])      # and splits deeper

    def test_run_records_executable_fingerprint_not_only_version_label(self):
        base = tempfile.mkdtemp()
        first = self._init("quick", base)
        second = self._init("quick", base)
        a, b = first["implementation"], second["implementation"]
        self.assertEqual(a["schema_version"], 1)
        self.assertRegex(a["skill_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(a["channel_config_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(a["runtime_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(a["skill_sha256"], b["skill_sha256"])
        self.assertEqual(a["channel_config_sha256"], b["channel_config_sha256"])
        self.assertEqual(a["runtime_sha256"], b["runtime_sha256"])
        self.assertIn(a["git_dirty"], (True, False, None))
        if a["git_commit"] is not None:
            self.assertRegex(a["git_commit"], r"^[0-9a-f]{40}$")

    def test_default_is_accuracy_with_hard_ceilings(self):
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "test topic", "--base", tempfile.mkdtemp()],
            text=True).strip()
        c = read_json(os.path.join(run, "run.json"))
        self.assertEqual(c["thoroughness"], "accuracy")
        self.assertGreaterEqual(c["budget"], 1_000_000)
        self.assertGreaterEqual(c["max_depth"], 99)
        self.assertEqual(c["limits"], {"max_seconds": 3600.0,
                                       "max_reads_per_round": 40,
                                       "max_read_attempts": 640})
        self.assertEqual(c["verbosity"], "user")              # default audience

    def test_same_topic_initializations_never_share_a_run_directory(self):
        base = tempfile.mkdtemp()
        first = subprocess.check_output(
            [sys.executable, self.T, "init", "same topic", "--slug", "same", "--base", base],
            text=True).strip()
        second = subprocess.check_output(
            [sys.executable, self.T, "init", "same topic", "--slug", "same", "--base", base],
            text=True).strip()
        self.assertNotEqual(first, second)

    def test_invalid_thoroughness_fails_instead_of_running_accuracy(self):
        proc = subprocess.run(
            [sys.executable, self.T, "init", "topic", "--thoroughness", "quik",
             "--base", tempfile.mkdtemp()], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)

    def test_explicit_budget_stays_custom(self):
        # an explicit --budget stays custom rather than becoming the accuracy tier
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "t", "--budget", "32", "--base", tempfile.mkdtemp()],
            text=True).strip()
        c = read_json(os.path.join(run, "run.json"))
        self.assertEqual(c["thoroughness"], "custom")
        self.assertEqual(c["budget"], 32.0)

    def test_verbosity_agent_recorded_and_bundle_has_full_files(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "bundle topic", "--verbosity", "agent",
             "--budget", "8", "--base", base],
            text=True).strip()
        self.assertEqual(read_json(os.path.join(run, "run.json"))["verbosity"], "agent")
        subprocess.check_call([sys.executable, self.T, "findings", "--node",
                               os.path.join(run, "tree", "root"), "--text",
                               "UNIQUE_FINDING_MARKER with a [primary](https://x)"], stdout=subprocess.DEVNULL)
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        out = subprocess.check_output([sys.executable, rep, "bundle", "--run", run], text=True)
        self.assertIn("FULL BUNDLE", out)
        self.assertIn("UNIQUE_FINDING_MARKER", out)           # the actual file content is included verbatim

    def test_bundle_can_write_an_artifact(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "bundle output topic", "--verbosity", "agent", "--base", base],
            text=True).strip()
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        output = os.path.join(run, "bundle.md")
        printed = subprocess.check_output(
            [sys.executable, rep, "bundle", "--run", run, "--output", output], text=True).strip()
        self.assertEqual(printed, os.path.abspath(output))
        self.assertIn("bundle output topic", read_text(output))

    def test_report_score_ships_with_skill(self):
        # 0.4.1 parity: the headline scorer is INSIDE the skill (report.py score) — no repo/eval dep.
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "score topic", "--base", base], text=True).strip()
        os.makedirs(os.path.join(run, "index"), exist_ok=True)
        with open(os.path.join(run, "verify.jsonl"), "w") as fh:
            for v in ("supported", "supported", "off_topic", "relevant"):
                fh.write(json.dumps({"verdict": v}) + "\n")
        with open(os.path.join(run, "tree", "root", "telemetry.jsonl"), "w") as fh:
            fh.write(json.dumps({"event": "candidate_gather", "selection_mode": "agent",
                                 "round": 1, "attempt": 1, "requery": False, "retrieved": 5,
                                 "unique": 5, "eligible": 4}) + "\n")
            fh.write(json.dumps({"event": "candidate_gather", "selection_mode": "agent",
                                 "round": 1, "attempt": 2, "requery": True, "retrieved": 8,
                                 "unique": 7, "eligible": 6}) + "\n")
            fh.write(json.dumps({"event": "investigation_round", "selection_mode": "agent",
                                 "round": 1, "retrieved": 8, "unique": 7, "eligible": 6, "selected": 3,
                                 "read_attempts": 3, "reads_ok": 2, "read_failures": 1,
                                 "floor_engaged": False, "read_seconds": 1.5}) + "\n")
            fh.write(json.dumps({"event": "triage_requery", "selection_mode": "agent"}) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        s = json.loads(subprocess.check_output([sys.executable, rep, "score", "--run", run], text=True))
        self.assertEqual(s["citation_precision"], round(2 / 3, 3))   # off_topic counts in denominator
        self.assertEqual(s["citation_denominator"], 3)
        self.assertFalse(s["citation_complete"])                     # 1 claim still awaiting
        self.assertIsNone(s["citation_accuracy"])
        self.assertEqual(s["runtime"]["rounds_by_selection_mode"], {"agent": 1})
        self.assertEqual(s["runtime"]["reads_ok"], 2)
        self.assertEqual(s["runtime"]["triage_requeries"], 1)
        self.assertEqual(s["runtime"]["retrieval_passes"], 2)
        self.assertEqual(s["runtime"]["candidate_gathers"], 2)
        self.assertEqual(s["runtime"]["retrieved"], 13)       # gathers only; round is not double-counted
        self.assertEqual(s["runtime"]["completed_round_retrieved"], 8)

    def test_runtime_cost_handles_mixed_pre_upgrade_agent_trace(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "mixed telemetry", "--base", base], text=True).strip()
        telemetry = os.path.join(run, "tree", "root", "telemetry.jsonl")
        with open(telemetry, "w", encoding="utf-8") as fh:
            # Round 1 predates candidate_gather telemetry, so its completed-round count is the only
            # available search-cost record. Round 2 is new and must use its gather without doubling.
            fh.write(json.dumps({"event": "investigation_round", "selection_mode": "agent",
                                 "round": 1, "retrieved": 4, "unique": 4, "eligible": 3,
                                 "selected": 2, "read_attempts": 2, "reads_ok": 2}) + "\n")
            fh.write(json.dumps({"event": "candidate_gather", "selection_mode": "agent",
                                 "round": 2, "attempt": 1, "retrieved": 5,
                                 "unique": 5, "eligible": 4}) + "\n")
            fh.write(json.dumps({"event": "investigation_round", "selection_mode": "agent",
                                 "round": 2, "retrieved": 5, "unique": 5, "eligible": 4,
                                 "selected": 2, "read_attempts": 2, "reads_ok": 2}) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        s = json.loads(subprocess.check_output([sys.executable, rep, "score", "--run", run], text=True))
        self.assertEqual(s["runtime"]["rounds"], 2)
        self.assertEqual(s["runtime"]["retrieval_passes"], 2)
        self.assertEqual(s["runtime"]["retrieved"], 9)
        self.assertEqual(s["runtime"]["completed_round_retrieved"], 9)

    def test_runtime_exposes_read_artifacts_outside_engine_telemetry(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "read artifact accounting", "--base", base],
            text=True).strip()
        node = os.path.join(run, "tree", "root")
        notes = os.path.join(node, "notes")
        os.makedirs(os.path.join(notes, "decisive"))
        with open(os.path.join(notes, "engine.md"), "w", encoding="utf-8") as fh:
            fh.write("engine-selected primary")
        with open(os.path.join(notes, "decisive", "manual.md"), "w", encoding="utf-8") as fh:
            fh.write("manually chased primary")
        with open(os.path.join(node, "sources.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"url": "https://engine", "_read_file": "notes/engine.md",
                                 "_read_ok": True}) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        s = json.loads(subprocess.check_output([sys.executable, rep, "score", "--run", run], text=True))
        self.assertEqual(s["runtime"]["read_artifacts"], 2)
        self.assertEqual(s["runtime"]["engine_read_artifacts"], 1)
        self.assertEqual(s["runtime"]["direct_or_manual_read_artifacts"], 1)

    def test_report_score_can_persist_machine_readable_artifact(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "persistent score", "--base", base], text=True).strip()
        claim = {"claim": "c", "url": "https://x"}
        with open(os.path.join(run, "claims.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(claim) + "\n")
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(claim, verdict="supported")) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        subprocess.check_call([sys.executable, rep, "write-brief", "--run", run,
                               "--text", "# Final brief\nSupported claim c."],
                              stdout=subprocess.DEVNULL)
        subprocess.check_call([sys.executable, rep, "audit-claims", "--run", run,
                               "--auditor", "fresh-context-test-verifier"],
                              stdout=subprocess.DEVNULL)
        output = os.path.join(run, "score.json")
        stdout_score = json.loads(subprocess.check_output(
            [sys.executable, rep, "score", "--run", run, "--output", output], text=True))
        self.assertEqual(read_json(output), stdout_score)
        self.assertTrue(stdout_score["citation_complete"])
        self.assertTrue(stdout_score["claim_scope_audit"]["valid"])

    def test_claim_scope_audit_invalidates_after_final_brief_changes(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "scope audit", "--base", base], text=True).strip()
        claim = {"claim": "c", "url": "https://x"}
        with open(os.path.join(run, "claims.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(claim) + "\n")
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(claim, verdict="supported")) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        subprocess.check_call([sys.executable, rep, "write-brief", "--run", run,
                               "--text", "# Audited\nClaim c."], stdout=subprocess.DEVNULL)
        subprocess.check_call([sys.executable, rep, "audit-claims", "--run", run,
                               "--auditor", "fresh-context-test-verifier"],
                              stdout=subprocess.DEVNULL)
        self.assertTrue(json.loads(subprocess.check_output(
            [sys.executable, rep, "score", "--run", run], text=True))["citation_complete"])
        with open(os.path.join(run, "brief.md"), "a", encoding="utf-8") as fh:
            fh.write("\nNew unaudited factual assertion.\n")
        changed = json.loads(subprocess.check_output(
            [sys.executable, rep, "score", "--run", run], text=True))
        self.assertFalse(changed["citation_complete"])
        self.assertIsNone(changed["citation_accuracy"])
        self.assertIn("brief_changed_after_audit", changed["claim_scope_audit"]["reasons"])

    def test_claim_scope_audit_invalidates_after_verdict_changes(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "verdict audit", "--base", base], text=True).strip()
        claim = {"claim": "c", "url": "https://x"}
        with open(os.path.join(run, "claims.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(claim) + "\n")
        verify_path = os.path.join(run, "verify.jsonl")
        with open(verify_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(claim, verdict="unsupported")) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        subprocess.check_call([sys.executable, rep, "write-brief", "--run", run,
                               "--text", "# Audited\nClaim c."], stdout=subprocess.DEVNULL)
        subprocess.check_call([sys.executable, rep, "audit-claims", "--run", run,
                               "--auditor", "fresh-context-test-verifier"],
                              stdout=subprocess.DEVNULL)
        with open(verify_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(claim, verdict="supported")) + "\n")
        changed = json.loads(subprocess.check_output(
            [sys.executable, rep, "score", "--run", run], text=True))
        self.assertFalse(changed["citation_complete"])
        self.assertIsNone(changed["citation_accuracy"])
        self.assertIn("verify_changed_after_audit", changed["claim_scope_audit"]["reasons"])

    def test_claim_scope_accepts_declared_multi_url_claim(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "multi url audit", "--base", base], text=True).strip()
        claim = {"claim": "c", "urls": ["https://unreadable", "https://readable"]}
        with open(os.path.join(run, "claims.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(claim) + "\n")
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"claim": "c", "url": "https://readable",
                                 "verdict": "supported"}) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        subprocess.check_call([sys.executable, rep, "write-brief", "--run", run,
                               "--text", "# Audited\nClaim c."], stdout=subprocess.DEVNULL)
        subprocess.check_call([sys.executable, rep, "audit-claims", "--run", run,
                               "--auditor", "fresh-context-test-verifier"],
                              stdout=subprocess.DEVNULL)
        scored = json.loads(subprocess.check_output(
            [sys.executable, rep, "score", "--run", run], text=True))
        self.assertTrue(scored["citation_complete"])

    def test_claim_scope_refuses_malformed_jsonl_instead_of_skipping_it(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "malformed audit", "--base", base], text=True).strip()
        with open(os.path.join(run, "claims.jsonl"), "w", encoding="utf-8") as fh:
            fh.write('{"claim":"c","url":"https://x"}\nnot-json\n')
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"claim": "c", "url": "https://x",
                                 "verdict": "supported"}) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        subprocess.check_call([sys.executable, rep, "write-brief", "--run", run,
                               "--text", "# Audited\nClaim c."], stdout=subprocess.DEVNULL)
        proc = subprocess.run([sys.executable, rep, "audit-claims", "--run", run,
                               "--auditor", "fresh-context-test-verifier"],
                              capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("claims.jsonl line 2 is invalid JSON", proc.stderr)
        self.assertFalse(os.path.exists(os.path.join(run, "claim_audit.json")))

    def test_legacy_run_keeps_row_only_score_compatibility(self):
        run = tempfile.mkdtemp()
        with open(os.path.join(run, "run.json"), "w", encoding="utf-8") as fh:
            json.dump({"topic": "legacy", "version": "aletheia-research-accuracy 0.4.3"}, fh)
        os.makedirs(os.path.join(run, "tree"))
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"claim": "c", "url": "https://x",
                                 "verdict": "supported"}) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        scored = json.loads(subprocess.check_output(
            [sys.executable, rep, "score", "--run", run], text=True))
        self.assertTrue(scored["citation_complete"])
        self.assertEqual(scored["citation_accuracy"], 1.0)
        self.assertFalse(scored["claim_scope_audit"]["required"])

    def test_broken_citation_blocks_completion(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "broken citation", "--base", base], text=True).strip()
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"claim": "good", "url": "https://good", "verdict": "supported"}) + "\n")
            fh.write(json.dumps({"claim": "bad", "url": "https://dead", "verdict": "broken"}) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        s = json.loads(subprocess.check_output([sys.executable, rep, "score", "--run", run], text=True))
        self.assertFalse(s["citation_complete"])
        self.assertLess(s["citation_coverage"], 1.0)
        self.assertIsNone(s["citation_accuracy"])

    def test_report_scores_independence_over_cited_claim_sources(self):
        # 0.4.2 dogfood: retrieved-hit independence (including unread/off-topic records) was reported
        # as if it were claim support. The headline must instead cluster the finally cited sources.
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "claim independence", "--base", base], text=True).strip()
        idx = os.path.join(run, "index", "sources.jsonl")
        same_title = "Single Agent Systems Outperform Multi Agent Systems Under Equal Token Budgets"
        rows = [
            {"url": "https://arxiv.org/abs/2604.02460", "title": same_title,
             "index_of_origin": "arxiv"},
            {"url": "https://researchgate.net/publication/403529711", "title": "(PDF) " + same_title,
             "index_of_origin": "brave"},
            {"url": "https://arxiv.org/abs/2503.13657", "title": "Why Do Multi-Agent LLM Systems Fail?",
             "index_of_origin": "arxiv"},
            {"url": "https://irrelevant.example/hit", "title": "Unread search hit",
             "index_of_origin": "brave"},
        ]
        with open(idx, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            for url in (rows[0]["url"], rows[1]["url"], rows[2]["url"]):
                fh.write(json.dumps({"claim": "c", "url": url, "verdict": "supported"}) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        s = json.loads(subprocess.check_output([sys.executable, rep, "score", "--run", run], text=True))
        self.assertEqual(s["retrieved_sources"], 4)
        self.assertEqual(s["claim_sources"], 3)
        self.assertEqual(s["independent_origins"], 2)       # arXiv + ResearchGate are one work
        self.assertEqual(s["origin_echo_ratio"], round(1 / 3, 3))

    def test_report_deduplicates_cited_publisher_url_variants(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "publisher variants", "--base", base], text=True).strip()
        urls = [
            "https://www.tandfonline.com/doi/abs/10.1080/15368378.2024.2327432",
            "https://www.tandfonline.com/doi/full/10.1080/15368378.2024.2327432",
        ]
        with open(os.path.join(run, "index", "sources.jsonl"), "w", encoding="utf-8") as fh:
            for url in urls:
                fh.write(json.dumps({"url": url, "title": "Same paper"}) + "\n")
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            for url in urls:
                fh.write(json.dumps({"claim": "c", "url": url, "verdict": "supported"}) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        s = json.loads(subprocess.check_output([sys.executable, rep, "score", "--run", run], text=True))
        self.assertEqual(s["claim_sources"], 1)
        self.assertEqual(s["independent_origins"], 1)

    def test_agent_bundle_includes_nested_reads_and_verification(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "complete bundle", "--base", base], text=True).strip()
        notes = os.path.join(run, "tree", "root", "notes", "full")
        os.makedirs(notes)
        with open(os.path.join(notes, "primary.md"), "w", encoding="utf-8") as fh:
            fh.write("NESTED_PRIMARY_MARKER")
        with open(os.path.join(run, "claims.jsonl"), "w", encoding="utf-8") as fh:
            fh.write('{"claim":"CLAIM_MARKER","url":"https://example"}\n')
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            fh.write('{"claim":"CLAIM_MARKER","url":"https://example","verdict":"supported"}\n')
        with open(os.path.join(run, "score.json"), "w", encoding="utf-8") as fh:
            fh.write('{"citation_complete":true,"score_marker":"SCORE_MARKER"}\n')
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        out = subprocess.check_output([sys.executable, rep, "bundle", "--run", run, "--reads"], text=True)
        self.assertIn("NESTED_PRIMARY_MARKER", out)
        self.assertIn("CLAIM_MARKER", out)
        self.assertIn('"verdict":"supported"', out)
        self.assertIn("SCORE_MARKER", out)

    def test_report_write_brief_emits_deliverable(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "brief topic", "--base", base], text=True).strip()
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        subprocess.check_call([sys.executable, rep, "write-brief", "--run", run, "--text",
                               "# Brief\nMULTIPAGE_MARKER"], stdout=subprocess.DEVNULL)
        self.assertIn("MULTIPAGE_MARKER", read_text(os.path.join(run, "brief.md")))

    def test_run_lifecycle_reaches_complete(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "lifecycle topic", "--budget", "8", "--base", base],
            text=True).strip()
        root = os.path.join(run, "tree", "root")
        subprocess.check_call([sys.executable, self.T, "split", "--node", root, "--children",
                               json.dumps([["a", "qa"], ["b", "qb"]])], stdout=subprocess.DEVNULL)
        with open(os.path.join(run, "run.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["state"], "investigating")
        subprocess.check_call([sys.executable, self.T, "findings", "--node", root,
                               "--text", "root synthesis " * 20], stdout=subprocess.DEVNULL)
        with open(os.path.join(run, "run.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["state"], "synthesized")
        claim = {"claim": "c", "url": "https://x"}
        with open(os.path.join(run, "claims.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(claim) + "\n")
        with open(os.path.join(run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(claim, verdict="supported")) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        subprocess.check_call([sys.executable, rep, "write-brief", "--run", run,
                               "--text", "# Complete"], stdout=subprocess.DEVNULL)
        with open(os.path.join(run, "run.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["state"], "briefed")
        subprocess.check_call([sys.executable, rep, "audit-claims", "--run", run,
                               "--auditor", "fresh-context-test-verifier"],
                              stdout=subprocess.DEVNULL)
        with open(os.path.join(run, "run.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["state"], "complete")

    def test_bundle_survives_corrupt_artifacts(self):
        # review hardening: a non-UTF-8 byte or a non-dict sources line must NOT abort the whole
        # bundle into an empty result — it must degrade gracefully and still return every artifact.
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "corrupt topic", "--budget", "8", "--base", base],
            text=True).strip()
        subprocess.check_call([sys.executable, self.T, "findings", "--node",
                               os.path.join(run, "tree", "root"), "--text", "SURVIVOR_MARKER"],
                              stdout=subprocess.DEVNULL)
        with open(os.path.join(run, "portfolio.md"), "wb") as fh:
            fh.write(b"valid text \xff\xfe then more")        # invalid UTF-8
        with open(os.path.join(run, "tree", "root", "sources.jsonl"), "w") as fh:
            fh.write("123\n" + json.dumps({"url": "https://x", "title": "ok"}) + "\n")  # non-dict line
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts", "report.py")
        out = subprocess.check_output([sys.executable, rep, "bundle", "--run", run], text=True)
        self.assertIn("SURVIVOR_MARKER", out)                 # content survived the corrupt neighbors


class TestAletheiaResearch031(unittest.TestCase):
    """0.3.1 audit fixes: weighted split, resumable frontier, structural independence,
    _anchor de-pollution, biomed authority, code-gated citation coverage. The aletheia-research-accuracy
    scripts share module names with the frozen deep-aletheia baseline imported above, so CLI-level
    checks go through subprocess and Python-level checks load the AR modules under distinct names."""

    AR = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts")

    @classmethod
    def _load(cls, name, fname):
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, os.path.join(cls.AR, fname))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def _tinit(self, base, budget, unit):
        t = os.path.join(self.AR, "treestate.py")
        return subprocess.check_output([sys.executable, t, "init", "topic", "--budget", str(budget),
                                        "--unit", str(unit), "--base", base], text=True).strip()

    def test_weighted_split_conserves_and_floors(self):
        run = self._tinit(tempfile.mkdtemp(), 32, 4)
        root = os.path.join(run, "tree", "root")
        t = os.path.join(self.AR, "treestate.py")
        dirs = subprocess.check_output(
            [sys.executable, t, "split", "--node", root, "--children",
             json.dumps([["a", "qa"], ["b", "qb"], ["c", "qc"]]), "--weights", "[3,1,2]"],
            text=True).split()
        b = [read_json(os.path.join(d, "status.json"))["budget"] for d in dirs]
        self.assertAlmostEqual(sum(b), 32, places=2)      # budget conserved across the split
        self.assertTrue(all(x >= 4 - 1e-9 for x in b))    # every child floored at the scrutiny unit
        self.assertGreater(b[0], b[2])                    # weight 3 > weight 2 ...
        self.assertGreater(b[2], b[1])                    # ... > weight 1 (contestedness-scaled)

    def test_uniform_split_is_the_default(self):
        run = self._tinit(tempfile.mkdtemp(), 12, 4)
        root = os.path.join(run, "tree", "root")
        t = os.path.join(self.AR, "treestate.py")
        dirs = subprocess.check_output(
            [sys.executable, t, "split", "--node", root, "--children",
             json.dumps([["a", "qa"], ["b", "qb"], ["c", "qc"]])], text=True).split()
        b = [read_json(os.path.join(d, "status.json"))["budget"] for d in dirs]
        self.assertEqual(b, [4.0, 4.0, 4.0])              # no weights -> uniform (backward compatible)

    def test_resumable_frontier_repicks_crashed_active_node(self):
        run = self._tinit(tempfile.mkdtemp(), 12, 4)
        root = os.path.join(run, "tree", "root")
        t = os.path.join(self.AR, "treestate.py")
        subprocess.check_call([sys.executable, t, "split", "--node", root, "--children",
                               json.dumps([["a", "qa"], ["b", "qb"]])], stdout=subprocess.DEVNULL)
        ca = os.path.join(root, "children", "a")
        subprocess.check_call([sys.executable, t, "status", "--node", ca, "--set", "active"],
                              stdout=subprocess.DEVNULL)   # simulate a crash mid-round
        plain = subprocess.check_output([sys.executable, t, "frontier", "--run", run,
                                         "--state", "pending"], text=True).split()
        resume = subprocess.check_output([sys.executable, t, "frontier", "--run", run,
                                          "--resumable"], text=True).split()
        self.assertNotIn(ca, plain)                       # plain pending scan silently skips it (the bug)
        self.assertIn(ca, resume)                         # --resumable catches the crashed active node

    def test_structural_independence_catches_echo_voice_key_misses(self):
        syn = self._load("ar_synthesize", "synthesize.py")
        text = ("the agency concluded the additive is safe at current exposure after reviewing the "
                "full toxicological evidence and found no cause to revise the acceptable intake")
        echo = [{"id": "e%d" % i, "url": "https://s%d.example/a" % i, "title": "Agency clears additive",
                 "snippet": text, "authors": [{"name": "Reporter %d" % i}]} for i in range(6)]
        ind = syn.independence(echo)
        self.assertGreaterEqual(ind["voices"], 5)             # voice_key thinks they're independent
        self.assertLessEqual(ind["independent_origins"], 2)   # structural clustering collapses the echo
        self.assertGreaterEqual(ind["origin_echo_ratio"], 0.6)

    def test_structural_independence_keeps_distinct_primaries(self):
        syn = self._load("ar_synthesize", "synthesize.py")
        prim = [{"id": "p%d" % i, "url": "https://journals.plos.org/x?id=%d" % i,
                 "doi": "10.1371/j.%d" % i, "title": "Distinct study %d" % i,
                 "snippet": "a unique finding about cohort %d" % i,
                 "authors": [{"name": "Team %d" % i}], "primary": True} for i in range(6)]
        self.assertEqual(syn.independence(prim)["independent_origins"], 6)

    def test_synthesis_skips_corrupt_jsonl_records(self):
        syn = self._load("ar_synthesize_corrupt_compat", "synthesize.py")
        node = tempfile.mkdtemp()
        os.makedirs(os.path.join(node, "children"))
        with open(os.path.join(node, "status.json"), "w", encoding="utf-8") as fh:
            json.dump({"qid": "root", "question": "q"}, fh)
        with open(os.path.join(node, "sources.jsonl"), "w", encoding="utf-8") as fh:
            fh.write("not-json\n")
            fh.write(json.dumps({"url": "https://valid.example", "_read_ok": True}) + "\n")
        ind = syn.synthesis_input(node)["independence"]
        self.assertEqual(ind["n"], 1)
        self.assertEqual(ind["retrieved_n"], 1)

    def test_subtree_independence_counts_same_source_once(self):
        # A source may be useful to two branches. Root synthesis must not emit a duplicate-ID warning
        # or count two retrieval instances as two items merely because both children retained it.
        syn = self._load("ar_synthesize_cross_branch_042", "synthesize.py")
        source = {"id": "brav-same", "url": "https://example.org/study", "title": "One study"}
        ind = syn.independence([source, dict(source)])
        self.assertEqual(ind["n"], 1)
        self.assertEqual(ind["independent_origins"], 1)

    def test_anchor_skips_proper_noun_and_self_contained(self):
        inv = self._load("ar_investigate", "investigate.py")
        # proper-noun / coined topic must NOT be prepended (the self-referential-Aletheia bug)
        self.assertEqual(inv._anchor("multi-agent tree vs single-agent loop",
                                     "the Aletheia Research deep-survey agent"),
                         "multi-agent tree vs single-agent loop")
        # but a bare leaf on a common-noun topic still gets anchored to the subject
        self.assertIn("fasting", inv._anchor("real-world adherence", "intermittent fasting fat loss"))

    def test_b6_anchor_prefers_specific_terms_and_drops_meta_fragments(self):
        inv = self._load("ar_investigate", "investigate.py")
        topic = "Aletheia Research 0.3.1 deep per-component per-step self-audit"
        # short question on a coined/meta topic -> UNCHANGED (no "deep component step" fragment noise)
        self.assertEqual(inv._anchor("adherence over time", topic), "adherence over time")
        # keeps the 2 most-specific (longest) subject words, drops generic meta words
        out = inv._anchor("dropout rates", "reinforcement learning curricula deep study analysis")
        self.assertIn("reinforcement", out)
        self.assertIn("curricula", out)
        self.assertNotIn("study", out)      # generic meta word, dropped
        self.assertNotIn("analysis", out)

    def test_anchor_keeps_distinctive_root_subject_on_long_adversary_question(self):
        # 0.4.2 dogfood: a long adversary leaf was incorrectly treated as self-contained and drifted
        # into graph theory/macro because it omitted the root's distinctive "LLM" subject.
        inv = self._load("ar_investigate_anchor_042", "investigate.py")
        root = ("Do multi-agent LLM research systems improve breadth and accuracy over single-agent "
                "systems, and what coordination failures erase those gains?")
        leaf = ("What are the strongest empirical and practitioner counterexamples to the leading "
                "conditional-complementarity framing, and which coordination failures erase gains?")
        self.assertIn("llm", inv._anchor(leaf, root).lower())

    def test_anchor_promotes_late_subject_before_api_compaction(self):
        inv = self._load("ar_investigate_late_anchor_043", "investigate.py")
        root = "Are synced passkeys more phishing-resistant than passwords plus app-based TOTP?"
        leaf = ("What do primary standards and security research establish about whether synced "
                "passkeys resist phishing better than TOTP? Hunt the decisive source.")
        anchored = inv._anchor(leaf, root).lower()
        self.assertTrue(anchored.startswith("synced passkeys phishing-resistant "))

    def test_named_history_subject_survives_anchor_and_rank_focus(self):
        inv = self._load("ar_investigate_named_subject_043", "investigate.py")
        rk = self._load("ar_rank_named_subject_043", "rank.py")
        carnegie = "How did Carnegie public libraries affect social mobility in the United States, 1890-1920?"
        self.assertEqual(inv._subject_terms(carnegie, include_proper=True)[:3],
                         ["carnegie", "public", "libraries"])
        anchored = inv._anchor("economic causes and political conflict", "What caused the French Revolution?")
        self.assertTrue(anchored.lower().startswith("french revolution"))
        leaf = ("What causal and archival evidence measures how Carnegie public libraries affected "
                "education and occupational mobility?")
        self.assertTrue(inv._anchor(leaf, carnegie).lower().startswith("carnegie public libraries "))
        rows = [
            {"url": "https://history.example/carnegie", "title": "Carnegie Public Libraries and Social Mobility",
             "snippet": "historical evidence", "_class": "evidence", "primary": True},
            {"url": "https://example.org/catalog", "title": "Methods for Library Catalog Maintenance",
             "snippet": "software system migration", "_class": "evidence"},
        ]
        selected = rk.select_reads(rk.rank(
            carnegie, rows, subject_terms=inv._subject_terms(carnegie, include_proper=True)[:3],
            required_subject_terms=["carnegie"]), 2)
        self.assertEqual([row["url"] for row in selected], ["https://history.example/carnegie"])

    def test_cross_domain_title_duplicate_uses_one_read_slot(self):
        inv = self._load("ar_investigate_dedupe_042", "investigate.py")
        title = "Single-Agent LLMs Outperform Multi-Agent Systems Under Equal Thinking Token Budgets"
        recs = [
            {"url": "https://arxiv.org/abs/2604.02460", "title": title},
            {"url": "https://researchgate.net/publication/403529711", "title": "(PDF) " + title},
        ]
        self.assertEqual(len(inv._dedupe_records(recs)), 1)
        distinct = [dict(recs[0], doi="10.1/a"), dict(recs[1], doi="10.1/b")]
        self.assertEqual(len(inv._dedupe_records(distinct)), 2)  # strong IDs veto title merging
        weak_then_distinct = [{"url": "https://index.example/copy", "title": title}] + distinct
        self.assertEqual(len(inv._dedupe_records(weak_then_distinct)), 2)  # alias cannot hide DOI B

    def test_forward_trace_index_decorations_collapse_to_one_read(self):
        inv = self._load("ar_investigate_forward_titles_042", "investigate.py")
        recs = [
            {"url": "https://scholars.mssm.edu/en/publications/does-the-ipad-night-shift-mode/fingerprints/",
             "title": "Does the iPad Night Shift mode reduce melatonin suppression? - Fingerprint - Icahn School of Medicine at Mount Sinai"},
            {"url": "https://pubmed.ncbi.nlm.nih.gov/31191118/",
             "title": "Does the iPad Night Shift mode reduce melatonin suppression? - PubMed"},
            {"url": "https://www.semanticscholar.org/paper/example",
             "title": "[PDF] Does the iPad Night Shift mode reduce melatonin suppression? | Semantic Scholar"},
            {"url": "https://journals.sagepub.com/doi/abs/10.1177/1477153517748189",
             "title": "Does the iPad Night Shift mode reduce melatonin suppression? - R Nagare, B Plitnick, MG Figueiro, 2019"},
        ]
        self.assertEqual(len(inv._dedupe_records(recs)), 1)

    def test_forward_trace_truncated_title_collapse_is_order_independent(self):
        inv = self._load("ar_investigate_forward_truncation_042", "investigate.py")
        recs = [
            {"url": "https://www.sciencedirect.com/science/article/pii/S2352721821000607",
             "title": "Does iPhone night shift mitigate negative effects of smartphone use on ..."},
            {"url": "https://www.sciencedirect.com/science/article/abs/pii/S2352721821000607",
             "title": "Does iPhone night shift mitigate negative effects of smartphone use on sleep outcomes in emerging adults? - ScienceDirect"},
            {"url": "https://www.sleephealthjournal.org/article/S2352-7218(21)00060-7/abstract",
             "title": "Does iPhone night shift mitigate negative effects of smartphone use on sleep outcomes in emerging adults? - Sleep Health: Journal of the National Sleep Foundation"},
        ]
        for ordered in (recs, list(reversed(recs))):
            self.assertEqual(len(inv._dedupe_records(ordered)), 1)

    def test_later_read_updates_existing_source_record(self):
        inv = self._load("ar_investigate_update_042", "investigate.py")
        node = tempfile.mkdtemp()
        title = "A Definitive Controlled Study of Multi Agent Research Systems"
        with open(os.path.join(node, "sources.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"url": "https://example.org/paper", "title": title}) + "\n")
        inv._merge_existing_read_metadata(node, [{"url": "https://mirror.example/paper", "title": title,
                                                   "_read_ok": True, "_read_file": "notes/x.md"}])
        with open(os.path.join(node, "sources.jsonl"), encoding="utf-8") as fh:
            row = json.loads(fh.readline())
        self.assertTrue(row["_read_ok"])
        self.assertEqual(row["_read_file"], "notes/x.md")

    def test_arxiv_abstract_resolves_to_full_text_endpoint(self):
        inv = self._load("ar_investigate_fulltext_042", "investigate.py")
        calls = []
        original = inv.readmod.read_url

        def fake_read(url, *args, **kwargs):
            calls.append(url)
            return ("full paper body " * 300, "stub")

        inv.readmod.read_url = fake_read
        try:
            text, method, resolved = inv._read_source("https://arxiv.org/abs/2503.13657", 5.0)
        finally:
            inv.readmod.read_url = original
        self.assertGreater(len(text), 1500)
        self.assertIn("/html/2503.13657", calls[0])
        self.assertEqual(resolved, calls[0])
        self.assertIn("full-text", method)

    def test_youtube_source_uses_full_captions(self):
        inv = self._load("ar_investigate_youtube_full", "investigate.py")
        import youtube
        original = youtube.captions
        youtube.captions = lambda _vid: "full caption transcript " * 200
        try:
            text, method, resolved = inv._read_source("https://www.youtube.com/watch?v=aircAruvnKk", 1)
        finally:
            youtube.captions = original
        self.assertGreater(len(text), 1500)
        self.assertIn("captions", method)
        self.assertIn("youtube.com", resolved)

    def test_short_youtube_captions_never_fall_back_to_generic_page(self):
        inv = self._load("ar_investigate_youtube_short", "investigate.py")
        import youtube
        original_captions = youtube.captions
        original_read = inv.readmod.read_url
        youtube.captions = lambda _vid: "short but complete caption transcript"
        inv.readmod.read_url = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("must not read the generic YouTube webpage"))
        try:
            text, method, resolved = inv._read_source("https://youtu.be/aircAruvnKk", 1)
        finally:
            youtube.captions = original_captions
            inv.readmod.read_url = original_read
        self.assertEqual(text, "short but complete caption transcript")
        self.assertIn("captions", method)
        self.assertIn("youtu.be", resolved)

    def test_verify_finds_reads_in_child_nodes_without_live_refetch(self):
        ver = self._load("ar_verify_recursive_reads", "verify.py")
        root = tempfile.mkdtemp()
        notes = os.path.join(root, "children", "leaf", "notes")
        os.makedirs(notes)
        url = "https://example.org/primary"
        with open(os.path.join(notes, hashlib.sha1(url.encode()).hexdigest()[:10] + ".md"),
                  "w", encoding="utf-8") as fh:
            fh.write("Passkeys use origin-bound public key credentials and resist phishing. " * 12)
        original = ver.readmod.read_url
        ver.readmod.read_url = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("must not refetch"))
        try:
            result = ver.verify_claim("Passkeys use public key credentials to resist phishing",
                                      [url], root, None, 1)
        finally:
            ver.readmod.read_url = original
        self.assertTrue(result["link_works"])
        self.assertNotEqual(result["verdict"], "broken")

    def test_synthesis_independence_uses_read_sources_not_search_hits(self):
        syn = self._load("ar_synthesize_reads_042", "synthesize.py")
        node = tempfile.mkdtemp()
        os.makedirs(os.path.join(node, "children"))
        with open(os.path.join(node, "status.json"), "w", encoding="utf-8") as fh:
            json.dump({"qid": "root", "question": "q"}, fh)
        with open(os.path.join(node, "sources.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"url": "https://read.example/a", "_read_ok": True}) + "\n")
            for i in range(10):
                fh.write(json.dumps({"url": "https://unread.example/%d" % i}) + "\n")
        ind = syn.synthesis_input(node)["independence"]
        self.assertEqual(ind["n"], 1)
        self.assertEqual(ind["retrieved_n"], 11)

    def test_rank_relevance_gate_excludes_offtopic_high_authority(self):
        # 0.4.1 efficacy parity: authority must NOT buy a read slot for an off-topic source; the
        # decisive on-topic primary must be read instead (the cold-caller quality gap).
        rk = self._load("ar_rank", "rank.py")
        q = "does magnesium glycinate supplementation improve sleep in adults"
        recs = [
            {"url": "https://www.nature.com/articles/x", "title": "Deep learning segmentation of coral reefs",
             "_class": "evidence", "primary": True},                                     # off-topic, high authority
            {"url": "https://consensus.app/r/mg", "title": "does magnesium improve sleep summary",
             "_class": "evidence"},                                                       # secondary aggregator
            {"url": "https://j.example/rct", "title": "magnesium glycinate supplementation improves sleep quality randomized adults",
             "_class": "evidence", "primary": True},                                      # on-topic primary
        ]
        sel = rk.select_reads(rk.rank(q, recs), 1)
        urls = " ".join(r["url"] for r in sel)
        self.assertIn("j.example/rct", urls)          # the on-topic primary is read
        self.assertNotIn("nature.com", urls)          # off-topic-high-authority is NOT
        self.assertNotIn("consensus.app", urls)       # secondary aggregator is NOT

    def test_rank_never_fills_thin_pool_with_off_topic_sources(self):
        rk = self._load("ar_rank_thin_pool", "rank.py")
        ranked = rk.rank("FIDO2 passkey phishing resistance", [
            {"url": "https://nature.com/ocean", "title": "Deep ocean circulation", "_class": "evidence"},
            {"url": "https://example.org/trees", "title": "Forest canopy ecology", "_class": "evidence"},
        ])
        self.assertEqual(rk.select_reads(ranked, 4), [])

    def test_rank_requires_root_subject_not_generic_comparator_overlap(self):
        rk = self._load("ar_rank_root_focus", "rank.py")
        q = ("synced passkeys phishing-resistant primary standards security whether synced passkeys "
             "are better than passwords plus app TOTP under an exact threat model")
        recs = [
            {"url": "https://arxiv.org/abs/honeywords",
             "title": "The Impact of Exposed Passwords on Honeyword Efficacy",
             "snippet": "password credential database threat model", "_class": "evidence", "primary": True},
            {"url": "https://example.org/totp", "title": "A synced TOTP authenticator app",
             "snippet": "password plus app TOTP", "_class": "lead_gen"},
            {"url": "https://www.nist.gov/passkeys", "title": "Synced passkeys are phishing-resistant",
             "snippet": "passkey credentials are scoped to the relying party", "_class": "evidence", "primary": True},
        ]
        selected = rk.select_reads(rk.rank(
            q, recs, subject_terms=["synced", "passkeys", "phishing-resistant"]), 3)
        self.assertEqual([r["url"] for r in selected], ["https://www.nist.gov/passkeys"])

    def test_rank_preserves_evidence_and_lead_gen_quotas(self):
        rk = self._load("ar_rank_class_quota", "rank.py")
        rows = [
            {"url": "https://e%d" % i, "_class": "evidence", "_relnorm": 1.0,
             "score": 0.5 - i * 0.01} for i in range(4)
        ] + [
            {"url": "https://lead", "_class": "lead_gen", "_relnorm": 1.0, "score": 0.99},
            {"url": "https://color", "_class": "color", "_relnorm": 1.0, "score": 1.0},
        ]
        selected = rk.select_reads(rows, 4)
        self.assertGreaterEqual(sum(r["_class"] == "evidence" for r in selected), 3)
        self.assertEqual(sum(r["_class"] == "lead_gen" for r in selected), 1)
        self.assertEqual(sum(r["_class"] == "color" for r in selected), 0)

    def test_b6_short_distinctive_token_not_dropped(self):
        # review regression: a short but SPECIFIC token (keto/json) must not be dropped in favor of a
        # longer generic co-occurring word — anchor keeps topic order, not length ranking.
        inv = self._load("ar_investigate", "investigate.py")
        self.assertIn("keto", inv._anchor("efficacy over time", "keto epilepsy children"))
        self.assertIn("json", inv._anchor("validation errors", "json schema validation rules"))

    def test_zero_result_relaxation_retries_shorter(self):
        # 0.3.3: a channel that ANDs terms (returns [] on a long query) is retried with fewer
        # most-salient terms until non-empty; the relaxation is recorded in the per-channel report.
        inv = self._load("ar_investigate", "investigate.py")
        calls = []

        def stub(q, n, t):
            calls.append(q)
            return ([{"url": "https://x/1", "title": "hit", "index_of_origin": "stub"}]
                    if len(q.split()) <= 2 else [])          # simulate the AND-cliff
        inv.DISPATCH["stub"] = stub
        inv._cfg_classes = lambda: {"stub": {"class": "evidence", "index_group": "stub"}}
        recs, per = inv.retrieve("how do transformer attention mechanisms scale in large language models",
                                 ["stub"], 5, 5.0)
        self.assertTrue(recs)                                # relaxation recovered results
        self.assertIn("relaxed_to", per["stub"])            # and recorded which shorter query worked
        self.assertGreater(len(calls), 1)                   # it actually retried

    def test_read_floor_recovers_relevant_subject_gate_false_negative(self):
        # If the subject gate empties a lexically relevant pool (the audited product bug), recover;
        # the separate abstention regression below ensures this does not authorize arbitrary noise.
        import tempfile
        inv = self._load("ar_inv_floor", "investigate.py")
        ar_rank = self._load("ar_rank_floor", "rank.py")        # AR rank (fresh instance; avoids the
        inv.rankmod = ar_rank                                   # cached deep-aletheia `rank` + no leak)
        ts = self._load("ar_ts_floor", "treestate.py")
        run = ts.init_run("portable appliance long term review", budget=8, unit=4,
                          base=tempfile.mkdtemp())
        node = os.path.join(run, "tree", "root")
        cands = [{"url": "https://site%d.example/x" % i, "title": "hands-on review %d" % i,
                  "index_of_origin": "stub", "_class": "evidence",
                  "snippet": "real user impressions of the device " * 20} for i in range(4)]
        inv.retrieve = lambda q, ch, lim, to: (list(cands), {"stub": {"n": len(cands)}})
        ar_rank.select_reads = lambda pool, k: []               # force the relevance gate to zero
        inv._read_source = lambda u, to: ("full read text " * 300, "stub", u)
        inv._cfg_classes = lambda: {"stub": {"class": "evidence", "index_group": "stub"}}
        res = inv.investigate(node, channels=["stub"], reads=3)
        self.assertGreater(res["reads_ok"], 0)                  # floor engaged, not a silent zero-read
        self.assertEqual(res["telemetry"]["selection_mode"], "deterministic")
        self.assertTrue(res["telemetry"]["floor_engaged"])

    def test_read_floor_does_not_read_low_relevance_noise(self):
        inv = self._load("ar_inv_floor_abstain", "investigate.py")
        inv.rankmod = self._load("ar_rank_floor_abstain", "rank.py")
        ts = self._load("ar_ts_floor_abstain", "treestate.py")
        run = ts.init_run("portable appliance long term review", budget=8, unit=4,
                          base=tempfile.mkdtemp())
        node = os.path.join(run, "tree", "root")
        raw = [{"url": "https://noise.example/unrelated", "title": "unrelated source",
                "index_of_origin": "stub", "_class": "evidence"}]
        inv.retrieve = lambda *_a, **_k: (list(raw), {"stub": {"n": 1}})
        inv.rankmod.rank = lambda *_a, **_k: [dict(raw[0], _relnorm=0.1, score=0.9)]
        inv.rankmod.select_reads = lambda _pool, _k: []
        inv._read_source = lambda *_a, **_k: self.fail("low-relevance noise must not be read")
        inv._cfg_classes = lambda: {"stub": {"class": "evidence", "index_group": "stub"}}
        res = inv.investigate(node, channels=["stub"], reads=3)
        self.assertEqual(res["reads_ok"], 0)
        self.assertEqual(res["telemetry"]["selected"], 0)
        self.assertFalse(res["telemetry"]["floor_engaged"])

    def _triage_fixture(self):
        # shared setup for the agent-triage path (0.5 brick 2): a fresh AR rank instance (avoids the
        # cached deep-aletheia `rank` collision), stubbed retrieve/read, 4 readable candidates.
        import tempfile
        inv = self._load("ar_inv_triage", "investigate.py")
        inv.rankmod = self._load("ar_rank_triage", "rank.py")
        ts = self._load("ar_ts_triage", "treestate.py")
        run = ts.init_run("portable appliance long term review", budget=8, unit=4,
                          base=tempfile.mkdtemp())
        node = os.path.join(run, "tree", "root")
        cands = [{"url": "https://site%d.example/x" % i, "title": "hands-on review %d" % i,
                  "index_of_origin": "stub", "_class": "evidence", "_index_group": "stub",
                  "snippet": "real user impressions of the device " * 20} for i in range(6)]
        inv.retrieve = lambda q, ch, lim, to: (list(cands), {"stub": {"n": len(cands)}})
        inv._read_source = lambda u, to: ("full read text " * 300, "stub", u)
        inv._cfg_classes = lambda: {"stub": {"class": "evidence", "index_group": "stub"}}
        return inv, node

    def test_candidates_emits_manifest_without_reading(self):
        # step 1 of triage: return the ranked manifest for the agent to judge; read NOTHING, don't
        # bump the round. The manifest must carry the metadata the agent needs (class, snippet, url).
        inv, node = self._triage_fixture()
        out = inv.gather_candidates(node, channels=["stub"])
        self.assertTrue(out["candidates"])                       # a manifest was produced
        self.assertTrue(all("url" in c and "class" in c and "snippet" in c and "primary" in c
                            and "published" in c for c in out["candidates"]))
        self.assertTrue(os.path.exists(inv._triage_path(node)))  # round context persisted for `read`
        self.assertFalse(os.path.isdir(os.path.join(node, "notes")) and
                         os.listdir(os.path.join(node, "notes")))  # nothing read yet

    def test_read_picks_reads_exactly_the_agents_choices(self):
        # step 2: read exactly the URLs the agent picked, finish the round, consume the manifest.
        inv, node = self._triage_fixture()
        inv.gather_candidates(node, channels=["stub"])
        res = inv.read_picks(node, picks=["https://site0.example/x", "https://site2.example/x"])
        self.assertEqual(res["reads_ok"], 2)                    # only the two picks were read
        self.assertEqual(res["round"], 1)                       # round bumped once
        self.assertEqual(res["telemetry"]["selection_mode"], "agent")
        self.assertFalse(res["telemetry"]["floor_engaged"])
        self.assertFalse(os.path.exists(inv._triage_path(node)))  # manifest consumed after read

    def test_read_picks_rejects_empty_selection_without_consuming_round(self):
        # An abstaining agent must not silently turn back into the fixed-table selector.
        inv, node = self._triage_fixture()
        inv.gather_candidates(node, channels=["stub"])
        with self.assertRaises(SystemExit):
            inv.read_picks(node, picks=["https://not-a-candidate.example/z"])
        self.assertTrue(os.path.exists(inv._triage_path(node)))  # agent can correct the selection
        st = inv.treestate._read_json(os.path.join(node, "status.json"), {})
        self.assertEqual(st.get("rounds", 0), 0)

    def test_read_picks_caps_agent_selection_to_round_budget(self):
        inv, node = self._triage_fixture()
        inv.gather_candidates(node, channels=["stub"])
        res = inv.read_picks(node, picks=["https://site%d.example/x" % i for i in range(6)])
        self.assertEqual(res["reads_ok"], 4)                   # unit=4 => at most four reads

    def test_agent_requery_is_observable_without_consuming_the_round(self):
        inv, node = self._triage_fixture()
        inv.gather_candidates(node, channels=["stub"])
        inv.gather_candidates(node, query="specific pump failure evidence", channels=["stub"])
        with open(inv._telemetry_path(node), encoding="utf-8") as fh:
            events = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual([e["event"] for e in events],
                         ["candidate_gather", "candidate_gather", "triage_requery"])
        self.assertEqual([e["attempt"] for e in events[:2]], [1, 2])
        self.assertEqual([e["requery"] for e in events[:2]], [False, True])
        self.assertGreater(events[2]["rejected_candidates"], 0)
        st = inv.treestate._read_json(os.path.join(node, "status.json"), {})
        self.assertEqual(st.get("rounds", 0), 0)

    def test_agent_requery_cap_refuses_third_gather_before_network_io(self):
        inv, node = self._triage_fixture()
        inv.gather_candidates(node, channels=["stub"])
        inv.gather_candidates(node, query="specific pump failure evidence", channels=["stub"])
        inv.retrieve = lambda *_a, **_k: self.fail("third gather must fail before network I/O")
        with self.assertRaises(SystemExit):
            inv.gather_candidates(node, query="another hidden search pass", channels=["stub"])
        with open(inv._telemetry_path(node), encoding="utf-8") as fh:
            events = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual(sum(e.get("event") == "candidate_gather" for e in events), 2)
        self.assertTrue(os.path.exists(inv._triage_path(node)))
        st = inv.treestate._read_json(os.path.join(node, "status.json"), {})
        self.assertEqual(st.get("rounds", 0), 0)

    def test_agent_can_explicitly_reject_manifest_and_consume_round(self):
        inv, node = self._triage_fixture()
        inv.gather_candidates(node, channels=["stub"])
        inv._read_source = lambda *_a, **_k: self.fail("reject must not read a source")
        res = inv.reject_candidates(node, why="all candidates are off-topic affiliate pages")
        self.assertEqual(res["round"], 1)
        self.assertEqual(res["reads_ok"], 0)
        self.assertEqual(res["telemetry"]["selection_mode"], "agent")
        self.assertTrue(res["telemetry"]["abstained"])
        self.assertFalse(os.path.exists(inv._triage_path(node)))
        st = inv.treestate._read_json(os.path.join(node, "status.json"), {})
        self.assertEqual(st.get("rounds"), 1)
        with open(os.path.join(node, "decisions.jsonl"), encoding="utf-8") as fh:
            decisions = [json.loads(line) for line in fh if line.strip()]
        self.assertTrue(any("off-topic affiliate pages" in d.get("why", "") for d in decisions))

    def test_runtime_dispatch_covers_enabled_specialty_channels(self):
        inv = self._load("ar_investigate_dispatch_compat", "investigate.py")
        for channel in ("openlibrary", "x", "youtube"):
            self.assertIn(channel, inv.DISPATCH)

    def test_bounded_tier_round_cap_matches_scrutiny_budget(self):
        inv = self._load("ar_investigate_round_cap", "investigate.py")
        self.assertEqual(inv._round_cap({"budget": 4}, {"unit": 4, "thoroughness": "quick"}), 1)
        self.assertEqual(inv._round_cap({"budget": 12}, {"unit": 4, "thoroughness": "deep"}), 3)
        self.assertIsNone(inv._round_cap({"budget": 1_000_000},
                                         {"unit": 4, "thoroughness": "unlimited"}))
        self.assertIsNone(inv._round_cap({"budget": 1_000_000},
                                         {"unit": 4, "thoroughness": "accuracy"}))

    def test_bounded_leaf_refuses_an_extra_round_before_network_io(self):
        inv = self._load("ar_investigate_round_enforcement", "investigate.py")
        ts = self._load("ar_treestate_round_enforcement", "treestate.py")
        run = ts.init_run("topic", thoroughness="quick", base=tempfile.mkdtemp())
        leaf = ts.split_node(os.path.join(run, "tree", "root"), [["a", "qa"], ["b", "qb"]])[0]
        ts.set_status(leaf, rounds=1)
        original = inv.retrieve
        inv.retrieve = lambda *_a, **_k: self.fail("network must not run after the cap")
        try:
            with self.assertRaises(SystemExit):
                inv.investigate(leaf)
        finally:
            inv.retrieve = original

    def test_relaxation_not_triggered_when_first_query_hits(self):
        # never broaden a query that already returned results
        inv = self._load("ar_investigate", "investigate.py")
        calls = []

        def stub(q, n, t):
            calls.append(q)
            return [{"url": "https://y/1", "title": "hit", "index_of_origin": "stub"}]
        inv.DISPATCH["stub"] = stub
        inv._cfg_classes = lambda: {"stub": {"class": "evidence", "index_group": "stub"}}
        recs, per = inv.retrieve("a fairly long query with several distinct content terms here", ["stub"], 5, 5.0)
        self.assertEqual(len(calls), 1)                      # one call, no relaxation
        self.assertNotIn("relaxed_to", per["stub"])


    def test_biomed_and_regulatory_venues_rank_primary(self):
        rk = self._load("ar_rank", "rank.py")
        for u in ("https://www.thelancet.com/x", "https://www.nejm.org/x", "https://www.bmj.com/x",
                  "https://www.efsa.europa.eu/x", "https://www.who.int/x", "https://www.nice.org.uk/x"):
            self.assertEqual(rk.authority(u), 1.0, u)

    def test_tree_caps_reserve_room_for_a_real_split(self):
        ts = self._load("ar_treestate_node_cap", "treestate.py")
        run = ts.init_run("topic", budget=16, unit=4, max_depth=3, max_children=4,
                          max_nodes=4, base=tempfile.mkdtemp())
        root = os.path.join(run, "tree", "root")
        children = ts.split_node(root, [["a", "qa"], ["b", "qb"]])
        chk = ts.can_split(children[0])
        self.assertFalse(chk["can_split"])
        self.assertIn("max_nodes", " ".join(chk["reasons"]))

    def test_weight_count_mismatch_is_rejected(self):
        ts = self._load("ar_treestate_weight_validation", "treestate.py")
        run = ts.init_run("topic", budget=16, unit=4, base=tempfile.mkdtemp())
        with self.assertRaises(SystemExit):
            ts.split_node(os.path.join(run, "tree", "root"), [["a", "qa"], ["b", "qb"]],
                          weights=[1])

    def test_citation_accuracy_null_until_coverage_complete(self):
        run = tempfile.mkdtemp()
        with open(os.path.join(run, "run.json"), "w", encoding="utf-8") as fh:
            json.dump({"topic": "t", "version": "aletheia-research-accuracy 0.3.1"}, fh)
        os.makedirs(os.path.join(run, "tree"))
        with open(os.path.join(run, "verify.jsonl"), "w") as fh:
            for v in ("supported", "contradicted", "relevant"):     # one still awaiting the LLM pass
                fh.write(json.dumps({"claim": "c", "verdict": v}) + "\n")
        s = score_run.score(run)
        self.assertFalse(s["citation_complete"])
        self.assertIsNone(s["citation_accuracy"])            # no headline while a claim is unverified
        self.assertEqual(s["citation_precision"], 0.5)       # 1 supported / 2 finally judged
        self.assertEqual(s["citation_denominator"], 2)       # stated denominator = claims judged
        self.assertEqual(s["citation_coverage"], round(2 / 3, 3))

    def test_openalex_shortens_queries_over_api_limit(self):
        import importlib.util
        path = os.path.join(ROOT, ".cursor", "skills", "channel-retrieval", "scripts", "openalex.py")
        spec = importlib.util.spec_from_file_location("openalex_042", path)
        oa = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oa)
        seen = []
        original = oa._http.get_json
        oa._http.get_json = lambda url, timeout: (seen.append(url) or {"results": []})
        try:
            oa.search("What controlled evidence shows that multi-agent LLM research improves breadth "
                      "or accuracy over strong single-agent baselines?", 5, 1.0)
        finally:
            oa._http.get_json = original
        query = urllib.parse.parse_qs(urllib.parse.urlparse(seen[0]).query)["search"][0]
        self.assertLessEqual(len(query), 100)
        self.assertIn("llm", query.lower())

    def test_brave_retries_rejected_compound_query(self):
        import importlib.util
        path = os.path.join(ROOT, ".cursor", "skills", "channel-retrieval", "scripts", "brave.py")
        spec = importlib.util.spec_from_file_location("brave_043", path)
        brave = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(brave)
        calls = []
        original = brave._http.get_json

        def fake(url, *_a, **_k):
            calls.append(url)
            if len(calls) == 1:
                raise urllib.error.HTTPError(url, 422, "Unprocessable", {}, None)
            return {"web": {"results": []}}

        brave._http.get_json = fake
        with mock.patch.dict(os.environ, {"BRAVE_API_KEY": "test"}):
            try:
                brave.search("a very long compound authentication security query with many deployment "
                             "recovery fallback phishing implementation compatibility terms", 5, 1)
            finally:
                brave._http.get_json = original
        self.assertEqual(len(calls), 2)
        first = urllib.parse.parse_qs(urllib.parse.urlparse(calls[0]).query)["q"][0]
        second = urllib.parse.parse_qs(urllib.parse.urlparse(calls[1]).query)["q"][0]
        self.assertLess(len(second.split()), len(first.split()))

    def test_openlibrary_client_normalizes_book_records(self):
        import importlib.util
        path = os.path.join(ROOT, ".cursor", "skills", "channel-retrieval", "scripts", "openlibrary.py")
        spec = importlib.util.spec_from_file_location("openlibrary_043", path)
        ol = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ol)
        original = ol._http.get_json
        ol._http.get_json = lambda *_a, **_k: {"docs": [{
            "key": "/works/OL1W", "title": "Carnegie Libraries", "author_name": ["A. Scholar"],
            "first_publish_year": 2021, "edition_count": 3, "subject": ["Libraries", "Education"],
        }]}
        try:
            rows = ol.search("Carnegie libraries", 5, 1)
        finally:
            ol._http.get_json = original
        self.assertEqual(rows[0]["index_of_origin"], "openlibrary")
        self.assertEqual(rows[0]["title"], "Carnegie Libraries")
        self.assertIn("openlibrary.org/works/OL1W", rows[0]["url"])


class TestInstall(unittest.TestCase):
    def test_installer_links_skills_for_codex(self):
        home = tempfile.mkdtemp()
        env = dict(os.environ, HOME=home, CODEX_HOME=os.path.join(home, ".codex"))
        subprocess.check_call(["bash", os.path.join(ROOT, "scripts", "install.sh")], env=env,
                              stdout=subprocess.DEVNULL)
        target = os.path.join(home, ".codex", "skills", "aletheia-research-accuracy")
        self.assertTrue(os.path.islink(target))
        self.assertTrue(os.path.isfile(os.path.join(target, "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(target, "agents", "openai.yaml")))
        self.assertFalse(os.path.exists(os.path.join(home, ".codex", "skills", "deep-aletheia")))

    def test_installer_rejects_invalid_mode(self):
        home = tempfile.mkdtemp()
        env = dict(os.environ, HOME=home, CODEX_HOME=os.path.join(home, ".codex"))
        proc = subprocess.run(["bash", os.path.join(ROOT, "scripts", "install.sh"), "--invalid"],
                              env=env, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(home, ".codex", "skills")))

    def test_codex_only_install_leaves_cursor_and_claude_untouched(self):
        home = tempfile.mkdtemp()
        os.makedirs(os.path.join(home, ".cursor", "skills"))
        os.makedirs(os.path.join(home, ".claude", "skills"))
        cursor_marker = os.path.join(home, ".cursor", "skills", "KEEP")
        claude_marker = os.path.join(home, ".claude", "skills", "KEEP")
        for marker in (cursor_marker, claude_marker):
            with open(marker, "w", encoding="utf-8") as fh:
                fh.write("unchanged")
        env = dict(os.environ, HOME=home, CODEX_HOME=os.path.join(home, ".codex"))
        output = subprocess.check_output(
            ["bash", os.path.join(ROOT, "scripts", "install.sh"), "--codex-only"],
            env=env, text=True)
        target = os.path.join(home, ".codex", "skills", "aletheia-research-accuracy")
        self.assertTrue(os.path.islink(target))
        self.assertEqual(read_text(cursor_marker), "unchanged")
        self.assertEqual(read_text(claude_marker), "unchanged")
        self.assertEqual(os.listdir(os.path.dirname(cursor_marker)), ["KEEP"])
        self.assertEqual(os.listdir(os.path.dirname(claude_marker)), ["KEEP"])
        self.assertIn(os.path.join(os.path.abspath(ROOT), ".cursor", "skills", "channel-retrieval",
                                   "scripts", "doctor.py"), output)
        self.assertNotIn("~/.cursor/skills/channel-retrieval", output)

    def test_accuracy_install_preserves_stable_codex_skill(self):
        home = tempfile.mkdtemp()
        stable = os.path.join(home, ".codex", "skills", "aletheia-research")
        os.makedirs(stable)
        stable_marker = os.path.join(stable, "STABLE_CHECKPOINT")
        with open(stable_marker, "w", encoding="utf-8") as fh:
            fh.write("addfaf6")
        env = dict(os.environ, HOME=home, CODEX_HOME=os.path.join(home, ".codex"))
        subprocess.check_call(["bash", os.path.join(ROOT, "scripts", "install.sh"), "--codex-only"],
                              env=env, stdout=subprocess.DEVNULL)
        self.assertEqual(read_text(stable_marker), "addfaf6")
        self.assertTrue(os.path.islink(os.path.join(home, ".codex", "skills",
                                                    "aletheia-research-accuracy")))

    def test_copy_install_keeps_non_secret_repo_root_pointer(self):
        home = tempfile.mkdtemp()
        env = dict(os.environ, HOME=home, CODEX_HOME=os.path.join(home, ".codex"))
        subprocess.check_call(["bash", os.path.join(ROOT, "scripts", "install.sh"), "--copy"],
                              env=env, stdout=subprocess.DEVNULL)
        marker = os.path.join(home, ".cursor", "skills", "channel-retrieval", ".aletheia-root")
        self.assertTrue(os.path.isfile(marker))
        self.assertEqual(read_text(marker).strip(), os.path.abspath(ROOT))
        self.assertTrue(os.path.islink(os.path.join(home, ".codex", "skills", "aletheia-research-accuracy")))


class TestKeywordizeRecall(unittest.TestCase):
    """0.3.3 salience-aware keywordize: keep the n MOST salient terms (rare/acronym/identifier), not
    the first n — the audited recall bug that dropped distinctive rare terms appearing later."""

    def test_short_query_passthrough(self):
        self.assertEqual(_http.keywordize("intermittent fasting", 6), "intermittent fasting")

    def test_keeps_acronyms_drops_stopwords(self):
        o = _http.keywordize("what is the best RAG pipeline for retrieval augmented generation with LLM agents", 5)
        self.assertIn("rag", o)
        self.assertIn("llm", o)
        self.assertNotIn("best", o)
        self.assertNotIn("what", o)

    def test_central_terms_beat_peripheral_length(self):
        # length is capped, so the front-loaded central pair is kept, not a longer peripheral word
        self.assertEqual(
            _http.keywordize("how do transformer attention mechanisms scale in large language models", 2),
            "transformer attention")

    def test_keeps_version_identifier_and_acronym(self):
        o = _http.keywordize("does GPT-4 beat Claude on the MMLU benchmark suite released this year", 4)
        self.assertIn("gpt-4", o)   # digit/symbol bonus keeps the identifier
        self.assertIn("mmlu", o)    # all-caps acronym bonus keeps it despite being short

    def test_front_loaded_topic_not_lost_to_generic_filler(self):
        # review regression: length ranking dropped 'acid rain' for the longer adverb 'significantly'
        self.assertEqual(
            _http.keywordize("acid rain damages forest ecosystems significantly worldwide", 2),
            "acid rain")
        self.assertEqual(
            _http.keywordize("why does aspirin reduce heart attack risk in older adults reliably", 3),
            "aspirin reduce heart")

    def test_late_proper_noun_entity_is_rescued(self):
        # the audit's ACTUAL complaint: a distinctive proper noun appearing LATE (Exa/Tavily/Claude)
        # must survive, which pure first-n dropped and length mis-ranked
        self.assertIn("claude", _http.keywordize(
            "does GPT-4 beat Claude on the MMLU benchmark released this year", 4))
        self.assertIn("exa", _http.keywordize(
            "compare neural search api deep retrieval quality of Exa and Tavily", 4))

    def test_multiple_phrases_do_not_overflow_n(self):
        # review regression: quoted phrases used to bypass the n cap and over-constrain AND APIs
        out = _http.keywordize('find "alpha one" "beta two" "gamma three" "delta four" now', 2)
        self.assertLessEqual(out.count('"') // 2 + len([w for w in out.split()]), 4)  # <= 2 phrase-units
        self.assertIn("alpha", out)

    def test_orchestration_and_dates_cannot_crowd_out_root_subject(self):
        q = ("synced passkeys phishing-resistant What do primary standards, government guidance, "
             "and security research establish about app-based TOTP as of 2026-07-09? Hunt results.")
        out = _http.keywordize(q, 3)
        self.assertEqual(out, "synced passkeys totp")
        self.assertNotIn("2026", out)
        self.assertNotIn("hunt", out)


class TestHighAccuracyRuntimeLedger(unittest.TestCase):
    AR = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts")

    @classmethod
    def _load(cls, name, fname):
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, os.path.join(cls.AR, fname))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_init_decouples_read_and_reasoning_budgets(self):
        ts = self._load("runtime_ts_decoupled", "treestate.py")
        run = ts.init_run("accuracy", thoroughness="exhaustive", base=tempfile.mkdtemp(),
                          reads_per_round=40, max_read_attempts=640, max_seconds=3600)
        cfg = read_json(os.path.join(run, "run.json"))
        self.assertEqual(cfg["unit"], 4.0)
        self.assertEqual(cfg["limits"], {"max_seconds": 3600,
                                         "max_reads_per_round": 40,
                                         "max_read_attempts": 640})

    def test_accuracy_hard_ceilings_cannot_be_overridden(self):
        ts = self._load("runtime_ts_absolute_caps", "treestate.py")
        for kwargs in ({"reads_per_round": 41}, {"max_read_attempts": 641},
                       {"max_seconds": 3601}):
            with self.assertRaises(ValueError):
                ts.init_run("accuracy", base=tempfile.mkdtemp(), **kwargs)

    def test_run_read_cap_is_atomic_and_fail_closed(self):
        ts = self._load("runtime_ts_cap", "treestate.py")
        run = ts.init_run("accuracy", base=tempfile.mkdtemp(), reads_per_round=4,
                          max_read_attempts=3)
        node = os.path.join(run, "tree", "root")
        ts.reserve_runtime(node, "read", 2, "worker-a")
        with self.assertRaises(SystemExit):
            ts.reserve_runtime(node, "read", 2, "worker-b")
        ledger = read_json(os.path.join(run, "runtime-ledger.json"))
        self.assertEqual(ledger["read_attempts_reserved"], 2)
        self.assertEqual(ledger["termination_reason"], "run_read_limit")

    def test_candidates_honors_explicit_reads(self):
        ts = self._load("runtime_ts_reads", "treestate.py")
        prior = sys.modules.get("treestate")
        sys.modules["treestate"] = ts
        try:
            inv = self._load("runtime_inv_reads", "investigate.py")
        finally:
            if prior is None:
                sys.modules.pop("treestate", None)
            else:
                sys.modules["treestate"] = prior
        run = ts.init_run("pump reliability", base=tempfile.mkdtemp(), reads_per_round=7)
        node = os.path.join(run, "tree", "root")
        inv.retrieve = lambda *_a, **_k: ([{"url": "https://x.example/a", "title": "pump reliability",
                                             "snippet": "pump reliability evidence",
                                             "index_of_origin": "stub"}], {"stub": {"n": 1}})
        inv.rankmod.rank = lambda _q, recs, **_k: [dict(r, _class="evidence",
                                                        _index_group="stub", _relnorm=1.0,
                                                        score=1.0) for r in recs]
        inv.router.route = lambda *_a, **_k: {"channels": ["stub"]}
        out = inv.gather_candidates(node, channels=["stub"], reads=7)
        self.assertEqual(out["reads_suggested"], 7)

    def test_browser_zero_max_chars_stays_unlimited(self):
        import importlib.util
        path = os.path.join(ROOT, ".cursor", "skills", "channel-retrieval", "scripts", "read.py")
        spec = importlib.util.spec_from_file_location("runtime_read_zero", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        seen = []
        module._agentreach.browser_available = lambda: True
        module._agentreach.browser_extract = lambda _u, _t, n: (seen.append(n) or ("x" * 2000), "")
        text, method = module.read_url("https://example.invalid", 1, 0, browser=True)
        self.assertEqual((len(text), method), (2000, "opencli-browser"))
        self.assertEqual(seen, [0])


class TestEvalJudgeCore(unittest.TestCase):
    """The eval measurement core must be HONEST: it declares a winner ONLY when the win-rate CI clears
    0.5 AND the automated judge is calibrated to the human anchor — otherwise 'inconclusive'. This is
    the code-level guard against the audited failure (asserting improvement without valid measurement)."""

    def test_uncalibrated_judge_is_never_trusted(self):
        # high win-rate but no human anchor -> provisional, NOT "better"
        r = {"pairwise": [{"topic": t, "winner": "candidate"} for t in "abcd"]}
        self.assertIn("UNCALIBRATED", js.summarize(r)["verdict"])

    def test_judge_disagreeing_with_human_blocks_the_win(self):
        r = {"pairwise": [{"topic": t, "winner": "candidate"} for t in "abcde"],
             "human": [{"topic": t, "winner": "baseline"} for t in "abde"] + [{"topic": "c", "winner": "tie"}]}
        s = js.summarize(r)
        self.assertFalse(s["judge_calibration"]["trusted"])
        self.assertIn("NOT TRUSTED", s["verdict"])

    def test_small_n_stays_inconclusive_even_when_judge_perfect(self):
        # 4/5 wins + kappa=1.0, but N is too small: CI spans 0.5 -> must NOT claim "better"
        r = {"pairwise": [{"topic": t, "winner": "candidate"} for t in "abcd"] + [{"topic": "e", "winner": "baseline"}],
             "human": [{"topic": t, "winner": "candidate"} for t in "abcd"] + [{"topic": "e", "winner": "baseline"}]}
        s = js.summarize(r)
        self.assertEqual(s["judge_calibration"]["cohen_kappa"], 1.0)
        self.assertIn("inconclusive", s["verdict"])           # honest about statistical power

    def test_objective_deltas_and_tie_handling(self):
        r = {"pairwise": [{"topic": "a", "winner": "tie"}],
             "objective": {"candidate": {"a": {"citation_precision": 0.9}},
                           "baseline": {"a": {"citation_precision": 0.8}}}}
        s = js.summarize(r)
        self.assertEqual(s["objective_delta_candidate_minus_baseline"]["citation_precision"], 0.1)
        self.assertEqual(s["ties"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
