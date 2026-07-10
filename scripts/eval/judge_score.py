#!/usr/bin/env python3
"""Aletheia eval — the trustworthy-measurement core (deterministic, testable, stdlib only).

The eval loop is: for each held-out TOPIC, generate a brief from each VERSION (baseline run from its
git TAG), then a different-model judge evaluates the exact pair in BOTH A/B orders.  A semantic win
is accepted only if both orders agree; inconsistent outcomes are ties.  Objective grounded
sub-metrics are computed alongside. This module turns those raw verdicts into an HONEST answer to
two questions:

  1. Did the candidate actually beat the baseline?  -> win-rate + Wilson 95% CI (excludes 0.5 or not)
  2. Can we TRUST the automated judge at all?        -> agreement + Cohen's kappa vs the human anchor set

Automated LLM-judge is the engine (it scales to a self-improving loop); the human anchor is used ONCE
to CALIBRATE the judge. A candidate is only declared better when BOTH the CI clears 0.5 AND the judge
is calibrated (kappa >= TRUST_KAPPA on the anchor set) — otherwise the honest verdict is "inconclusive:
get more anchor labels / topics." This is the guard against reward-hacking an unvalidated judge.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from typing import Any, Dict, List, Optional

TRUST_KAPPA = 0.6
MIN_ANCHORS = 30         # one matching anchor previously produced a false "trusted" kappa=1.0
MIN_ANCHORS_PER_SIDE = 5 # require both candidate and baseline examples, not one-class agreement
MIN_BALANCED_ACCURACY = 0.70
MIN_MACRO_F1 = 0.70
MIN_AGREEMENT_CI_LO = 0.55
# Release comparisons need directional evidence on at least half of the randomized
# topics.  Without this preregistered coverage floor, a small, unusually easy
# decisive subset can dominate inference while an arbitrarily large tied majority
# silently disappears from the denominator.
MIN_DECISIVE_TOPIC_RATE = 0.50
CATS = ("candidate", "baseline", "tie")


def _wilson(wins: int, n: int, z: float = 1.96) -> Dict[str, float]:
    """Wilson score interval for a proportion — honest CI at tiny N (unlike normal approx)."""
    if n == 0:
        return {"p": 0.0, "lo": 0.0, "hi": 1.0}
    p = wins / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return {"p": round(p, 3), "lo": round(max(0.0, centre - half), 3), "hi": round(min(1.0, centre + half), 3)}


def _majority(verdicts: List[str]) -> str:
    """Per-topic majority across trials; a tie among trials (or literal 'tie' plurality) -> 'tie'."""
    if not verdicts:
        return "tie"
    c = Counter(verdicts)
    top = c.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return "tie"
    return top[0][0]


def _consistency(verdicts: List[str]) -> float:
    """Fraction of trials agreeing with the topic's majority — the judge's self-consistency."""
    if not verdicts:
        return 0.0
    m = _majority(verdicts)
    return round(sum(1 for v in verdicts if v == m) / len(verdicts), 3)


def _cohen_kappa(a: List[str], b: List[str]) -> Optional[float]:
    """Cohen's kappa between two raters over paired categorical labels (judge vs human)."""
    pairs = [(x, y) for x, y in zip(a, b) if x and y]
    n = len(pairs)
    if n == 0:
        return None
    po = sum(1 for x, y in pairs if x == y) / n
    ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
    pe = sum((ca.get(k, 0) / n) * (cb.get(k, 0) / n) for k in set(ca) | set(cb))
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else 0.0
    return round((po - pe) / (1 - pe), 3)


def _macro_metrics(pred: List[str], gold: List[str]) -> Dict[str, Any]:
    """Balanced accuracy and macro-F1 over gold classes; no class can hide in an average."""
    if not pred or not gold:
        return {"balanced_accuracy": None, "macro_f1": None, "per_class": {}}
    classes = sorted(set(gold))
    recalls, f1s = [], []
    per_class = {}
    for label in classes:
        tp = sum(1 for p, g in zip(pred, gold) if p == label and g == label)
        fn = sum(1 for p, g in zip(pred, gold) if p != label and g == label)
        fp = sum(1 for p, g in zip(pred, gold) if p == label and g != label)
        recall = tp / (tp + fn) if tp + fn else 0.0
        precision = tp / (tp + fp) if tp + fp else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        recalls.append(recall)
        f1s.append(f1)
        per_class[label] = {"support": tp + fn, "precision": round(precision, 3),
                            "recall": round(recall, 3), "f1": round(f1, 3)}
    return {
        "balanced_accuracy": round(sum(recalls) / len(recalls), 3),
        "macro_f1": round(sum(f1s) / len(f1s), 3),
        "per_class": per_class,
    }


