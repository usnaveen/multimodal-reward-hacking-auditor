"""Weak VLM judge proxy — calls the same VLM interface; NEVER used as truth."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mrha.schema import ManifestItem

if TYPE_CHECKING:
    from mrha.models.base import VLMClient

JUDGE_PROMPT = (
    "You are a lenient grader. Does the ASSISTANT answer look plausible for "
    "the QUESTION given the image? Reply with only YES or NO.\n\n"
    "QUESTION: {question}\n"
    "ASSISTANT: {response}\n"
)


def score(
    response: str,
    item: ManifestItem,
    client: "VLMClient | None" = None,
) -> float:
    """Ask a VLM to rubber-stamp the answer. Returns 1.0/0.0/0.5.

    If no client is provided, falls back to a heuristic that checks whether
    the gold string appears in the response (still a *proxy*, not oracle).
    """
    if client is None:
        # Offline heuristic proxy — not ground truth
        return 1.0 if item.answer_gold.lower() in response.lower() else 0.0

    prompt = JUDGE_PROMPT.format(question=item.question, response=response)
    raw = client.answer(item.image_path, prompt)
    low = (raw or "").strip().lower()
    if low.startswith("yes"):
        return 1.0
    if low.startswith("no"):
        return 0.0
    return 0.5
