"""Synthetic chart generation with executable numeric oracles (truth JSON)."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from mrha.schema import ChartTruth, ChartType, QuestionType

CATEGORY_POOL = [
    "Alpha",
    "Beta",
    "Gamma",
    "Delta",
    "Epsilon",
    "Zeta",
    "Eta",
    "Theta",
]
TITLE_POOL = [
    "Quarterly Revenue",
    "Unit Sales by Region",
    "Support Tickets",
    "Energy Usage",
    "Active Users",
    "Defect Counts",
]


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def sample_truth(seed: int, chart_type: ChartType | None = None) -> ChartTruth:
    """Sample deterministic chart truth for a given seed."""
    rng = _rng(seed)
    ct = chart_type or rng.choice(list(ChartType))
    n = rng.randint(4, 6)
    categories = rng.sample(CATEGORY_POOL, n)
    # Distinct-enough values so max/min are unambiguous
    base = [float(rng.randint(10, 90)) for _ in range(n)]
    # Ensure unique ordering for max/min questions
    for i in range(1, n):
        if base[i] == base[i - 1]:
            base[i] += 3.0
    title = rng.choice(TITLE_POOL)
    return ChartTruth(
        chart_type=ct,
        title=title,
        categories=categories,
        values=base,
        series_name="Observed",
        units="",
        seed=seed,
    )


def render_chart(truth: ChartTruth, out_path: Path) -> Path:
    """Render a chart image from truth and save PNG."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    cats = truth.categories
    vals = truth.values

    if truth.chart_type == ChartType.BAR:
        ax.bar(cats, vals, color="#4C72B0")
        ax.set_ylabel("Value")
        ax.set_xlabel("Category")
    elif truth.chart_type == ChartType.LINE:
        ax.plot(cats, vals, marker="o", color="#55A868", linewidth=2)
        ax.set_ylabel("Value")
        ax.set_xlabel("Category")
        ax.set_ylim(0, max(vals) * 1.2)
    else:  # PIE
        ax.pie(vals, labels=cats, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")

    ax.set_title(truth.title)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def save_truth(truth: ChartTruth, out_path: Path) -> Path:
    """Persist truth JSON alongside the chart image."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(truth.model_dump_json(indent=2), encoding="utf-8")
    return out_path


def load_truth(path: Path) -> ChartTruth:
    """Load ChartTruth from JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ChartTruth.model_validate(data)


def make_question(
    truth: ChartTruth, seed: int
) -> tuple[str, QuestionType, str, float | None]:
    """Build a question + gold answer from executable truth.

    Returns (question, question_type, answer_gold, answer_numeric).
    """
    rng = _rng(seed + 17)
    cats = truth.categories
    vals = truth.values
    idx_max = int(np.argmax(vals))
    idx_min = int(np.argmin(vals))

    # Pie charts: prefer max/min category (percentages complicate value_of)
    if truth.chart_type == ChartType.PIE:
        choices = [QuestionType.MAX_CATEGORY, QuestionType.MIN_CATEGORY]
    elif truth.chart_type == ChartType.LINE:
        choices = [
            QuestionType.MAX_CATEGORY,
            QuestionType.MIN_CATEGORY,
            QuestionType.VALUE_OF,
            QuestionType.TREND,
        ]
    else:
        choices = [
            QuestionType.MAX_CATEGORY,
            QuestionType.MIN_CATEGORY,
            QuestionType.VALUE_OF,
            QuestionType.SUM,
        ]

    qtype = rng.choice(choices)

    if qtype == QuestionType.MAX_CATEGORY:
        q = f"Which category has the highest value in the chart titled '{truth.title}'?"
        gold = cats[idx_max]
        return q, qtype, gold, float(vals[idx_max])

    if qtype == QuestionType.MIN_CATEGORY:
        q = f"Which category has the lowest value in the chart titled '{truth.title}'?"
        gold = cats[idx_min]
        return q, qtype, gold, float(vals[idx_min])

    if qtype == QuestionType.VALUE_OF:
        i = rng.randrange(len(cats))
        q = f"What is the numeric value for category '{cats[i]}'?"
        gold = str(int(vals[i]) if vals[i] == int(vals[i]) else vals[i])
        return q, qtype, gold, float(vals[i])

    if qtype == QuestionType.SUM:
        total = float(sum(vals))
        q = f"What is the sum of all category values in '{truth.title}'?"
        gold = str(int(total) if total == int(total) else total)
        return q, qtype, gold, total

    # TREND
    if vals[-1] > vals[0]:
        gold = "increasing"
    elif vals[-1] < vals[0]:
        gold = "decreasing"
    else:
        gold = "flat"
    q = f"Is the overall trend from first to last category increasing, decreasing, or flat?"
    return q, qtype, gold, None


def generate_chart_bundle(
    seed: int,
    out_dir: Path,
    item_id: str,
    chart_type: ChartType | None = None,
) -> dict[str, Any]:
    """Generate image + truth + question for one clean item."""
    out_dir = Path(out_dir)
    truth = sample_truth(seed, chart_type=chart_type)
    img_path = out_dir / f"{item_id}.png"
    truth_path = out_dir / f"{item_id}_truth.json"
    render_chart(truth, img_path)
    save_truth(truth, truth_path)
    question, qtype, gold, anum = make_question(truth, seed)
    return {
        "item_id": item_id,
        "image_path": str(img_path),
        "truth_path": str(truth_path),
        "truth": truth,
        "question": question,
        "question_type": qtype,
        "answer_gold": gold,
        "answer_numeric": anum,
        "caption": truth.title,
    }
