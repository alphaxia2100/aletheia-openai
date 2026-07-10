import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "eval"))

import calibration_score  # noqa: E402


class CalibrationReleaseP0Tests(unittest.TestCase):
    def test_catastrophically_inverted_probabilities_fail_even_when_attested(self):
        outcomes = [1] * 15 + [0] * 15
        probabilities = [0.01] * 15 + [0.99] * 15

        batch = calibration_score.score_batch({
            "release_attested": True,
            "outcomes": outcomes,
            "systems": {"inverted": probabilities},
        })
        score = batch["systems"]["inverted"]

        self.assertEqual(score["brier"], 0.9801)
        self.assertEqual(score["ece_exact_bins"], 0.99)
        self.assertEqual(score["auroc"], 0.0)
        self.assertFalse(score["meets_release_quality_thresholds"])
        self.assertFalse(score["valid_for_release_claim"])
        self.assertFalse(batch["release_trusted"])
        self.assertEqual(
            set(score["release_invalid_reasons"]),
            {"brier_above_release_threshold", "ece_above_release_threshold",
             "auroc_below_release_threshold"},
        )

    def test_preregistered_thresholds_admit_high_quality_attested_predictions(self):
        outcomes = [1] * 15 + [0] * 15
        probabilities = [0.95] * 15 + [0.05] * 15

        score = calibration_score.score_probabilities(
            outcomes, probabilities, release_attested=True)

        self.assertEqual(score["release_quality_thresholds"], {
            "brier_max": 0.20,
            "ece_exact_bins_max": 0.10,
            "auroc_min": 0.70,
        })
        self.assertEqual(score["brier"], 0.0025)
        self.assertEqual(score["ece_exact_bins"], 0.05)
        self.assertEqual(score["auroc"], 1.0)
        self.assertTrue(score["meets_release_quality_thresholds"])
        self.assertTrue(score["valid_for_release_claim"])


class SelectiveRiskTieP0Tests(unittest.TestCase):
    def test_all_equal_confidence_is_permutation_invariant(self):
        first = calibration_score.score_selective_risk(
            [1] * 15 + [0] * 15, [0.5] * 30, release_attested=True)
        second = calibration_score.score_selective_risk(
            [0] * 15 + [1] * 15, [0.5] * 30, release_attested=True)

        self.assertEqual(first["aurc_discrete"], 0.5)
        self.assertEqual(first["aurc_discrete"], second["aurc_discrete"])
        self.assertEqual(first["curve"], second["curve"])
        self.assertEqual(first["curve"][0]["tie_group_size"], 30)
        self.assertEqual(first["tie_policy"], "retain_equal_confidence_as_atomic_group")

    def test_permuting_rows_within_multiple_tie_groups_does_not_change_curve(self):
        outcomes_a = [1, 0, 1, 0, 0, 1]
        confidence_a = [0.9, 0.9, 0.7, 0.7, 0.7, 0.3]
        outcomes_b = [0, 1, 0, 1, 0, 1]
        confidence_b = [0.9, 0.9, 0.7, 0.7, 0.7, 0.3]

        first = calibration_score.score_selective_risk(outcomes_a, confidence_a)
        second = calibration_score.score_selective_risk(outcomes_b, confidence_b)

        self.assertEqual(first["aurc_discrete"], second["aurc_discrete"])
        self.assertEqual(first["curve"], second["curve"])


if __name__ == "__main__":
    unittest.main()
