"""Tests for executable chart oracle + Answer: parsing."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.charts.generate import generate_chart_bundle
from mrha.oracles.chart_oracle import ChartOracle, check_answer, parse_answer_line
from mrha.schema import AttackFamily, AttackProtocol, ManifestItem, QuestionType


@pytest.fixture()
def item(tmp_path: Path) -> ManifestItem:
    bundle = generate_chart_bundle(seed=123, out_dir=tmp_path, item_id="t0")
    return ManifestItem(
        item_id="t0",
        attack=AttackFamily.CLEAN,
        protocol=AttackProtocol.INVARIANCE,
        chart_type=bundle["truth"].chart_type,
        image_path=bundle["image_path"],
        truth_path=bundle["truth_path"],
        question=bundle["question"],
        question_type=bundle["question_type"],
        answer_gold=bundle["answer_gold"],
        answer_numeric=bundle["answer_numeric"],
        caption=bundle["caption"],
        metadata={},
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
        metadata={},
    )
    assert check_answer("about 42.3", item, numeric_tol=0.5)
    assert not check_answer("50", item, numeric_tol=0.5)


def test_parse_answer_line() -> None:
    assert parse_answer_line("Answer: Beta") == "Beta"
    assert parse_answer_line("answer: 42\nThanks") == "42"
    assert parse_answer_line("no structured line") is None


def test_oracle_prefers_answer_line(item: ManifestItem) -> None:
    ok = ChartOracle().score(f"Answer: {item.answer_gold}", item)
    assert ok
    assert item.metadata.get("oracle_mode") == "answer_line"


def test_category_rejects_exclusive_wrong() -> None:
    item = ManifestItem(
        item_id="c",
        attack=AttackFamily.CLEAN,
        chart_type="bar",
        image_path="x.png",
        truth_path="x.json",
        question="Which category is max?",
        question_type=QuestionType.MAX_CATEGORY,
        answer_gold="Alpha",
        answer_numeric=10.0,
        metadata={},
    )
    # Provide truth categories via a tiny file
    from mrha.schema import ChartTruth, ChartType
    from mrha.charts.generate import save_truth

    # Without truth file, exclusive wrong still fails if gold missing
    assert not check_answer("Answer: Beta", item)

    # With truth listing both categories
    import tempfile
    from pathlib import Path as P

    with tempfile.TemporaryDirectory() as td:
        tp = P(td) / "t.json"
        save_truth(
            ChartTruth(
                chart_type=ChartType.BAR,
                title="t",
                categories=["Alpha", "Beta"],
                values=[10.0, 5.0],
            ),
            tp,
        )
        item.truth_path = str(tp)
        assert check_answer("Answer: Alpha", item)
        assert not check_answer("Answer: Beta", item)


def test_unanswerable_gold() -> None:
    item = ManifestItem(
        item_id="u",
        attack=AttackFamily.EVIDENCE_DESTROY,
        protocol=AttackProtocol.RE_ANSWER,
        chart_type="bar",
        image_path="x.png",
        truth_path="x.json",
        question="Which is max?",
        question_type=QuestionType.MAX_CATEGORY,
        answer_gold="unanswerable",
        metadata={},
    )
    assert check_answer("Answer: unanswerable", item)
    assert check_answer("I cannot tell from the image", item)
    assert not check_answer("Answer: Alpha", item)