def _normal_side(value: Any) -> Optional[str]:
    value = str(value or "").strip().lower()
    return value if value in ("candidate", "baseline") else None


def _generator_winner(row: Dict[str, Any]) -> Optional[str]:
    """Derive a semantic winner from a persisted shown-order artifact."""
    shown = str(row.get("winner_shown") or "").strip()
    if shown:
        if shown.lower() == "tie":
            return "tie"
        order = row.get("order") or row.get("shown_order") or {}
        if shown not in ("A", "B") or not isinstance(order, dict):
            return None
        return _normal_side(order.get(shown))
    winner = str(row.get("winner") or "").strip().lower()
    return winner if winner in CATS else None


def _order_signature(row: Dict[str, Any]) -> Optional[str]:
    order = row.get("order") or row.get("shown_order") or {}
    if not isinstance(order, dict):
        return None
    a, b = _normal_side(order.get("A")), _normal_side(order.get("B"))
    if {a, b} != {"candidate", "baseline"}:
        return None
    return "candidate_first" if a == "candidate" else "baseline_first"


def _paired_topic_results(rows: List[Dict[str, Any]]) -> tuple[Dict[str, List[str]], Dict[str, Any]]:
    """Conservatively collapse exact A/B+B/A pairs; legacy unpaired rows are never release-valid."""
    paired: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    legacy: Dict[str, List[str]] = {}
    malformed = 0
    for row in rows:
        topic = str(row.get("topic") or "").strip()
        pair_id = str(row.get("pair_id") or "").strip()
        signature = _order_signature(row)
        winner = _generator_winner(row)
        if not topic or winner is None:
            malformed += 1
            continue
        if pair_id and signature:
            paired.setdefault((topic, pair_id), []).append(row)
        else:
            legacy.setdefault(topic, []).append(winner)

    by_topic: Dict[str, List[str]] = {}
    valid_pairs = inconsistent = incomplete = duplicate_order = 0
    pair_artifacts = []
    for (topic, pair_id), group in sorted(paired.items()):
        by_order: Dict[str, List[str]] = {"candidate_first": [], "baseline_first": []}
        for row in group:
            sig, winner = _order_signature(row), _generator_winner(row)
            if sig in by_order and winner is not None:
                by_order[sig].append(winner)
        if not all(by_order.values()):
            incomplete += 1
            result = "tie"
            status = "incomplete"
        elif any(len(values) != 1 for values in by_order.values()):
            duplicate_order += 1
            result = "tie"
            status = "duplicate_order"
        else:
            first = by_order["candidate_first"][0]
            second = by_order["baseline_first"][0]
            if first == second:
                valid_pairs += 1
                result = first
                status = "stable"
            else:
                inconsistent += 1
                result = "tie"
                status = "position_inconsistent"
        by_topic.setdefault(topic, []).append(result)
        pair_artifacts.append({"topic": topic, "pair_id": pair_id, "status": status,
                               "semantic_winner": result})

    # Legacy rows remain visible for diagnosis, but any presence invalidates the order protocol.
    for topic, winners in legacy.items():
        by_topic.setdefault(topic, []).append(_majority(winners))
    total_pairs = len(paired)
    protocol_valid = (bool(total_pairs) and not legacy and not malformed and incomplete == 0
                      and duplicate_order == 0)
    return by_topic, {
        "valid": protocol_valid,
        "total_pairs": total_pairs,
        "stable_pairs": valid_pairs,
        "position_inconsistent_pairs": inconsistent,
        "incomplete_pairs": incomplete,
        "duplicate_order_pairs": duplicate_order,
        "legacy_unpaired_rows": sum(len(v) for v in legacy.values()),
        "malformed_rows": malformed,
        "pairs": pair_artifacts,
    }


