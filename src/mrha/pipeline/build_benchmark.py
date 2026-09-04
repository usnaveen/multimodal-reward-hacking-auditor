"""Build chart-VQA benchmark with attacks -> manifest.jsonl."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import yaml

from mrha.attacks.base import registry
from mrha.charts.generate import load_truth
from mrha.schema import AttackFamily, AttackProtocol, ManifestItem


def load_config(path: Path | str) -> dict:
    """Load YAML config."""
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_benchmark(
    n_items: int = 200,
    out_dir: Path | str = "data/benchmark",
    seed: int = 42,
    attacks: Iterable[str] | None = None,
    protocols: Iterable[str] | None = None,
    source: str = "synthetic",
) -> Path:
    """Generate N clean charts + configured attacks; write manifest.jsonl.

    ``source``: ``synthetic`` | ``chartqa`` | ``mixed``.
    Dual protocols apply to evidence_swap / evidence_destroy only.

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
    proto_names = list(protocols) if protocols is not None else [
        AttackProtocol.INVARIANCE.value,
        AttackProtocol.RE_ANSWER.value,
    ]
    proto_list = [AttackProtocol(p) for p in proto_names]

    reg = registry()
    selected = []
    for name in attack_names:
        fam = AttackFamily(name)
        if fam == AttackFamily.CLEAN:
            continue
        if fam not in reg:
            raise KeyError(f"Unknown attack: {name}")
        selected.append(reg[fam])

    # Load clean items from source
    from mrha.datasets.synthetic import load_synthetic_items
    from mrha.datasets.chartqa import load_chartqa_items

    source = (source or "synthetic").lower()
    cleans: list[ManifestItem] = []

    if source == "synthetic":
        cleans = load_synthetic_items(n_items, clean_dir, seed=seed)
    elif source == "chartqa":
        cleans = load_chartqa_items(n_items, clean_dir, seed=seed)
    elif source == "mixed":
        n_syn = n_items // 2
        n_cq = n_items - n_syn
        cleans = load_synthetic_items(n_syn, clean_dir, seed=seed)
        try:
            cleans.extend(load_chartqa_items(n_cq, clean_dir, seed=seed + 10_000))
        except Exception as e:
            print(
                f"[warn] ChartQA unavailable ({e}); "
                f"filling remaining {n_cq} with synthetic."
            )
            cleans.extend(
                load_synthetic_items(
                    n_cq, clean_dir, seed=seed + 20_000, id_prefix="chart_fill"
                )
            )
    else:
        raise ValueError(f"Unknown source: {source}")

    items: list[ManifestItem] = []
    for clean in cleans:
        # Ensure protocol field on clean
        if not getattr(clean, "protocol", None):
            clean.protocol = AttackProtocol.INVARIANCE
        items.append(clean)
        truth = load_truth(Path(clean.truth_path))
        for atk in selected:
            if atk.supports_protocols:
                for proto in proto_list:
                    attacked = atk.apply(
                        clean, truth, attack_dir, seed=clean.metadata.get("seed", seed),
                        protocol=proto,
                    )
                    items.append(attacked)
            else:
                attacked = atk.apply(
                    clean,
                    truth,
                    attack_dir,
                    seed=clean.metadata.get("seed", seed),
                    protocol=AttackProtocol.INVARIANCE,
                )
                items.append(attacked)

    manifest_path = out_dir / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(it.model_dump_json() + "\n")

    meta = {
        "n_clean": len(cleans),
        "n_total": len(items),
        "attacks": [a.family.value for a in selected],
        "protocols": [p.value for p in proto_list],
        "source": source,
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
