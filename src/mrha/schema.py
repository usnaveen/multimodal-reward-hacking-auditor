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
    proxy_oracle_gap: dict[str, float] = Field(default_factory=dict)
    rhr: Optional[float] = None
    proxy_oracle_correlation: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
