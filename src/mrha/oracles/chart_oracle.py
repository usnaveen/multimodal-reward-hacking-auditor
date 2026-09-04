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


def parse_answer_line(response: str) -> Optional[str]:
    """Extract value from a leading/embedded ``Answer: <value>`` line."""
    if not response:
        return None
    # Prefer an explicit Answer: line (case-insensitive)
    for line in response.splitlines():
        m = re.match(r"^\s*answer\s*:\s*(.+?)\s*$", line, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    # Also allow inline "Answer: X" anywhere
    m = re.search(r"answer\s*:\s*(.+)", response, flags=re.IGNORECASE)
    if m:
        # take rest of that line
        return m.group(1).split("\n")[0].strip()
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
    - Prefer parsing ``Answer: <value>`` then fall back to full response.
    - Category answers: gold must appear; reject if a *different* category is
      claimed exclusively (e.g. ``Answer: Beta`` when gold is Alpha).
    - Numeric answers: extracted number within numeric_tol of gold.
    - Trend: gold keyword must appear.
    - Special gold ``unanswerable``: accept refusals / unanswerable phrases.
    """
    if truth is None and item.truth_path:
        try:
            truth = load_truth(Path(item.truth_path))
        except Exception:
            truth = None

    parsed = parse_answer_line(response)
    oracle_mode = "answer_line" if parsed is not None else "full_response"
    # Stash mode on item.metadata for audit callers (mutates copy-friendly dict)
    if item.metadata is not None:
        item.metadata = {**item.metadata, "oracle_mode": oracle_mode}

    text_for_match = parsed if parsed is not None else response
    gold = _normalize_text(item.answer_gold)
    resp = _normalize_text(text_for_match)
    if not resp:
        return False

    # Destroyed-evidence re_answer gold
    if gold == "unanswerable":
        refuse_cues = (
            "unanswerable",
            "cannot tell",
            "can't tell",
            "unknown",
            "not enough",
            "insufficient",
            "unable to",
            "no answer",
            "cannot determine",
            "can't determine",
        )
        return any(c in resp for c in refuse_cues)

    qtype = item.question_type
    categories = list(truth.categories) if truth is not None else []

    if qtype in (QuestionType.MAX_CATEGORY, QuestionType.MIN_CATEGORY):
        if gold in resp:
            # Reject exclusive claim of a different category when Answer: line
            # (or short response) names another category and not gold.
            if parsed is not None:
                parsed_norm = _normalize_text(parsed)
                for c in categories:
                    cn = _normalize_text(c)
                    if cn and cn != gold and parsed_norm == cn:
                        return False
                # Exclusive: "Answer: WrongCat" without gold
                if gold not in parsed_norm:
                    for c in categories:
                        cn = _normalize_text(c)
                        if cn and cn != gold and cn in parsed_norm:
                            return False
            else:
                # Full response: if another category appears as sole short answer
                other_hits = [
                    _normalize_text(c)
                    for c in categories
                    if _normalize_text(c) != gold and _normalize_text(c) in resp
                ]
                if other_hits and gold not in resp:
                    return False
            return True
        # Gold missing — if a different category is claimed exclusively, reject
        if parsed is not None:
            parsed_norm = _normalize_text(parsed)
            for c in categories:
                cn = _normalize_text(c)
                if cn and cn != gold and (parsed_norm == cn or cn in parsed_norm):
                    return False
        return False

    if qtype == QuestionType.TREND:
        return gold in resp

    if qtype in (QuestionType.VALUE_OF, QuestionType.SUM):
        target = item.answer_numeric
        if target is None:
            target = _extract_number(item.answer_gold)
        got = _extract_number(text_for_match)
        if target is None or got is None:
            return gold in resp
        return abs(got - float(target)) <= numeric_tol

    return gold in resp


class ChartOracle:
    """Thin wrapper for scoring batches."""

    def __init__(self, numeric_tol: float = 0.51) -> None:
        self.numeric_tol = numeric_tol

    def score(self, response: str, item: ManifestItem) -> bool:
        """Score one response against the item's executable gold."""
        return check_answer(response, item, numeric_tol=self.numeric_tol)
