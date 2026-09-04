#!/usr/bin/env python3
"""Build chart-VQA benchmark with attack variants (synthetic / chartqa / mixed)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.pipeline.build_benchmark import build_benchmark, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "default.yaml",
    )
    parser.add_argument("--n-items", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument(
        "--source",
        choices=["synthetic", "chartqa", "mixed"],
        default=None,
    )
    args = parser.parse_args()

    cfg = load_config(args.config) if args.config.exists() else {}
    n = args.n_items if args.n_items is not None else int(cfg.get("n_items", 200))
    seed = args.seed if args.seed is not None else int(cfg.get("seed", 42))
    out = args.out_dir or Path(cfg.get("paths", {}).get("benchmark", "data/benchmark"))
    if not out.is_absolute():
        out = ROOT / out
    attacks = cfg.get("attacks")
    protocols = cfg.get("protocols")
    source = args.source or cfg.get("source", "synthetic")
    path = build_benchmark(
        n_items=n,
        out_dir=out,
        seed=seed,
        attacks=attacks,
        protocols=protocols,
        source=source,
    )
    print(f"Wrote manifest: {path} (source={source})")


if __name__ == "__main__":
    main()
