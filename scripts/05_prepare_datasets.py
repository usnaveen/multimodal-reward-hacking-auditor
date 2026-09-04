#!/usr/bin/env python3
"""Optional dataset download / cache helper (ChartQA via HuggingFace).

Mixed benchmarks (synthetic + ChartQA) are built via::

    python scripts/01_build_benchmark.py --source mixed --n-items 200
    # tiny smoke:
    python scripts/01_build_benchmark.py --config configs/chartqa_smoke.yaml

This script only *prepares/caches* ChartQA (or synthetic) under ``data/raw``.
If HF ``datasets`` or network fails, exit 2 with a clear message — use synthetic.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=["chartqa", "synthetic"],
        default="chartqa",
    )
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "data" / "raw" / "chartqa",
    )
    args = parser.parse_args()

    if args.source == "synthetic":
        from mrha.datasets.synthetic import load_synthetic_items

        items = load_synthetic_items(args.limit, args.out_dir)
        print(f"Wrote {len(items)} synthetic items under {args.out_dir}")
        return

    try:
        from mrha.datasets.chartqa import load_chartqa_items

        items = load_chartqa_items(args.limit, args.out_dir)
        print(f"Prepared {len(items)} ChartQA items → {args.out_dir}")
    except Exception as e:
        print(
            f"ChartQA prepare failed: {e}\n"
            "Degrading gracefully — use --source synthetic for offline work.\n"
            "Install: pip install datasets",
            file=sys.stderr,
        )
        raise SystemExit(2) from e


if __name__ == "__main__":
    main()
