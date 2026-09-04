#!/usr/bin/env python3
"""Smoke test: charts + dual protocols + attacks + oracle — NO model / GPU."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.attacks.base import registry
from mrha.charts.generate import generate_chart_bundle, load_truth
from mrha.oracles.chart_oracle import ChartOracle, parse_answer_line
from mrha.pipeline.build_benchmark import build_benchmark, read_manifest
from mrha.proxies import gold_overlap_proxy, weak_vlm_judge
from mrha.proxies.weak_vlm_judge import JudgeClientRequiredError
from mrha.schema import AttackFamily, AttackProtocol, ManifestItem


def main() -> int:
    print("MRHA smoke test (no VLM)…")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        for i, seed in enumerate([0, 1]):
            bundle = generate_chart_bundle(
                seed=seed,
                out_dir=tmp_path / "charts",
                item_id=f"smoke_{i}",
            )
            assert Path(bundle["image_path"]).is_file(), "chart image missing"
            assert Path(bundle["truth_path"]).is_file(), "truth json missing"
            truth = load_truth(bundle["truth_path"])
            assert len(truth.values) == len(truth.categories)
            print(f"  [ok] chart {bundle['item_id']} ({truth.chart_type.value})")

        bundle = generate_chart_bundle(7, tmp_path / "one", "base")
        truth = bundle["truth"]
        clean = ManifestItem(
            item_id="base",
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
        oracle = ChartOracle()
        assert oracle.score(f"Answer: {clean.answer_gold}", clean)
        assert oracle.score(clean.answer_gold, clean), "oracle must accept gold"
        assert not oracle.score("TOTALLY_WRONG_XYZ", clean), "oracle must reject junk"
        assert parse_answer_line("Answer: Foo") == "Foo"
        print("  [ok] oracle Answer: parsing / gold / reject")

        # Judge requires client
        try:
            weak_vlm_judge.score("hi", clean, client=None)
            raise AssertionError("weak_vlm_judge should require client")
        except JudgeClientRequiredError:
            print("  [ok] weak_vlm_judge requires VLMClient")

        assert gold_overlap_proxy.score(clean.answer_gold, clean) == 1.0

        atk_dir = tmp_path / "atk"
        for fam, atk in registry().items():
            if atk.supports_protocols:
                for proto in (AttackProtocol.INVARIANCE, AttackProtocol.RE_ANSWER):
                    attacked = atk.apply(
                        clean, truth, atk_dir, seed=7, protocol=proto
                    )
                    assert Path(attacked.image_path).is_file()
                    assert attacked.protocol == proto
                    assert attacked.metadata.get("protocol") == proto.value
                    if proto == AttackProtocol.INVARIANCE:
                        assert attacked.answer_gold == clean.answer_gold
                    print(f"  [ok] attack {fam.value}/{proto.value}")
            else:
                attacked = atk.apply(clean, truth, atk_dir, seed=7)
                assert Path(attacked.image_path).is_file()
                assert attacked.parent_id == clean.item_id
                if fam == AttackFamily.JUDGE_BAIT:
                    assert attacked.metadata.get("paints_gold") is False
                    assert clean.answer_gold not in (
                        attacked.metadata.get("stamp") or ""
                    )
                if fam != AttackFamily.WRONG_CAPTION:
                    pass
                assert attacked.answer_gold == clean.answer_gold
                print(f"  [ok] attack {fam.value}")

        # Mini benchmark: 2 clean × (2 evidence × 2 proto + 3 other) = 2 + 2*(4+3)=16
        man = build_benchmark(
            n_items=2,
            out_dir=tmp_path / "bench",
            seed=99,
            attacks=[
                "evidence_swap",
                "evidence_destroy",
                "wrong_caption",
                "judge_bait",
                "nuisance",
            ],
            protocols=["invariance", "re_answer"],
            source="synthetic",
        )
        items = read_manifest(man)
        # evidence attacks: 2 protocols each → 4; others: 3; total attacks/clean=7
        # 2 clean + 2*7 = 16
        assert len(items) == 16, f"expected 16 items, got {len(items)}"
        assert any(i.protocol == AttackProtocol.RE_ANSWER for i in items)
        assert any(i.attack == AttackFamily.NUISANCE for i in items)
        print(f"  [ok] benchmark build → {len(items)} items")

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"SMOKE TEST FAILED: {e}", file=sys.stderr)
        raise
