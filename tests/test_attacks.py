"""Tests for attack families, protocols, and nuisance control."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.attacks.base import registry
from mrha.attacks.evidence_swap import EvidenceSwapAttack
from mrha.attacks.judge_bait import JudgeBaitAttack
from mrha.attacks.nuisance import NuisanceAttack
from mrha.charts.generate import generate_chart_bundle
from mrha.schema import AttackFamily, AttackProtocol, ManifestItem


def _clean(tmp_path: Path, seed: int = 5) -> tuple[ManifestItem, object]:
    bundle = generate_chart_bundle(seed, tmp_path / "c", "c0")
    truth = bundle["truth"]
    clean = ManifestItem(
        item_id="c0",
        attack=AttackFamily.CLEAN,
        protocol=AttackProtocol.INVARIANCE,
        chart_type=truth.chart_type,
        image_path=bundle["image_path"],
        truth_path=bundle["truth_path"],
        question=bundle["question"],
        question_type=bundle["question_type"],
        answer_gold=bundle["answer_gold"],
        answer_numeric=bundle["answer_numeric"],
        caption=bundle["caption"],
    )
    return clean, truth


def test_all_attacks_produce_images(tmp_path: Path) -> None:
    clean, truth = _clean(tmp_path)
    for fam, atk in registry().items():
        out = atk.apply(clean, truth, tmp_path / "a", seed=5)
        assert out.attack == fam
        assert Path(out.image_path).is_file()
        assert out.question == clean.question


def test_nuisance_keeps_gold(tmp_path: Path) -> None:
    clean, truth = _clean(tmp_path)
    out = NuisanceAttack().apply(clean, truth, tmp_path / "n", seed=3)
    assert out.attack == AttackFamily.NUISANCE
    assert out.answer_gold == clean.answer_gold
    assert out.metadata.get("should_change_answer") is False


def test_judge_bait_never_paints_gold(tmp_path: Path) -> None:
    clean, truth = _clean(tmp_path)
    out = JudgeBaitAttack().apply(clean, truth, tmp_path / "j", seed=1)
    assert out.metadata.get("paints_gold") is False
    stamp = out.metadata.get("stamp") or ""
    assert clean.answer_gold not in stamp
    assert clean.answer_gold not in (out.metadata.get("bait") or "")


def test_evidence_swap_dual_protocols(tmp_path: Path) -> None:
    clean, truth = _clean(tmp_path)
    atk = EvidenceSwapAttack()
    inv = atk.apply(
        clean, truth, tmp_path / "e", seed=2, protocol=AttackProtocol.INVARIANCE
    )
    rea = atk.apply(
        clean, truth, tmp_path / "e", seed=2, protocol=AttackProtocol.RE_ANSWER
    )
    assert inv.protocol == AttackProtocol.INVARIANCE
    assert rea.protocol == AttackProtocol.RE_ANSWER
    assert inv.answer_gold == clean.answer_gold
    assert "values_before" in inv.metadata
    assert "values_after" in inv.metadata
    assert inv.metadata["values_before"] != inv.metadata["values_after"]
    # re_answer gold tracks visual truth
    assert rea.answer_gold == rea.metadata["visual_answer_gold"]
    assert rea.metadata["protocol"] == "re_answer"


def test_registry_includes_nuisance() -> None:
    assert AttackFamily.NUISANCE in registry()
