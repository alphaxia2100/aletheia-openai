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
sys.path.insert(0, os.path.join(ROOT, "scripts", "eval"))

import provenance_graph as pg  # noqa: E402
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
        self.assertEqual(set(out["counts"]), {"relevant", "off_topic", "broken"})


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
        self.assertEqual(s["verdicts"], {"supported": 2, "contradicted": 1,
                                         "unsupported": 1, "awaiting_llm_check": 0})

    def test_citation_accuracy_is_none_before_llm_pass(self):
        run = self._run_with_verify(["relevant", "relevant", "relevant"])
        s = score_run.score(run)
        self.assertIsNone(s["citation_accuracy"])          # not yet Fact-Checked
        self.assertEqual(s["verdicts"]["awaiting_llm_check"], 3)
        self.assertEqual(s["on_topic_rate"], 1.0)


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


class TestAletheia03Thoroughness(unittest.TestCase):
    """aletheia 0.3's thoroughness dial sets the tree budget/caps and tags version 0.3.0.
    Run via subprocess to avoid a module-name clash with the frozen deep-aletheia `treestate`."""

    def _init(self, tier, base):
        t = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts", "treestate.py")
        run = subprocess.check_output(
            [sys.executable, t, "init", "test topic", "--thoroughness", tier, "--base", base],
            text=True).strip()
        return json.load(open(os.path.join(run, "run.json"), encoding="utf-8"))

    def test_tiers_scale_and_version(self):
        base = tempfile.mkdtemp()
        q, dp = self._init("quick", base), self._init("deep", base)
        self.assertEqual(q["version"], "aletheia-research 0.3.0")
        self.assertEqual(q["thoroughness"], "quick")
        self.assertLess(q["budget"], dp["budget"])            # deeper tier spends more
        self.assertLess(q["max_depth"], dp["max_depth"])      # and splits deeper


if __name__ == "__main__":
    unittest.main(verbosity=2)
