#!/usr/bin/env python3
"""Recompute metrics from results/audit_records.jsonl."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.metrics.compute import compute_all, write_metrics
from mrha.schema import AuditRecord


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--records",
        type=Path,
        default=ROOT / "results" / "audit_records.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "results",
    )
    parser.add_argument("--rhr-proxy", type=str, default="keyword_match")
    args = parser.parse_args()

    if not args.records.exists():
        raise SystemExit(
            f"No records at {args.records}. Run audit first "
            "(do not invent metric numbers)."
        )

    records: list[AuditRecord] = []
    for line in args.records.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(AuditRecord.model_validate_json(line))

    summary = compute_all(records, rhr_proxy=args.rhr_proxy)
    paths = write_metrics(summary, args.out_dir, records=records)
    print(summary.model_dump_json(indent=2))
    print("Wrote:", {k: str(v) for k, v in paths.items()})


if __name__ == "__main__":
    main()
