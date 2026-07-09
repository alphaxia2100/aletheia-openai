#!/usr/bin/env python3
"""Aletheia correctness tests (stdlib unittest, no deps).

Run: python3 -m unittest discover -s tests   (or: python3 tests/test_aletheia.py)

These lock in the fixes for the independence-math bugs found in review — the
differentiator must never silently return wrong numbers again.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

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
        return [l for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []

    def test_rounds_accumulate_and_no_source_duplication(self):
        investigate.investigate(self.node, channels=["stub"], reads=2)          # round 1: read A,B
        investigate.investigate(self.node, query="metabolic gap", channels=["stub"], reads=2)  # round 2: B dup, C new
        st = treestate._read_json(os.path.join(self.node, "status.json"), {})
        self.assertEqual(st["rounds"], 2)                       # accumulated, not overwritten
        self.assertEqual(st["n_read"], 3)                      # A,B (r1) + C (r2); B not re-read
        self.assertEqual(len(self._node_sources()), 3)         # A,B,C — B deduped, not duplicated
        ev = open(os.path.join(self.node, "evidence.md"), encoding="utf-8").read()
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
    """aletheia-research's router scopes channels to the question's domain and EXCLUDES off-topic
    ones (subprocess: avoids a module-name clash with the frozen deep-aletheia `router`)."""

    def _route(self, q):
        r = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts", "router.py")
        out = subprocess.check_output([sys.executable, r, q, "--json", "--max", "6"], text=True)
        return json.loads(out)

    def test_biomed_routes_to_europepmc_not_arxiv(self):
        c = self._route("does intermittent fasting improve metabolic health and cognition")["channels"]
        self.assertIn("europepmc", c)
        self.assertNotIn("arxiv", c)          # arXiv has ~no clinical content

    def test_cs_routes_to_arxiv_not_europepmc(self):
        c = self._route("how do transformer attention mechanisms scale in large language models")["channels"]
        self.assertIn("arxiv", c)
        self.assertNotIn("europepmc", c)

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
    """aletheia 0.3's thoroughness dial sets the tree budget/caps and tags version 0.3.0.
    Run via subprocess to avoid a module-name clash with the frozen deep-aletheia `treestate`."""

    T = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts", "treestate.py")

    def _init(self, tier, base):
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "test topic", "--thoroughness", tier, "--base", base],
            text=True).strip()
        return json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))

    def test_tiers_scale_and_version(self):
        base = tempfile.mkdtemp()
        q, dp = self._init("quick", base), self._init("deep", base)
        self.assertEqual(q["version"], "aletheia-research 0.4.1")
        self.assertEqual(q["thoroughness"], "quick")
        self.assertLess(q["budget"], dp["budget"])            # deeper tier spends more
        self.assertLess(q["max_depth"], dp["max_depth"])      # and splits deeper

    def test_default_is_unlimited(self):
        # 0.4.0: no --thoroughness and no --budget -> the unlimited default (unbounded depth/budget)
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "test topic", "--base", tempfile.mkdtemp()],
            text=True).strip()
        c = json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))
        self.assertEqual(c["thoroughness"], "unlimited")
        self.assertGreaterEqual(c["budget"], 1_000_000)
        self.assertGreaterEqual(c["max_depth"], 99)
        self.assertEqual(c["verbosity"], "user")              # default audience

    def test_explicit_budget_stays_custom(self):
        # an explicit --budget is a bounded CUSTOM run, NOT overridden by the unlimited default
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "t", "--budget", "32", "--base", tempfile.mkdtemp()],
            text=True).strip()
        c = json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))
        self.assertEqual(c["thoroughness"], "custom")
        self.assertEqual(c["budget"], 32.0)

    def test_verbosity_agent_recorded_and_bundle_has_full_files(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "bundle topic", "--verbosity", "agent", "--base", base],
            text=True).strip()
        self.assertEqual(json.load(open(os.path.join(run, "run.json")))["verbosity"], "agent")
        subprocess.check_call([sys.executable, self.T, "findings", "--node",
                               os.path.join(run, "tree", "root"), "--text",
                               "UNIQUE_FINDING_MARKER with a [primary](https://x)"], stdout=subprocess.DEVNULL)
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts", "report.py")
        out = subprocess.check_output([sys.executable, rep, "bundle", "--run", run], text=True)
        self.assertIn("FULL BUNDLE", out)
        self.assertIn("UNIQUE_FINDING_MARKER", out)           # the actual file content is included verbatim

    def test_report_score_ships_with_skill(self):
        # 0.4.1 parity: the headline scorer is INSIDE the skill (report.py score) — no repo/eval dep.
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "score topic", "--base", base], text=True).strip()
        os.makedirs(os.path.join(run, "index"), exist_ok=True)
        with open(os.path.join(run, "verify.jsonl"), "w") as fh:
            for v in ("supported", "supported", "off_topic", "relevant"):
                fh.write(json.dumps({"verdict": v}) + "\n")
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts", "report.py")
        s = json.loads(subprocess.check_output([sys.executable, rep, "score", "--run", run], text=True))
        self.assertEqual(s["citation_precision"], round(2 / 3, 3))   # off_topic counts in denominator
        self.assertEqual(s["citation_denominator"], 3)
        self.assertFalse(s["citation_complete"])                     # 1 claim still awaiting
        self.assertIsNone(s["citation_accuracy"])

    def test_report_write_brief_emits_deliverable(self):
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "brief topic", "--base", base], text=True).strip()
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts", "report.py")
        subprocess.check_call([sys.executable, rep, "write-brief", "--run", run, "--text",
                               "# Brief\nMULTIPAGE_MARKER"], stdout=subprocess.DEVNULL)
        self.assertIn("MULTIPAGE_MARKER", open(os.path.join(run, "brief.md")).read())

    def test_bundle_survives_corrupt_artifacts(self):
        # review hardening: a non-UTF-8 byte or a non-dict sources line must NOT abort the whole
        # bundle into an empty result — it must degrade gracefully and still return every artifact.
        base = tempfile.mkdtemp()
        run = subprocess.check_output(
            [sys.executable, self.T, "init", "corrupt topic", "--base", base], text=True).strip()
        subprocess.check_call([sys.executable, self.T, "findings", "--node",
                               os.path.join(run, "tree", "root"), "--text", "SURVIVOR_MARKER"],
                              stdout=subprocess.DEVNULL)
        with open(os.path.join(run, "portfolio.md"), "wb") as fh:
            fh.write(b"valid text \xff\xfe then more")        # invalid UTF-8
        with open(os.path.join(run, "tree", "root", "sources.jsonl"), "w") as fh:
            fh.write("123\n" + json.dumps({"url": "https://x", "title": "ok"}) + "\n")  # non-dict line
        rep = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts", "report.py")
        out = subprocess.check_output([sys.executable, rep, "bundle", "--run", run], text=True)
        self.assertIn("SURVIVOR_MARKER", out)                 # content survived the corrupt neighbors


class TestAletheiaResearch031(unittest.TestCase):
    """0.3.1 audit fixes: weighted split, resumable frontier, structural independence,
    _anchor de-pollution, biomed authority, code-gated citation coverage. The aletheia-research
    scripts share module names with the frozen deep-aletheia baseline imported above, so CLI-level
    checks go through subprocess and Python-level checks load the AR modules under distinct names."""

    AR = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts")

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
        b = [json.load(open(os.path.join(d, "status.json")))["budget"] for d in dirs]
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
        b = [json.load(open(os.path.join(d, "status.json")))["budget"] for d in dirs]
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

    def test_citation_accuracy_null_until_coverage_complete(self):
        run = tempfile.mkdtemp()
        json.dump({"topic": "t", "version": "aletheia-research 0.3.1"},
                  open(os.path.join(run, "run.json"), "w"))
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
