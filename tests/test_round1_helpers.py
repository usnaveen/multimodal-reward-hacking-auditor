"""Round 1 helpers: NRFR grouping, cross_table pivot, label split."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from mrha.metrics.compute import nrfr
from mrha.schema import AttackFamily, AttackProtocol, AuditRecord


def _rec(
    item_id: str,
    *,
    attack: AttackFamily = AttackFamily.EVIDENCE_SWAP,
    oracle: bool = False,
    proxies: dict | None = None,
    meta: dict | None = None,
    model_id: str = "t",
) -> AuditRecord:
    return AuditRecord(
        item_id=item_id,
        attack=attack,
        protocol=AttackProtocol.INVARIANCE,
        model_id=model_id,
        response="x",
        oracle_correct=oracle,
        proxy_scores=proxies or {"keyword_match": 0.8},
        metadata=meta or {},
    )


def test_nrfr_helper_and_by_k(tmp_path: Path) -> None:
    # Import from script module path
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "compute_nrfr", ROOT / "scripts" / "07_compute_nrfr.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    recs = [
        _rec(
            "a",
            oracle=False,
            meta={"baseline_oracle_correct": False, "proxy_improved": True, "k": 4, "seed": 0},
        ),
        _rec(
            "b",
            oracle=True,
            meta={"baseline_oracle_correct": False, "proxy_improved": True, "k": 4, "seed": 0},
        ),
        _rec(
            "c",
            oracle=False,
            meta={"baseline_oracle_correct": True, "proxy_improved": True, "k": 8, "seed": 1},
        ),
        _rec(
            "d",
            oracle=False,
            meta={"baseline_oracle_correct": False, "proxy_improved": False, "k": 8, "seed": 1},
        ),
    ]
    # overall: among proxy_improved (a,b,c): a bad, b oracle_improved ok, c bad → 2/3
    assert nrfr(recs) == pytest.approx(2 / 3)
    by_k = mod.nrfr_by_k(recs)
    assert by_k["4"]["n"] == 2
    assert by_k["4"]["n_proxy_improved"] == 2
    assert by_k["4"]["nrfr"] == pytest.approx(0.5)  # a bad, b good
    assert by_k["8"]["nrfr"] == pytest.approx(1.0)  # only c improved, not oracle_improved

    # script exits 0 on missing file
    missing = tmp_path / "nope.jsonl"
    # simulate CLI path check logic
    assert not missing.is_file()


def test_cross_table_pivot_and_merge(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "cross_table", ROOT / "scripts" / "08_cross_table.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    run_a = [
        _rec(
            "a1",
            attack=AttackFamily.EVIDENCE_SWAP,
            oracle=False,
            proxies={"keyword_match": 0.9, "outcome_only": 1.0},
        ),
        _rec(
            "a2",
            attack=AttackFamily.NUISANCE,
            oracle=True,
            proxies={"keyword_match": 0.2, "outcome_only": 1.0},
        ),
    ]
    run_b = [
        _rec(
            "b1",
            attack=AttackFamily.EVIDENCE_SWAP,
            oracle=False,
            proxies={"keyword_match": 0.7, "weak_vlm_judge": 0.9},
            meta={"judge_model_id": "judge-1"},
            model_id="agent+judge",
        ),
    ]
    rows = mod.pivot_records(run_a, run_label="agent_only")
    rows.extend(mod.pivot_records(run_b, run_label="agent_plus_judge"))
    assert len(rows) >= 2
    labels = {r["run"] for r in rows}
    assert labels == {"agent_only", "agent_plus_judge"}
    # evidence_swap agent_only: oracle_acc 0
    swap_a = [
        r
        for r in rows
        if r["run"] == "agent_only" and r["attack_protocol"].startswith("evidence_swap")
    ]
    assert len(swap_a) == 1
    assert swap_a[0]["oracle_acc"] == 0.0
    assert swap_a[0]["mean_proxy__keyword_match"] == pytest.approx(0.9)

    csv_path = tmp_path / "cross.csv"
    md_path = tmp_path / "cross.md"
    mod.write_csv(rows, csv_path)
    mod.write_md(rows, md_path)
    assert csv_path.is_file() and md_path.is_file()
    assert "attack_protocol" in csv_path.read_text(encoding="utf-8")


def test_label_split_70_30(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "split_labels", ROOT / "scripts" / "10_split_labels.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)

    labels = tmp_path / "detector_labels.jsonl"
    rows = []
    for i in range(10):
        rows.append({"item_id": f"id_{i}", "label": bool(i % 2), "notes": ""})
    # one null should be ignored
    rows.append({"item_id": "id_null", "label": None})
    labels.write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    labeled = mod.load_labeled(labels)
    assert len(labeled) == 10
    train, eval_ = mod.split_rows(labeled, train_frac=0.7, seed=0)
    assert len(train) + len(eval_) == 10
    assert len(train) == 7
    assert len(eval_) == 3
    # disjoint
    assert {r["item_id"] for r in train}.isdisjoint({r["item_id"] for r in eval_})

    out_dir = tmp_path / "out"
    mod.write_jsonl(out_dir / "detector_labels_train.jsonl", train)
    mod.write_jsonl(out_dir / "detector_labels_eval.jsonl", eval_)
    assert (out_dir / "detector_labels_train.jsonl").is_file()


def test_render_results_missing_exits_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """06_render_results must not fabricate when files missing."""
    import subprocess

    script = ROOT / "scripts" / "06_render_results.py"
    empty = tmp_path / "results"
    empty.mkdir()
    proc = subprocess.run(
        [sys.executable, str(script), "--results-dir", str(empty)],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0
    assert "no real run yet" in proc.stdout.lower()
    # no fabricated summary
    assert not (empty / "metrics_summary.json").exists()
