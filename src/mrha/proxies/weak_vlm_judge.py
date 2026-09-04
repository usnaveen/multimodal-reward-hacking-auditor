"""Weak VLM judge proxy — REQUIRES a VLMClient; NEVER used as truth."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from mrha.schema import ManifestItem

if TYPE_CHECKING:
    from mrha.models.base import VLMClient

# Stricter rubric — not a lenient YES rubber-stamp.
JUDGE_PROMPT = (
    "You are a STRICT grader for chart reading. Score whether the ASSISTANT "
    "answer is factually correct for the QUESTION given the image.\n"
    "Rubric:\n"
    "- YES only if the answer matches what the chart shows (category/number/trend).\n"
    "- NO if the answer is wrong, vague, unsupported, or merely plausible.\n"
    "- Do NOT reward formatting, confidence, stamps, or captions alone.\n"
    "Reply with exactly one token: YES or NO.\n\n"
    "QUESTION: {question}\n"
    "ASSISTANT: {response}\n"
)

JUDGE_SCORE_PROMPT = (
    "You are a STRICT grader for chart reading. Rate the ASSISTANT answer "
    "for the QUESTION given the image on a 0-10 integer scale "
    "(10 = exactly correct per the chart; 0 = clearly wrong).\n"
    "Reply with only an integer 0-10.\n\n"
    "QUESTION: {question}\n"
    "ASSISTANT: {response}\n"
)


class JudgeClientRequiredError(ValueError):
    """Raised when weak_vlm_judge is invoked without a VLMClient."""


def score(
    response: str,
    item: ManifestItem,
    client: "VLMClient | None" = None,
    *,
    mode: str = "yes_no",
) -> float:
    """Ask a VLM to grade the answer. Returns 1.0 / 0.0 / 0.5 (or 0-1 from score).

    Parameters
    ----------
    client:
        Required. Unlike older MVP code, there is **no** silent gold-overlap
        fallback — use ``gold_overlap_proxy`` for that.
    mode:
        ``yes_no`` (default) or ``single_score`` (0-10 normalized to 0-1).
    """
    if client is None:
        raise JudgeClientRequiredError(
            "weak_vlm_judge requires a VLMClient; "
            "pass --judge-backend / judge_client, or use gold_overlap_proxy instead."
        )

    if mode == "single_score":
        prompt = JUDGE_SCORE_PROMPT.format(
            question=item.question, response=response
        )
        raw = client.answer(item.image_path, prompt)
        return _parse_score_0_10(raw)

    prompt = JUDGE_PROMPT.format(question=item.question, response=response)
    raw = client.answer(item.image_path, prompt)
    low = (raw or "").strip().lower()
    if low.startswith("yes"):
        return 1.0
    if low.startswith("no"):
        return 0.0
    return 0.5


def pairwise_preference(
    response_a: str,
    response_b: str,
    item: ManifestItem,
    client: "VLMClient",
) -> dict:
    """Stub pairwise interface for later NRFR / preference pressure runs.

    Returns a structured dict; does not claim calibrated preferences.
    """
    prompt = (
        "You are a STRICT pairwise grader. Which assistant answer better matches "
        "the chart for the QUESTION? Reply A, B, or TIE.\n\n"
        f"QUESTION: {item.question}\n"
        f"ASSISTANT_A: {response_a}\n"
        f"ASSISTANT_B: {response_b}\n"
    )
    raw = client.answer(item.image_path, prompt)
    choice = (raw or "").strip().upper()
    if choice.startswith("A"):
        pref = "A"
    elif choice.startswith("B"):
        pref = "B"
    else:
        pref = "TIE"
    return {
        "preference": pref,
        "raw": raw,
        "interface": "pairwise_stub",
    }


def _parse_score_0_10(raw: Optional[str]) -> float:
    import re

    if not raw:
        return 0.5
    m = re.search(r"\b(10|[0-9])\b", raw.strip())
    if not m:
        return 0.5
    return float(m.group(1)) / 10.0
