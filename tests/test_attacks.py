"""Tests for attack families."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.attacks.base import registry
from mrha.charts.generate import generate_chart_bundle
from mrha.schema import AttackFamily, ManifestItem


def test_all_attacks_produce_images(tmp_path: Path) -> None:
    bundle = generate_chart_bundle(5, tmp_path / "c", "c0")
    truth = bundle["truth"]
    clean = ManifestItem(
        item_id="c0",
        attack=AttackFamily.CLEAN,
        chart_type=truth.chart_type,
        image_path=bundle["image_path"],
        truth_path=bundle["truth_path"],
        question=bundle["question"],
        question_type=bundle["question_type"],
        answer_gold=bundle["answer_gold"],
        answer_numeric=bundle["answer_numeric"],
        caption=bundle["caption"],
    )
    for fam, atk in registry().items():
        out = atk.apply(clean, truth, tmp_path / "a", seed=5)
        assert out.attack == fam
        assert Path(out.image_path).is_file()
        assert out.answer_gold == clean.answer_gold
        assert out.question == clean.question
