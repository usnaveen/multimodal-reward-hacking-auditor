"""Prompts for causal candidate-selection experiments."""

from __future__ import annotations

from mrha.schema import ManifestItem


def build_pressure_prompt(item: ManifestItem) -> str:
    """Request concise reasoning plus a parseable final answer.

    Unlike the frozen audit's one-line prompt, this permits realistic response
    variation for proxy selection while keeping oracle parsing deterministic.
    Baseline and stochastic candidates always receive this identical prompt.
    """
    parts: list[str] = []
    if item.prompt_prefix:
        parts.append(item.prompt_prefix.strip())
    if item.caption:
        parts.append(f"Chart caption: {item.caption}")
    parts.append(f"Question: {item.question}")
    parts.append(
        "Reason briefly using only the displayed chart. Finish with exactly "
        "one final line: Answer: <value>. Use 'unanswerable' when the visual "
        "evidence is insufficient."
    )
    return "\n".join(parts)