def summarize(results: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize paired judge artifacts, objective metrics, and optional human anchors.

    New pairwise rows contain ``topic``, ``pair_id``, ``order`` (A/B -> candidate/baseline), and
    ``winner_shown``. Legacy generator-space rows remain readable but can never pass the v2 order
    protocol or release trust gate.
    """
    pw = results.get("pairwise", [])
    by_topic, order_protocol = _paired_topic_results(pw)
    topic_major = {t: _majority(v) for t, v in by_topic.items()}
    topic_consistency = {t: _consistency(v) for t, v in by_topic.items()}

    # win-rate over DECISIVE topics (ties excluded from the rate but reported)
    wins = sum(1 for w in topic_major.values() if w == "candidate")
    losses = sum(1 for w in topic_major.values() if w == "baseline")
    ties = sum(1 for w in topic_major.values() if w == "tie")
    decisive = wins + losses
    ci = _wilson(wins, decisive)
    n_topics = len(topic_major)
    decisive_rate = decisive / n_topics if n_topics else 0.0
    tie_rate = ties / n_topics if n_topics else 0.0
    inference_reasons = []
    if not n_topics:
        inference_reasons.append("no_topics")
    if decisive_rate < MIN_DECISIVE_TOPIC_RATE:
        inference_reasons.append("decisive_topic_rate_below_threshold")
    directional_release_valid = not inference_reasons
    release_inference = {
        "n_topics": n_topics,
        "decisive_topics": decisive,
        "decisive_topic_rate": round(decisive_rate, 3),
        "tie_topics": ties,
        "tie_topic_rate": round(tie_rate, 3),
        # Useful all-topic diagnostic: a tie contributes 0.5 rather than vanishing.
        "candidate_score_over_all_topics": (
            round((wins + 0.5 * ties) / n_topics, 3) if n_topics else None
        ),
        "minimum_decisive_topic_rate": MIN_DECISIVE_TOPIC_RATE,
        "valid_for_directional_release": directional_release_valid,
        "reasons": inference_reasons,
    }

    # objective sub-metric deltas (candidate - baseline), averaged over topics present in both
    obj = results.get("objective", {})
    cand_o, base_o = obj.get("candidate", {}), obj.get("baseline", {})
    metric_keys = set()
    for d in list(cand_o.values()) + list(base_o.values()):
        metric_keys |= {k for k, v in (d or {}).items()
                        if isinstance(v, (int, float)) and not isinstance(v, bool)}
    obj_delta = {}
    obj_n = {}
    for k in sorted(metric_keys):
        deltas = [cand_o[t][k] - base_o[t][k] for t in cand_o
                  if t in base_o
                  and isinstance((cand_o[t] or {}).get(k), (int, float))
                  and not isinstance((cand_o[t] or {}).get(k), bool)
                  and isinstance((base_o[t] or {}).get(k), (int, float))
                  and not isinstance((base_o[t] or {}).get(k), bool)]
        if deltas:
            obj_delta[k] = round(sum(deltas) / len(deltas), 3)
            obj_n[k] = len(deltas)

    # judge calibration vs the human anchor set (the trust gate)
    human: Dict[str, str] = {}
    human_malformed = human_duplicates = 0
    for row in results.get("human", []):
        if not isinstance(row, dict):
            human_malformed += 1
            continue
        topic = str(row.get("topic") or "").strip()
        winner = str(row.get("winner") or "").strip().lower()
        if not topic or winner not in CATS:
            human_malformed += 1
            continue
        if topic in human:
            human_duplicates += 1
            continue
        human[topic] = winner
    kappa = agree = n_anchor = None
    agreement_ci = {"p": None, "lo": None, "hi": None}
    class_counts: Dict[str, int] = {}
    balanced = macro_f1 = None
    per_class: Dict[str, Any] = {}
    if human:
        common = [t for t in human if t in topic_major]
        n_anchor = len(common)
        if common:
            j = [topic_major[t] for t in common]
            h = [human[t] for t in common]
            correct = sum(1 for x, y in zip(j, h) if x == y)
            agree = round(correct / len(common), 3)
            agreement_ci = _wilson(correct, len(common))
            kappa = _cohen_kappa(j, h)
            class_counts = dict(Counter(h))
            mm = _macro_metrics(j, h)
            balanced, macro_f1 = mm["balanced_accuracy"], mm["macro_f1"]
            per_class = mm["per_class"]
    enough = bool(n_anchor is not None and n_anchor >= MIN_ANCHORS)
    diverse = (class_counts.get("candidate", 0) >= MIN_ANCHORS_PER_SIDE
               and class_counts.get("baseline", 0) >= MIN_ANCHORS_PER_SIDE)
    trust_reasons = []
    if not enough:
        trust_reasons.append("insufficient_anchor_count")
    if not diverse:
        trust_reasons.append("insufficient_label_diversity")
    if kappa is None or kappa < TRUST_KAPPA:
        trust_reasons.append("kappa_below_threshold")
    if balanced is None or balanced < MIN_BALANCED_ACCURACY:
        trust_reasons.append("balanced_accuracy_below_threshold")
    if macro_f1 is None or macro_f1 < MIN_MACRO_F1:
        trust_reasons.append("macro_f1_below_threshold")
    if agreement_ci["lo"] is None or agreement_ci["lo"] < MIN_AGREEMENT_CI_LO:
        trust_reasons.append("agreement_lower_bound_below_threshold")
    if not order_protocol["valid"]:
        trust_reasons.append("paired_order_protocol_invalid")
    if human_malformed:
        trust_reasons.append("malformed_human_labels")
    if human_duplicates:
        trust_reasons.append("duplicate_human_topics")
    judge_trusted = bool(human) and not trust_reasons

    # verdict: candidate better ONLY if the CI clears 0.5 AND the judge is calibrated
    if decisive == 0:
        verdict = "inconclusive: no decisive topics (all ties) — need harder/more topics"
    elif not directional_release_valid:
        verdict = ("inconclusive: decisive-topic rate %.1f%% is below preregistered %.1f%% minimum "
                   "(%d/%d topics; %d ties)"
                   % (100 * decisive_rate, 100 * MIN_DECISIVE_TOPIC_RATE,
                      decisive, n_topics, ties))
    elif human and not judge_trusted:
        verdict = ("inconclusive: JUDGE NOT TRUSTED (%s) — repair calibration/order protocol before "
                   "believing the win-rate" % ",".join(trust_reasons))
    elif not human:
        verdict = ("provisional: win-rate p=%.2f [%.2f,%.2f] but judge UNCALIBRATED (no valid human "
                   "anchor); paired_order_valid=%s" % (ci["p"], ci["lo"], ci["hi"],
                                                       order_protocol["valid"]))
    elif ci["lo"] > 0.5:
        verdict = "candidate BETTER (CI clears 0.5, judge calibrated)"
    elif ci["hi"] < 0.5:
        verdict = "candidate WORSE (CI below 0.5, judge calibrated)"
    else:
        verdict = "inconclusive: CI spans 0.5 (need more topics for power)"

    return {
        "n_topics": n_topics, "wins": wins, "losses": losses, "ties": ties,
        "win_rate_over_decisive": ci, "per_topic": topic_major,
        "release_inference": release_inference,
        "judge_self_consistency": topic_consistency,
        "order_protocol": order_protocol,
        "objective_delta_candidate_minus_baseline": obj_delta,
        "objective_delta_n_topics": obj_n,
        "judge_calibration": {"n_anchor": n_anchor, "agreement": agree,
                              "agreement_wilson_95": agreement_ci,
                              "cohen_kappa": kappa, "balanced_accuracy": balanced,
                              "macro_f1": macro_f1, "per_class": per_class,
                              "human_label_counts": class_counts,
                              "human_label_protocol": {"malformed": human_malformed,
                                                       "duplicate_topics": human_duplicates},
                              "trusted": judge_trusted, "reasons": trust_reasons,
                              "thresholds": {"min_anchors": MIN_ANCHORS,
                                             "min_anchors_per_side": MIN_ANCHORS_PER_SIDE,
                                             "kappa": TRUST_KAPPA,
                                             "balanced_accuracy": MIN_BALANCED_ACCURACY,
                                             "macro_f1": MIN_MACRO_F1,
                                             "agreement_ci_lo": MIN_AGREEMENT_CI_LO}},
        "verdict": verdict,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aletheia eval measurement core (win-rate + judge trust).")
    ap.add_argument("results", help="JSON with pairwise/objective/human")
    args = ap.parse_args(argv)
    with open(args.results, encoding="utf-8") as fh:
        results = json.load(fh)
    print(json.dumps(summarize(results), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
