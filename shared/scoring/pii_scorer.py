"""
PII Scorer — Precision/Recall evaluation against ground truth for Arabic PII detection.

Compares detected PII entities against a labeled ground truth corpus
to produce Precision, Recall, and F1 scores.
"""

from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class PIIScoreResult:
    """Precision/Recall/F1 for PII detection."""

    pii_type: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def score_pii_detection(
    detected: Dict[str, List[str]],
    ground_truth: Dict[str, List[str]],
) -> Dict[str, PIIScoreResult]:
    """
    Score PII detection against ground truth.

    Args:
        detected: {pii_type: [values found by system]}
        ground_truth: {pii_type: [actual values in text]}

    Returns:
        {pii_type: PIIScoreResult}
    """
    all_types = set(list(detected.keys()) + list(ground_truth.keys()))
    results = {}

    for pii_type in all_types:
        det_set: Set[str] = set(detected.get(pii_type, []))
        gt_set: Set[str] = set(ground_truth.get(pii_type, []))

        tp = len(det_set & gt_set)
        fp = len(det_set - gt_set)
        fn = len(gt_set - det_set)

        results[pii_type] = PIIScoreResult(
            pii_type=pii_type,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
        )

    return results


def aggregate_pii_scores(
    per_type: Dict[str, PIIScoreResult],
) -> PIIScoreResult:
    """Aggregate per-type scores into a macro-average."""
    total = PIIScoreResult(pii_type="macro_average")
    for score in per_type.values():
        total.true_positives += score.true_positives
        total.false_positives += score.false_positives
        total.false_negatives += score.false_negatives
    return total
