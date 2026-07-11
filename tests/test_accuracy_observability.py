import importlib.util
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
AR = os.path.join(ROOT, ".cursor", "skills", "aletheia-research-accuracy", "scripts")
REPORT = os.path.join(AR, "report.py")
GRADER = os.path.join(ROOT, "scripts", "eval", "grade_accuracy_run.py")


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(AR, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestAccuracyObservability(unittest.TestCase):
    def setUp(self):
        self.ts = load("observability_treestate_%s" % id(self), "treestate.py")
        self.run = self.ts.init_run("exact original user request", base=tempfile.mkdtemp())
        self.node = os.path.join(self.run, "tree", "root")

    def score(self):
        return json.loads(subprocess.check_output(
            [sys.executable, REPORT, "score", "--run", self.run], text=True))

    def test_run_log_is_hash_chained_and_preserves_request(self):
        audit = self.ts.audit_run_events(self.run)
        self.assertTrue(audit["chain_valid"])
        self.assertEqual(audit["event_counts"], {"node_created": 1, "run_initialized": 1})
        with open(os.path.join(self.run, "request.md"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "exact original user request\n")
        path = os.path.join(self.run, "run-events.jsonl")
        with open(path, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        rows[0]["actor"] = "tampered"
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        self.assertFalse(self.ts.audit_run_events(self.run)["chain_valid"])

    def test_manifest_and_engine_read_identity_survive_triage_serialization(self):
        prior = sys.modules.get("treestate")
        sys.modules["treestate"] = self.ts
        try:
            inv = load("observability_investigate_%s" % id(self), "investigate.py")
        finally:
            if prior is None:
                sys.modules.pop("treestate", None)
            else:
                sys.modules["treestate"] = prior
        inv.retrieve = lambda *_a, **_k: ([{
            "url": "https://example.org/primary", "title": "exact original user request evidence",
            "snippet": "direct evidence", "index_of_origin": "stub"}],
            {"stub": {"n": 1, "latency_s": 0.01, "error": None}})
        inv.rankmod.rank = lambda _q, rows, **_k: [dict(
            row, _class="evidence", _index_group="stub", _relnorm=1.0, score=1.0)
            for row in rows]
        inv._read_source = lambda *_a, **_k: ("evidence " * 400, "stub-reader", "https://example.org/primary")
        out = inv.gather_candidates(self.node, channels=["stub"], reads=1)
        self.assertTrue(os.path.isfile(os.path.join(self.run, out["manifest"])))
        inv.read_picks(self.node, picks=["https://example.org/primary"], why="decisive primary")
        with open(os.path.join(self.node, "sources.jsonl"), encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        read_rows = [row for row in rows if row.get("_read_ok")]
        self.assertEqual(len(read_rows), 1)
        self.assertTrue(read_rows[0].get("_read_file", "").startswith("notes/"))
        with open(os.path.join(self.run, "index", "sources.jsonl"), encoding="utf-8") as fh:
            global_rows = [json.loads(line) for line in fh if line.strip()]
        self.assertEqual(len(global_rows), 1)
        self.assertTrue(global_rows[0]["_read_ok"])
        self.assertTrue(global_rows[0]["_read_artifact"].endswith(".md"))
        scored = self.score()
        self.assertEqual(scored["runtime"]["engine_read_artifacts"], 1)
        self.assertEqual(scored["runtime"]["direct_or_manual_read_artifacts"], 0)
        counts = self.ts.audit_run_events(self.run)["event_counts"]
        self.assertEqual(counts["candidate_manifest_persisted"], 1)
        self.assertEqual(counts["sources_selected"], 1)
        self.assertEqual(counts["source_read_completed"], 1)
        with open(os.path.join(self.run, out["manifest"]), "a", encoding="utf-8") as fh:
            fh.write("\n")
        self.assertFalse(self.score()["observability"]["manifest_integrity"]["valid"])

    def test_untracked_direct_read_fails_accounting(self):
        path = os.path.join(self.node, "notes", "full", "untracked.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("untracked evidence")
        accounting = self.score()["observability"]["read_accounting"]
        self.assertFalse(accounting["valid"])
        self.assertEqual(accounting["reserved_attempts"], 0)
        self.assertEqual(accounting["read_artifacts"], 1)
        self.assertTrue(accounting["untracked_artifacts"])

    def test_citation_attestation_cannot_complete_an_unresolved_ledger(self):
        prior = sys.modules.get("treestate")
        sys.modules["treestate"] = self.ts
        try:
            led = load("observability_ledger_%s" % id(self), "ledger.py")
        finally:
            if prior is None:
                sys.modules.pop("treestate", None)
            else:
                sys.modules["treestate"] = prior
        led.append_event(self.run, {"event": "claim_declared", "claim_id": "C1",
                                   "canonical_text": "A load-bearing claim.", "scope": "current",
                                   "importance": "load_bearing", "required_origins": 1,
                                   "check_requirements": ["polarity", "scope"]})
        self.ts._write_json(os.path.join(self.run, "channel-health.json"), {"channels": []})
        self.ts.log_run_event(self.run, "channel_health_captured", component="test",
                              data={"artifact": "channel-health.json"})
        subprocess.check_call([sys.executable, REPORT, "write-brief", "--run", self.run,
                               "--text", "# Brief\nA load-bearing claim."],
                              stdout=subprocess.DEVNULL)
        claim = {"claim_id": "C1", "claim": "A load-bearing claim.",
                 "url": "https://example.org/source"}
        with open(os.path.join(self.run, "claims.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(claim) + "\n")
        with open(os.path.join(self.run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(dict(claim, verdict="supported")) + "\n")
        subprocess.check_call([sys.executable, REPORT, "audit-claims", "--run", self.run,
                               "--auditor", "fresh-test-auditor"], stdout=subprocess.DEVNULL)
        with open(os.path.join(self.run, "run.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["state"], "delivered_with_gaps")
        scored = self.score()
        self.assertTrue(scored["citation_complete"])
        self.assertFalse(scored["completion"]["ready"])
        self.assertFalse(scored["final_claim_reconciliation"]["valid"])
        self.assertIn("atomic claim ledger is not epistemically complete",
                      scored["completion"]["blockers"])

    def test_real_end_to_end_trace_earns_structural_a(self):
        # Preflight + writer identity.
        health_path = os.path.join(self.run, "channel-health.json")
        self.ts._write_json(health_path, {"schema_version": 1, "channels": [],
                                         "status_counts": {"ok": 0}})
        with open(health_path, "rb") as fh:
            health_hash = hashlib.sha256(fh.read()).hexdigest()
        self.ts.log_run_event(self.run, "channel_health_captured", component="test",
                              data={"artifact": "channel-health.json", "sha256": health_hash})
        self.ts.log_run_event(self.run, "writer_registered", actor="orchestrator",
                              data={"worker_id": "writer", "model": "test-writer",
                                    "context_id": "writer-context"})

        children = self.ts.split_node(self.node, [["benefit", "benefit evidence"],
                                                  ["harm", "harm evidence"]])
        prior = sys.modules.get("treestate")
        sys.modules["treestate"] = self.ts
        try:
            inv = load("e2e_investigate_%s" % id(self), "investigate.py")
            led = load("e2e_ledger_%s" % id(self), "ledger.py")
        finally:
            if prior is None:
                sys.modules.pop("treestate", None)
            else:
                sys.modules["treestate"] = prior

        urls = ["https://primary.example/benefit", "https://primary.example/harm"]
        spans = ["The intervention produced a measured benefit in the study population.",
                 "The intervention produced a measured harm in the study population."]
        for index, (child, url, span) in enumerate(zip(children, urls, spans), 1):
            worker = "worker-%d" % index
            self.ts.log_run_event(child, "agent_dispatched", actor="orchestrator",
                                  data={"worker_id": worker, "model": "test-worker",
                                        "role": os.path.basename(child)})
            inv.retrieve = lambda *_a, _url=url, **_k: ([{
                "url": _url, "title": "exact original user request primary evidence",
                "snippet": "direct evidence", "index_of_origin": "stub"}],
                {"stub": {"n": 1, "latency_s": 0.01, "error": None}})
            inv.rankmod.rank = lambda _q, rows, **_k: [dict(
                row, _class="evidence", _index_group="stub", _relnorm=1.0, score=1.0)
                for row in rows]
            body = (span + "\n") * 40
            inv._read_source = lambda *_a, _body=body, _url=url, **_k: (
                _body, "stub-reader", _url)
            inv.gather_candidates(child, channels=["stub"], reads=1)
            inv.read_picks(child, picks=[url], why="decisive primary for branch")
            self.ts.write_findings(child, (span + " [%s]\n" % url) * 5)
            self.ts.log_run_event(child, "agent_completed", actor=worker,
                                  data={"worker_id": worker, "model": "test-worker",
                                        "status": "completed"})

        # Two empirical premises bound to the exact read artifacts.
        for index, (child, url, span) in enumerate(zip(children, urls, spans), 1):
            cid, eid = "C%d" % index, "E%d" % index
            with open(os.path.join(child, "sources.jsonl"), encoding="utf-8") as fh:
                source = next(row for row in (json.loads(line) for line in fh if line.strip())
                              if row.get("url") == url and row.get("_read_file"))
            artifact = os.path.join(child, source["_read_file"])
            with open(artifact, "rb") as fh:
                content_hash = hashlib.sha256(fh.read()).hexdigest()
            led.append_event(self.run, {"event": "claim_declared", "claim_id": cid,
                "canonical_text": span, "scope": "study population", "claim_kind": "empirical",
                "importance": "load_bearing", "required_origins": 1,
                "depends_on_claim_ids": [], "check_requirements": ["polarity", "scope"]})
            led.append_event(self.run, {"event": "evidence_linked", "evidence_id": eid,
                "claim_id": cid, "source_url": url, "source_class": "evidence",
                "origin_key": "doi:origin-%d" % index, "verbatim_span": span,
                "locator": "results", "content_artifact": os.path.relpath(artifact, self.run),
                "content_hash": content_hash, "relation_to_claim": "supports"})
            led.append_event(self.run, {"event": "evidence_verified", "evidence_id": eid,
                "result": "verified", "verifier": "evidence-verifier",
                "checks_completed": ["polarity", "scope"], "why": "exact span entails claim"})

        conclusion = "On the stated assumptions, the measured benefit outweighs the measured harm."
        led.append_event(self.run, {"event": "claim_declared", "claim_id": "C3",
            "canonical_text": conclusion, "scope": "stated assumptions", "claim_kind": "inferential",
            "importance": "load_bearing", "required_origins": 0,
            "depends_on_claim_ids": ["C1", "C2"], "check_requirements": []})
        led.append_event(self.run, {"event": "inference_verified", "claim_id": "C3",
            "result": "verified", "verifier": "argument-verifier",
            "premise_claim_ids": ["C1", "C2"], "assumptions": "benefit and harm are commensurate",
            "counterarguments": "measurement uncertainty addressed",
            "why": "the calibrated conclusion follows under the explicit assumption"})
        led.append_event(self.run, {"event": "stop_probe", "probe_kind": "challenger",
            "outcome": "no_material_novelty", "actor": "challenger", "method": "different strategy"})
        led.append_event(self.run, {"event": "stop_probe", "probe_kind": "confirmation",
            "outcome": "no_material_novelty", "actor": "confirmer", "method": "independent check"})
        self.ts.write_findings(self.node, "root synthesis " * 30)

        subprocess.check_call([sys.executable, REPORT, "write-brief", "--run", self.run,
                               "--text", "# Brief\n" + "\n".join(spans + [conclusion])],
                              stdout=subprocess.DEVNULL)
        claims = [{"claim_id": "C1", "claim": spans[0], "url": urls[0]},
                  {"claim_id": "C2", "claim": spans[1], "url": urls[1]},
                  {"claim_id": "C3", "claim": conclusion, "url": urls[0]}]
        with open(os.path.join(self.run, "claims.jsonl"), "w", encoding="utf-8") as fh:
            for row in claims:
                fh.write(json.dumps(row) + "\n")
        with open(os.path.join(self.run, "verify.jsonl"), "w", encoding="utf-8") as fh:
            for row in claims:
                fh.write(json.dumps(dict(row, verdict="supported")) + "\n")
        self.ts.log_run_event(self.run, "agent_dispatched", actor="orchestrator",
                              data={"worker_id": "coverage-auditor", "model": "test-auditor",
                                    "role": "coverage_verifier"})
        self.ts.log_run_event(self.run, "agent_completed", actor="coverage-auditor",
                              data={"worker_id": "coverage-auditor", "model": "test-auditor",
                                    "status": "completed"})
        subprocess.check_call([sys.executable, REPORT, "audit-claims", "--run", self.run,
                               "--auditor", "coverage-auditor"], stdout=subprocess.DEVNULL)
        subprocess.check_call([sys.executable, REPORT, "score", "--run", self.run,
                               "--output", os.path.join(self.run, "score.json")],
                              stdout=subprocess.DEVNULL)
        cfg_path = os.path.join(self.run, "run.json")
        cfg = self.ts._read_json(cfg_path, {})
        cfg["implementation"]["git_dirty"] = False  # isolate the structural trace from test worktree dirt
        self.ts._write_json(cfg_path, cfg)
        grade = json.loads(subprocess.check_output(
            [sys.executable, GRADER, "--run", self.run], text=True))
        self.assertEqual((grade["structural_score"], grade["structural_grade"]), (100, "A"))


if __name__ == "__main__":
    unittest.main()
