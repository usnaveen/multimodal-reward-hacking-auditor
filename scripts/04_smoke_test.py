#!/usr/bin/env python3
"""Smoke test: 2 charts + attacks + oracle — NO model / GPU required."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.attacks.base import registry
from mrha.charts.generate import generate_chart_bundle, load_truth
from mrha.oracles.chart_oracle import ChartOracle
from mrha.pipeline.build_benchmark import build_benchmark, read_manifest
from mrha.schema import AttackFamily, ManifestItem


def main() -> int:
    print("MRHA smoke test (no VLM)…")
    failures = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # 1) Chart generation
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

        # 2) Attacks + oracle on gold string
        bundle = generate_chart_bundle(7, tmp_path / "one", "base")
        truth = bundle["truth"]
        clean = ManifestItem(
            item_id="base",
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
        oracle = ChartOracle()
        assert oracle.score(clean.answer_gold, clean), "oracle must accept gold"
        assert not oracle.score("TOTALLY_WRONG_XYZ", clean), "oracle must reject junk"
        print("  [ok] oracle accepts gold / rejects junk")

        atk_dir = tmp_path / "atk"
        for fam, atk in registry().items():
            attacked = atk.apply(clean, truth, atk_dir, seed=7)
            assert Path(attacked.image_path).is_file(), f"{fam} image missing"
            assert attacked.parent_id == clean.item_id
            assert attacked.answer_gold == clean.answer_gold
            # Gold answer still scores True against clean truth path
            assert oracle.score(clean.answer_gold, attacked)
            print(f"  [ok] attack {fam.value}")

        # 3) Mini benchmark build
        man = build_benchmark(
            n_items=2,
            out_dir=tmp_path / "bench",
            seed=99,
            attacks=["evidence_swap", "evidence_destroy", "wrong_caption", "judge_bait"],
        )
        items = read_manifest(man)
        # 2 clean + 2*4 attacks
        assert len(items) == 10, f"expected 10 items, got {len(items)}"
        print(f"  [ok] benchmark build → {len(items)} items")

    print("SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"SMOKE TEST FAILED: {e}", file=sys.stderr)
        raise
