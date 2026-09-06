#!/usr/bin/env python3
"""Compute NRFR from best-of-n pressure JSONL (no fabrication).

Reads records written by ``scripts/02b_best_of_n_pressure.py`` that include
``metadata.baseline_oracle_correct``, ``metadata.proxy_improved``, ``metadata.k``,
and ``metadata.seed``.

If the file is missing or has no pressure fields, prints a clear message and
exits 0 without inventing an NRFR value.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.metrics.compute import nrfr
from mrha.schema import AuditRecord


def load_pressure_records(path: Path) -> list[AuditRecord]:
    records: list[AuditRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(AuditRecord.model_validate_json(line))
    return records


def nrfr_by_k(records: list[AuditRecord]) -> dict[str, dict]:
    """Group by metadata.k and compute NRFR per group."""
    groups: dict[str, list[AuditRecord]] = defaultdict(list)
    for r in records:
        k = r.metadata.get("k")
        key = str(k) if k is not None else "unknown"
        groups[key].append(r)
    out: dict[str, dict] = {}
    for key, recs in sorted(groups.items(), key=lambda t: (t[0] == "unknown", t[0])):
        val = nrfr(recs)
        n_improved = sum(1 for r in recs if r.metadata.get("proxy_improved") is True)
        seeds = sorted({r.metadata.get("seed") for r in recs if "seed" in r.metadata})
        out[key] = {
            "k": None if key == "unknown" else (int(key) if key.isdigit() else key),
            "n": len(recs),
            "n_proxy_improved": n_improved,
            "nrfr": val,
            "seeds": seeds,
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pressure-jsonl",
        type=Path,
        default=ROOT / "results" / "best_of_n" / "pressure_records.jsonl",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "nrfr_summary.json",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=None,
        help="Optional markdown table path",
    )
    args = parser.parse_args()

    path = args.pressure_jsonl
    if not path.is_absolute():
        path = ROOT / path

    if not path.is_file():
        print(
            f"no real pressure run yet — missing {path}. "
            "Run scripts/02b_best_of_n_pressure.py first. "
            "Refusing to fabricate NRFR. Exit 0."
        )
        raise SystemExit(0)

    records = load_pressure_records(path)
    if not records:
        print(f"Pressure file empty: {path}. Exit 0 without fabricating.")
        raise SystemExit(0)

    source = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    model_ids = sorted({record.model_id for record in records})
    research_eligible = "echo-stub" not in model_ids
    overall = nrfr(records)
    if not research_eligible:
        payload = {
            "source": source,
            "n": len(records),
            "model_ids": model_ids,
            "research_eligible": False,
            "nrfr": None,
            "diagnostic_nrfr": overall,
            "by_k": nrfr_by_k(records),
            "notes": [
                "Echo-stub pressure records validate plumbing only; their "
                "diagnostic NRFR is not research evidence.",
            ],
        }
    elif overall is None:
        print(
            "NRFR undefined — no records with metadata.proxy_improved=True. "
            "Check that 02b wrote pressure fields. Exit 0 without fabricating."
        )
        # Still write a stub summary noting undefined (not a fake rate).
        payload = {
            "source": source,
            "n": len(records),
            "model_ids": model_ids,
            "research_eligible": True,
            "nrfr": None,
            "by_k": nrfr_by_k(records),
            "notes": [
                "NRFR undefined (no proxy_improved). Not a fabricated zero.",
            ],
        }
    else:
        payload = {
            "source": source,
            "n": len(records),
            "model_ids": model_ids,
            "research_eligible": True,
            "nrfr": overall,
            "by_k": nrfr_by_k(records),
            "notes": [],
        }

    out = args.out
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"Wrote: {out}")

    md_out = args.md_out
    if md_out is not None:
        if not md_out.is_absolute():
            md_out = ROOT / md_out
        lines = [
            f"Model(s): {', '.join(payload['model_ids'])}",
            f"Research eligible: {payload['research_eligible']}",
            "",
            "| k | n | n_proxy_improved | NRFR | seeds |",
            "|---|---|------------------|------|-------|",
        ]
        for row in payload["by_k"].values():
            displayed_nrfr = row["nrfr"] if payload["research_eligible"] else "—"
            lines.append(
                f"| {row['k']} | {row['n']} | {row['n_proxy_improved']} | "
                f"{displayed_nrfr} | {row['seeds']} |"
            )
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote: {md_out}")


if __name__ == "__main__":
    main()
