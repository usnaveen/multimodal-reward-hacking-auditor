"""Integration: tiny benchmark build."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.pipeline.build_benchmark import build_benchmark, read_manifest
from mrha.schema import AttackFamily


def test_build_small_benchmark(tmp_path: Path) -> None:
    man = build_benchmark(
        n_items=2,
        out_dir=tmp_path,
        seed=1,
        attacks=["evidence_swap", "judge_bait"],
    )
    items = read_manifest(man)
    assert len(items) == 2 + 2 * 2
    cleans = [i for i in items if i.attack == AttackFamily.CLEAN]
    assert len(cleans) == 2
    for p in [i.image_path for i in items]:
        assert Path(p).is_file()
