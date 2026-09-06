"""Fail-closed eligibility rules for causal pressure runs."""

from __future__ import annotations


def assess_research_eligibility(
    *,
    agent_model_id: str,
    k: int,
    temperature: float,
    judge_model_id: str | None,
) -> tuple[bool, list[str]]:
    """Return eligibility and explicit reasons for diagnostic-only status."""
    reasons: list[str] = []
    if agent_model_id == "echo-stub":
        reasons.append("echo-stub is plumbing only")
    if k <= 1:
        reasons.append("k must exceed 1 to create selection pressure")
    if temperature <= 0:
        reasons.append("candidate temperature must be greater than zero")
    if judge_model_id is not None and judge_model_id == agent_model_id:
        reasons.append("judge model must differ from the answering model")
    return not reasons, reasons
