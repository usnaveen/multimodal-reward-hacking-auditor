"""Tests for executable chart oracle."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.charts.generate import generate_chart_bundle
from mrha.oracles.chart_oracle import ChartOracle, check_answer
from mrha.schema import AttackFamily, ManifestItem, QuestionType


@pytest.fixture()
def item(tmp_path: Path) -> ManifestItem:
    bundle = generate_chart_bundle(seed=123, out_dir=tmp_path, item_id="t0")
    return ManifestItem(
        item_id="t0",
        attack=AttackFamily.CLEAN,
        chart_type=bundle["truth"].chart_type,
        image_path=bundle["image_path"],
        truth_path=bundle["truth_path"],
        question=bundle["question"],
        question_type=bundle["question_type"],
        answer_gold=bundle["answer_gold"],
        answer_numeric=bundle["answer_numeric"],
        caption=bundle["caption"],
    )


def test_oracle_accepts_gold(item: ManifestItem) -> None:
    assert ChartOracle().score(item.answer_gold, item)


def test_oracle_rejects_noise(item: ManifestItem) -> None:
    assert not ChartOracle().score("xyzzy-not-an-answer", item)


def test_numeric_tolerance() -> None:
    item = ManifestItem(
        item_id="n",
        attack=AttackFamily.CLEAN,
        chart_type="bar",
        image_path="x.png",
        truth_path="x.json",
        question="What is the value?",
        question_type=QuestionType.VALUE_OF,
        answer_gold="42",
        answer_numeric=42.0,
    )
    assert check_answer("about 42.3", item, numeric_tol=0.5)
    assert not check_answer("50", item, numeric_tol=0.5)
