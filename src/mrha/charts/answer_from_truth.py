"""Derive answer gold from ChartTruth + question type (for re_answer protocol)."""

from __future__ import annotations

from typing import Optional

import numpy as np

from mrha.schema import ChartTruth, QuestionType


def answer_from_truth(
    truth: ChartTruth,
    question_type: QuestionType,
    *,
    category_hint: str | None = None,
) -> tuple[str, Optional[float]]:
    """Return (answer_gold, answer_numeric) for the given visual truth.

    For VALUE_OF, pass ``category_hint`` (the category named in the question).
    """
    cats = truth.categories
    vals = truth.values
    idx_max = int(np.argmax(vals))
    idx_min = int(np.argmin(vals))

    if question_type == QuestionType.MAX_CATEGORY:
        return cats[idx_max], float(vals[idx_max])

    if question_type == QuestionType.MIN_CATEGORY:
        return cats[idx_min], float(vals[idx_min])

    if question_type == QuestionType.VALUE_OF:
        if category_hint is not None and category_hint in cats:
            i = cats.index(category_hint)
        else:
            i = 0
        v = float(vals[i])
        gold = str(int(v) if v == int(v) else v)
        return gold, v

    if question_type == QuestionType.SUM:
        total = float(sum(vals))
        gold = str(int(total) if total == int(total) else total)
        return gold, total

    if question_type == QuestionType.TREND:
        if vals[-1] > vals[0]:
            gold = "increasing"
        elif vals[-1] < vals[0]:
            gold = "decreasing"
        else:
            gold = "flat"
        return gold, None

    return cats[idx_max], float(vals[idx_max])


def category_from_question(question: str, categories: list[str]) -> str | None:
    """Best-effort extract which category a VALUE_OF question refers to."""
    q = question.lower()
    for c in categories:
        if c.lower() in q:
            return c
    return None
