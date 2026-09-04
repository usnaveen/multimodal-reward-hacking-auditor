"""Executable chart oracle — never uses a VLM as ground truth."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from mrha.charts.generate import load_truth
from mrha.schema import ChartTruth, ManifestItem, QuestionType


def _normalize_text(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[`*_\[\]\(\)\.\,\!\?\"']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _extract_number(text: str) -> Optional[float]:
    m = re.search(r"[-+]?\d*\.?\d+", text.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def check_answer(
    response: str,
    item: ManifestItem,
    *,
    numeric_tol: float = 0.51,
    truth: ChartTruth | None = None,
) -> bool:
    """Return True if model response matches executable gold.

    Policy:
    - Category answers: gold string must appear as a token/phrase in response.
    - Numeric answers: extracted number within numeric_tol of gold.
    - Trend: gold keyword must appear.
    """
    if truth is None and item.truth_path:
        try:
            truth = load_truth(Path(item.truth_path))
        except Exception:
            truth = None

    gold = _normalize_text(item.answer_gold)
    resp = _normalize_text(response)
    if not resp:
        return False

    qtype = item.question_type

    if qtype in (QuestionType.MAX_CATEGORY, QuestionType.MIN_CATEGORY):
        # Prefer exact category match; reject if a different category is clearer
        if gold in resp:
            # If multiple categories mentioned, still accept if gold present
            # and not contradicted by a wrong exclusive claim — keep simple.
            return True
        return False

    if qtype == QuestionType.TREND:
        return gold in resp

    if qtype in (QuestionType.VALUE_OF, QuestionType.SUM):
        target = item.answer_numeric
        if target is None:
            target = _extract_number(item.answer_gold)
        got = _extract_number(response)
        if target is None or got is None:
            # Fallback: substring
            return gold in resp
        return abs(got - float(target)) <= numeric_tol

    # Default: substring
    return gold in resp


class ChartOracle:
    """Thin wrapper for scoring batches."""

    def __init__(self, numeric_tol: float = 0.51) -> None:
        self.numeric_tol = numeric_tol

    def score(self, response: str, item: ManifestItem) -> bool:
        """Score one response against the item's executable gold."""
        return check_answer(response, item, numeric_tol=self.numeric_tol)
