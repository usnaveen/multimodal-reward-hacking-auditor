"""Build synthetic chart-VQA benchmark with attacks -> manifest.jsonl."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import yaml

from mrha.attacks.base import registry
from mrha.charts.generate import generate_chart_bundle, load_truth
from mrha.schema import AttackFamily, ChartType, ManifestItem


def load_config(path: Path | str) -> dict:
    """Load YAML config."""
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_benchmark(
    n_items: int = 20,
    out_dir: Path | str = "data/benchmark",
    seed: int = 42,
    attacks: Iterable[str] | None = None,
) -> Path:
    """Generate N clean charts + configured attacks; write manifest.jsonl.

    Returns path to manifest.jsonl.
    """
    out_dir = Path(out_dir)
    clean_dir = out_dir / "clean"
    attack_dir = out_dir / "attacks"
    clean_dir.mkdir(parents=True, exist_ok=True)
    attack_dir.mkdir(parents=True, exist_ok=True)

    attack_names = list(attacks) if attacks is not None else [
        a.value for a in AttackFamily if a != AttackFamily.CLEAN
    ]
    reg = registry()
    selected = []
    for name in attack_names:
        fam = AttackFamily(name)
        if fam == AttackFamily.CLEAN:
            continue
        if fam not in reg:
            raise KeyError(f"Unknown attack: {name}")
        selected.append(reg[fam])

    chart_cycle = list(ChartType)
    items: list[ManifestItem] = []

    for i in range(n_items):
        item_seed = seed + i
        item_id = f"chart_{i:04d}"
        ct = chart_cycle[i % len(chart_cycle)]
        bundle = generate_chart_bundle(
            seed=item_seed,
            out_dir=clean_dir,
            item_id=item_id,
            chart_type=ct,
        )
        clean = ManifestItem(
            item_id=item_id,
            parent_id=None,
            attack=AttackFamily.CLEAN,
            chart_type=bundle["truth"].chart_type,
            image_path=bundle["image_path"],
            truth_path=bundle["truth_path"],
            question=bundle["question"],
            question_type=bundle["question_type"],
            answer_gold=bundle["answer_gold"],
            answer_numeric=bundle["answer_numeric"],
            caption=bundle["caption"],
            prompt_prefix=None,
            metadata={"seed": item_seed},
        )
        items.append(clean)
        truth = load_truth(Path(clean.truth_path))
        for atk in selected:
            attacked = atk.apply(clean, truth, attack_dir, seed=item_seed)
            items.append(attacked)

    manifest_path = out_dir / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(it.model_dump_json() + "\n")

    meta = {
        "n_clean": n_items,
        "n_total": len(items),
        "attacks": [a.family.value for a in selected],
        "seed": seed,
        "manifest": str(manifest_path),
    }
    (out_dir / "build_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return manifest_path


def read_manifest(path: Path | str) -> list[ManifestItem]:
    """Read manifest.jsonl into ManifestItem list."""
    items: list[ManifestItem] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(ManifestItem.model_validate_json(line))
    return items
