"""Synthetic chart generator wrapper (default Phase-A source)."""

from __future__ import annotations

from pathlib import Path

from mrha.charts.generate import generate_chart_bundle
from mrha.schema import AttackFamily, AttackProtocol, ChartType, ManifestItem

DEFAULT_N_ITEMS = 200


def load_synthetic_items(
    n_items: int = DEFAULT_N_ITEMS,
    out_dir: Path | str = "data/benchmark/clean",
    *,
    seed: int = 42,
    id_prefix: str = "chart",
) -> list[ManifestItem]:
    """Generate ``n_items`` clean synthetic chart-VQA items."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    chart_cycle = list(ChartType)
    items: list[ManifestItem] = []
    for i in range(n_items):
        item_seed = seed + i
        item_id = f"{id_prefix}_{i:04d}"
        ct = chart_cycle[i % len(chart_cycle)]
        bundle = generate_chart_bundle(
            seed=item_seed,
            out_dir=out_dir,
            item_id=item_id,
            chart_type=ct,
        )
        items.append(
            ManifestItem(
                item_id=item_id,
                parent_id=None,
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
                prompt_prefix=None,
                metadata={"seed": item_seed, "source": "synthetic"},
            )
        )
    return items
