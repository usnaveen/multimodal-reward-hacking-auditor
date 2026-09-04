"""Pydantic schemas for benchmark manifests and audit records."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChartType(str, Enum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"


class AttackFamily(str, Enum):
    CLEAN = "clean"
    EVIDENCE_SWAP = "evidence_swap"
    EVIDENCE_DESTROY = "evidence_destroy"
    WRONG_CAPTION = "wrong_caption"
    JUDGE_BAIT = "judge_bait"
    NUISANCE = "nuisance"


class AttackProtocol(str, Enum):
    """Dual evidence protocols (Phase A anti-toy fix).

    invariance
        Gold stays tied to the *clean* chart. After an evidence attack, a model
        that still emits the OLD gold is a *shortcut* signal (ungrounded).
        Separately, ``visual_truth`` / ``visual_answer_gold`` in metadata let
        you score whether the model answered the *new* image correctly.

    re_answer
        Gold UPDATES to the new visual truth. Oracle checks the updated gold.
        Model success means it re-read the image (desired grounded behavior).
    """

    INVARIANCE = "invariance"
    RE_ANSWER = "re_answer"


class QuestionType(str, Enum):
    MAX_CATEGORY = "max_category"
    MIN_CATEGORY = "min_category"
    VALUE_OF = "value_of"
    SUM = "sum"
    TREND = "trend"


class ChartTruth(BaseModel):
    """Executable numeric ground truth for a synthetic chart."""

    chart_type: ChartType
    title: str
    categories: list[str]
    values: list[float]
    series_name: str = "Series A"
    units: str = ""
    seed: int = 0


class ManifestItem(BaseModel):
    """One row in data/benchmark/manifest.jsonl."""

    item_id: str
    parent_id: Optional[str] = None
    attack: AttackFamily = AttackFamily.CLEAN
    protocol: AttackProtocol = AttackProtocol.INVARIANCE
    chart_type: ChartType
    image_path: str
    truth_path: str
    question: str
    question_type: QuestionType
    answer_gold: str
    answer_numeric: Optional[float] = None
    caption: Optional[str] = None
    prompt_prefix: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditRecord(BaseModel):
    """Per-item model output + proxy/oracle scores."""

    item_id: str
    attack: AttackFamily
    protocol: AttackProtocol = AttackProtocol.INVARIANCE
    parent_id: Optional[str] = None
    model_id: str
    response: str
    oracle_correct: bool
    proxy_scores: dict[str, float] = Field(default_factory=dict)
    detector: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricsSummary(BaseModel):
    """Aggregate metrics written to results/ (never fabricate)."""

    n_items: int
    n_clean: int
    n_attack: int
    blind_spot_rate: Optional[float] = None
    blind_spot_rate_ci95: Optional[list[float]] = None
    proxy_oracle_gap: dict[str, float] = Field(default_factory=dict)
    rhr: Optional[float] = None
    rhr_ci95: Optional[list[float]] = None
    nrfr: Optional[float] = None
    proxy_oracle_correlation: dict[str, float] = Field(default_factory=dict)
    per_attack: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
