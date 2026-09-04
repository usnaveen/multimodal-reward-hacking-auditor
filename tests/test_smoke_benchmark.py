"""Integration: tiny benchmark build with protocols + nuisance."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.pipeline.build_benchmark import build_benchmark, read_manifest
from mrha.schema import AttackFamily, AttackProtocol


def test_build_small_benchmark(tmp_path: Path) -> None:
    man = build_benchmark(
        n_items=2,
        out_dir=tmp_path,
        seed=1,
        attacks=["evidence_swap", "judge_bait", "nuisance"],
        protocols=["invariance", "re_answer"],
        source="synthetic",
    )
    items = read_manifest(man)
    # 2 clean + 2*(evidence_swap×2 proto + judge_bait + nuisance) = 2 + 2*4 = 10
    assert len(items) == 10
    cleans = [i for i in items if i.attack == AttackFamily.CLEAN]
    assert len(cleans) == 2
    swaps = [i for i in items if i.attack == AttackFamily.EVIDENCE_SWAP]
    assert len(swaps) == 4  # 2 items × 2 protocols
    assert {i.protocol for i in swaps} == {
        AttackProtocol.INVARIANCE,
        AttackProtocol.RE_ANSWER,
    }
    assert any(i.attack == AttackFamily.NUISANCE for i in items)
    for p in [i.image_path for i in items]:
        assert Path(p).is_file()


def test_metrics_bootstrap_and_nrfr() -> None:
    from mrha.metrics.compute import bootstrap_ci_rate, nrfr
    from mrha.schema import AuditRecord, AttackFamily, AttackProtocol

    ci = bootstrap_ci_rate([True, False, True, True], n_boot=200, seed=0)
    assert ci is not None and len(ci) == 2 and ci[0] <= ci[1]

    recs = [
        AuditRecord(
            item_id="a",
            attack=AttackFamily.CLEAN,
            protocol=AttackProtocol.INVARIANCE,
            model_id="t",
            response="x",
            oracle_correct=False,
            metadata={"baseline_oracle_correct": False, "proxy_improved": True},
        )
    ]
    assert nrfr(recs) == 1.0
    assert nrfr([]) is None
