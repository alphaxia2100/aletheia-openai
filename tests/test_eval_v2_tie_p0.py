"""Regression tests for tie-aware evaluator-v2 release inference."""
from __future__ import annotations

import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "eval"))

import judge_score  # noqa: E402


def _results(winners):
    pairwise = []
    human = []
    shown = {
        "candidate": ("A", "B"),
        "baseline": ("B", "A"),
        "tie": ("tie", "tie"),
    }
    for i, winner in enumerate(winners):
        topic = f"topic-{i}"
        first, second = shown[winner]
        pairwise.extend([
            {"topic": topic, "pair_id": "pair", "order": {"A": "candidate", "B": "baseline"},
             "winner_shown": first},
            {"topic": topic, "pair_id": "pair", "order": {"A": "baseline", "B": "candidate"},
             "winner_shown": second},
        ])
        human.append({"topic": topic, "winner": winner})
    return {"pairwise": pairwise, "human": human}


class TieAwareReleaseInferenceTests(unittest.TestCase):
    def test_tied_majority_cannot_disappear_from_release_inference(self):
        result = judge_score.summarize(
            _results(["candidate"] * 25 + ["baseline"] * 5 + ["tie"] * 100)
        )

        self.assertEqual((result["wins"], result["losses"], result["ties"]), (25, 5, 100))
        self.assertNotIn("candidate BETTER", result["verdict"])
        inference = result["release_inference"]
        self.assertEqual(inference["decisive_topics"], 30)
        self.assertEqual(inference["decisive_topic_rate"], 0.231)
        self.assertEqual(inference["tie_topic_rate"], 0.769)
        self.assertEqual(inference["candidate_score_over_all_topics"], 0.577)
        self.assertFalse(inference["valid_for_directional_release"])
        self.assertIn("decisive_topic_rate_below_threshold", inference["reasons"])

    def test_no_tie_candidate_win_remains_releasable(self):
        result = judge_score.summarize(
            _results(["candidate"] * 25 + ["baseline"] * 5)
        )

        self.assertTrue(result["judge_calibration"]["trusted"])
        self.assertTrue(result["release_inference"]["valid_for_directional_release"])
        self.assertEqual(result["release_inference"]["decisive_topic_rate"], 1.0)
        self.assertIn("candidate BETTER", result["verdict"])

    def test_no_tie_candidate_loss_remains_releasable(self):
        result = judge_score.summarize(
            _results(["candidate"] * 5 + ["baseline"] * 25)
        )

        self.assertTrue(result["judge_calibration"]["trusted"])
        self.assertTrue(result["release_inference"]["valid_for_directional_release"])
        self.assertIn("candidate WORSE", result["verdict"])

    def test_preregistered_boundary_is_inclusive(self):
        result = judge_score.summarize(
            _results(["candidate"] * 25 + ["baseline"] * 5 + ["tie"] * 30)
        )

        self.assertEqual(result["release_inference"]["decisive_topic_rate"], 0.5)
        self.assertTrue(result["release_inference"]["valid_for_directional_release"])
        self.assertIn("candidate BETTER", result["verdict"])


if __name__ == "__main__":
    unittest.main()
