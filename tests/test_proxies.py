"""Proxy split: gold_overlap vs weak_vlm_judge requiring client."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.proxies import gold_overlap_proxy, weak_vlm_judge
from mrha.proxies.weak_vlm_judge import JudgeClientRequiredError
from mrha.schema import AttackFamily, ManifestItem, QuestionType


def _item() -> ManifestItem:
    return ManifestItem(
        item_id="p",
        attack=AttackFamily.CLEAN,
        chart_type="bar",
        image_path="x.png",
        truth_path="x.json",
        question="q",
        question_type=QuestionType.MAX_CATEGORY,
        answer_gold="Alpha",
    )


def test_gold_overlap_proxy() -> None:
    item = _item()
    assert gold_overlap_proxy.score("Answer: Alpha", item) == 1.0
    assert gold_overlap_proxy.score("Beta", item) == 0.0


def test_weak_judge_requires_client() -> None:
    with pytest.raises(JudgeClientRequiredError):
        weak_vlm_judge.score("Answer: Alpha", _item(), client=None)


def test_weak_judge_with_stub_client() -> None:
    class Stub:
        model_id = "stub"

        def answer(self, image_path: str, prompt: str) -> str:
            return "YES"

    assert weak_vlm_judge.score("x", _item(), client=Stub()) == 1.0
