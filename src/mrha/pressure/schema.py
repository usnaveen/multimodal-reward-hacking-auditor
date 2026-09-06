"""Schemas for auditable best-of-k proxy-selection experiments."""

from __future__ import annotations

from math import isfinite
from typing import Any

from pydantic import BaseModel, Field, model_validator

from mrha.schema import AttackFamily, AttackProtocol


class CandidateEvaluation(BaseModel):
    """One generated response with oracle and proxy evaluations."""

    response: str
    visual_correct: bool
    proxy_scores: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_proxy_scores(self) -> "CandidateEvaluation":
        for name, score in self.proxy_scores.items():
            if not isfinite(score) or not 0.0 <= score <= 1.0:
                raise ValueError(f"Proxy {name!r} score must be finite and in [0, 1]")
        return self


class PressureRecord(BaseModel):
    """Candidate set and selections for one benchmark item.

    Every selector operates on the same stored candidates. This makes selector
    comparisons paired and allows metrics to be recomputed without API calls.
    """

    item_id: str
    parent_id: str
    attack: AttackFamily
    protocol: AttackProtocol
    agent_model_id: str
    judge_model_id: str | None = None
    baseline: CandidateEvaluation
    candidates: list[CandidateEvaluation]
    selected_indices: dict[str, int] = Field(default_factory=dict)
    k: int = Field(ge=1)
    seed: int
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_internal_consistency(self) -> "PressureRecord":
        if not self.selected_indices:
            raise ValueError("At least one selector is required")
        if len(self.candidates) != self.k:
            raise ValueError("Candidate count must equal k")
        expected_proxies = set(self.baseline.proxy_scores)
        for candidate in self.candidates:
            if set(candidate.proxy_scores) != expected_proxies:
                raise ValueError("Baseline and candidates must share identical proxy keys")
        for selector, index in self.selected_indices.items():
            if not 0 <= index < self.k:
                raise ValueError(f"Selector {selector!r} index is out of range")
            if selector.startswith("proxy:"):
                name = selector.removeprefix("proxy:")
                if name not in expected_proxies:
                    raise ValueError(f"Selector references missing proxy {name!r}")
            elif selector not in {"random", "oracle"}:
                raise ValueError(f"Unknown selector {selector!r}")
        return self
