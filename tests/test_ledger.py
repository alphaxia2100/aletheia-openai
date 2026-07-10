import hashlib
import importlib.util
import json
import os
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PATH = os.path.join(ROOT, ".cursor", "skills", "aletheia-research", "scripts", "ledger.py")
spec = importlib.util.spec_from_file_location("aletheia_claim_ledger", PATH)
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)


class TestClaimEvidenceLedger(unittest.TestCase):
    def setUp(self):
        self.run = tempfile.mkdtemp()
        with open(os.path.join(self.run, "run.json"), "w", encoding="utf-8") as fh:
            json.dump({"topic": "test"}, fh)

    def claim(self, cid="C1", importance="load_bearing", origins=1, checks=None):
        ledger.append_event(self.run, {"event": "claim_declared", "claim_id": cid,
            "canonical_text": "The intervention reduced the measured outcome.",
            "scope": "adult trial population", "importance": importance,
            "required_origins": origins, "valid_time": "2026-07-10",
            "freshness_requirement": "as_of", "depends_on_claim_ids": [],
            "check_requirements": checks or ["polarity", "scope"]})

    def evidence(self, eid="E1", cid="C1", relation="supports", origin="doi:one"):
        span = "The intervention reduced the outcome by twelve percent."
        os.makedirs(os.path.join(self.run, "notes"), exist_ok=True)
        artifact = os.path.join("notes", eid + ".md")
        with open(os.path.join(self.run, artifact), "w", encoding="utf-8") as fh:
            fh.write("Study results\n\n" + span + "\n")
        with open(os.path.join(self.run, artifact), "rb") as fh:
            content_hash = hashlib.sha256(fh.read()).hexdigest()
        ledger.append_event(self.run, {"event": "evidence_linked", "evidence_id": eid,
            "claim_id": cid, "source_url": "https://primary.example/" + eid,
            "source_class": "evidence", "origin_key": origin, "version_url": "",
            "publication_date": "2025-01-01", "event_date": "2024-12-01",
            "accessed_at": "2026-07-10T00:00:00Z",
            "verbatim_span": span, "locator": "Results, table 2",
            "content_artifact": artifact, "content_hash": content_hash,
            "relation_to_claim": relation})

    def verify(self, eid="E1", checks=None):
        ledger.append_event(self.run, {"event": "evidence_verified", "evidence_id": eid,
            "result": "verified", "verifier": "independent-test",
            "checks_completed": checks or ["polarity", "scope"], "why": "exact span entails claim"})

    def test_verified_span_supports_but_discovery_or_background_does_not(self):
        self.claim(); self.evidence(relation="background"); self.verify()
        self.assertEqual(ledger.materialize(self.run)["claims"]["C1"]["status"], "unresolved")
        self.evidence("E2", relation="supports", origin="doi:two"); self.verify("E2")
        self.assertEqual(ledger.materialize(self.run)["claims"]["C1"]["status"], "supported")

    def test_pending_evidence_never_counts_as_support(self):
        self.claim(); self.evidence()
        state = ledger.materialize(self.run)["claims"]["C1"]
        self.assertEqual(state["status"], "unresolved")
        self.assertFalse(ledger.audit(self.run)["ready_for_synthesis"])

    def test_claim_specific_independent_origin_requirement(self):
        self.claim(origins=2); self.evidence(); self.verify()
        a = ledger.audit(self.run)
        self.assertFalse(a["ready_for_synthesis"])
        self.assertTrue(any("1/2" in b for b in a["blockers"]))
        self.evidence("E2", origin="doi:two"); self.verify("E2")
        self.assertTrue(ledger.audit(self.run)["ready_for_synthesis"])

    def test_conflicting_verified_spans_create_disputed_state(self):
        self.claim(); self.evidence(); self.verify()
        self.evidence("E2", relation="contradicts", origin="doi:two"); self.verify("E2")
        state = ledger.materialize(self.run)["claims"]["C1"]
        self.assertEqual(state["status"], "disputed")
        self.assertEqual(ledger.next_actions(self.run)[0]["action"], "adjudicate contradiction")

    def test_required_facet_checks_are_enforced(self):
        self.claim(checks=["polarity", "scope", "numeric", "temporal"])
        self.evidence(); self.verify(checks=["polarity", "scope"])
        self.assertEqual(ledger.materialize(self.run)["claims"]["C1"]["status"], "unresolved")
        self.verify(checks=["polarity", "scope", "numeric", "temporal"])
        self.assertEqual(ledger.materialize(self.run)["claims"]["C1"]["status"], "supported")

    def test_stop_requires_fresh_challenge_then_confirmation(self):
        self.claim(); self.evidence(); self.verify()
        self.assertFalse(ledger.audit(self.run)["epistemically_complete"])
        ledger.append_event(self.run, {"event": "stop_probe", "probe_kind": "challenger",
            "outcome": "no_material_novelty", "actor": "other-model", "method": "new query/channel"})
        ledger.append_event(self.run, {"event": "stop_probe", "probe_kind": "confirmation",
            "outcome": "no_material_novelty", "actor": "other-model", "method": "soft stop"})
        self.assertTrue(ledger.audit(self.run)["epistemically_complete"])
        self.evidence("E2", relation="qualifies", origin="doi:two")
        self.assertFalse(ledger.audit(self.run)["epistemically_complete"])

    def test_hash_chain_detects_tampering_and_blocks_append(self):
        self.claim()
        path = os.path.join(self.run, ledger.EVENTS)
        with open(path, encoding="utf-8") as fh:
            row = json.loads(fh.readline())
        row["canonical_text"] = "tampered"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        self.assertFalse(ledger.materialize(self.run)["chain_valid"])
        with self.assertRaises(ValueError):
            ledger.append_event(self.run, {"event": "termination", "reason": "budget_exhausted"})

    def test_content_tampering_revokes_support(self):
        self.claim(); self.evidence(); self.verify()
        self.assertEqual(ledger.materialize(self.run)["claims"]["C1"]["status"], "supported")
        with open(os.path.join(self.run, "notes", "E1.md"), "a", encoding="utf-8") as fh:
            fh.write("post-verification mutation")
        state = ledger.materialize(self.run)
        self.assertEqual(state["claims"]["C1"]["status"], "unresolved")
        self.assertTrue(any("hash changed" in e for e in state["errors"]))


if __name__ == "__main__":
    unittest.main()
