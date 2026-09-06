#!/usr/bin/env python3
"""Recompute causal pressure metrics from stored candidate records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.pressure.analysis import summarize_pressure
from mrha.pressure.schema import PressureRecord


def _load(path: Path) -> list[PressureRecord]:
    return [
        PressureRecord.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _provenance_eligibility(
    records_path: Path, records: list[PressureRecord]
) -> tuple[bool, list[str]]:
    """Fail closed unless final run metadata and record hashes agree."""
    meta_path = records_path.parent / "run_meta.final.json"
    if not meta_path.is_file():
        return False, ["Missing run_meta.final.json; eligibility fails closed."]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    notes: list[str] = []
    config_hash = meta.get("config_hash")
    if not config_hash:
        notes.append("Final run metadata has no config hash.")
    if any(record.metadata.get("config_hash") != config_hash for record in records):
        notes.append("Record config hashes do not match final run metadata.")
    if {record.agent_model_id for record in records} != {meta.get("agent_model_id")}:
        notes.append("Record agent identity does not match final run metadata.")
    expected_judge = meta.get("judge_model_id")
    if {record.judge_model_id for record in records} != {expected_judge}:
        notes.append("Record judge identity does not match final run metadata.")
    if meta.get("n_records") != len(records):
        notes.append("Final metadata record count does not match the JSONL.")
    if meta.get("expected_records") != len(records):
        notes.append("Run is incomplete relative to its expected item count.")
    if not meta.get("research_eligible", False):
        notes.append("Runner marked this configuration non-research.")
    return not notes, notes


def _format(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Causal Proxy-Pressure Results",
        "",
        f"Research eligible: **{summary['research_eligible']}**",
        f"Records: {summary['n_records']} across {summary['n_parents']} parents",
        f"Agent model(s): {', '.join(summary['agent_model_ids'])}",
        f"Judge model(s): {', '.join(summary['judge_model_ids']) or 'none'}",
        "",
        "## Overall selector effects",
        "",
        "| selector | baseline acc | selected acc | oracle delta | vs random expectation | proxy gain | regression | rescue | false acceptance |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for selector, row in summary["selectors"].items():
        lines.append(
            f"| {selector} | {_format(row['baseline_accuracy'])} | "
            f"{_format(row['selected_accuracy'])} | {_format(row['oracle_delta'])} | "
            f"{_format(row['oracle_effect_vs_random_expectation'])} | "
            f"{_format(row['proxy_gain'])} | {_format(row['regression_rate'])} | "
            f"{_format(row['rescue_rate'])} | "
            f"{_format(row['false_acceptance_rate'])} |"
        )
    proxy_names = sorted(
        {
            name
            for row in summary["selectors"].values()
            for name in row["proxy_deltas"]
        }
    )
    lines.extend(["", "## Proxy deltas by selector", ""])
    lines.append("| selector | " + " | ".join(proxy_names) + " |")
    lines.append("|---|" + "---:|" * len(proxy_names))
    for selector, row in summary["selectors"].items():
        values = [_format(row["proxy_deltas"].get(name)) for name in proxy_names]
        lines.append(f"| {selector} | " + " | ".join(values) + " |")

    lines.extend(["", "## Per-condition oracle deltas", ""])
    selectors = list(summary["selectors"])
    lines.append("| condition | n | " + " | ".join(selectors) + " |")
    lines.append("|---|---:|" + "---:|" * len(selectors))
    for condition, block in summary["by_condition"].items():
        deltas = [
            _format(block["selectors"][selector]["oracle_delta"])
            for selector in selectors
        ]
        lines.append(
            f"| {condition} | {block['n_records']} | " + " | ".join(deltas) + " |"
        )
    lines.extend(
        [
            "",
            "Oracle delta is selected accuracy minus the paired greedy baseline.",
            "The random contrast uses exact candidate-set expectation, not one noisy draw.",
            "Regression is baseline-correct to selected-incorrect; rescue is the inverse.",
            "Confidence intervals in JSON use parent-cluster bootstrap resampling.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    args = parser.parse_args()

    records_path = args.records.resolve()
    if not records_path.is_file():
        raise SystemExit(f"Pressure records not found: {records_path}")
    records = _load(records_path)
    if not records:
        raise SystemExit(f"Pressure records are empty: {records_path}")

    research_eligible, eligibility_notes = _provenance_eligibility(
        records_path, records
    )
    summary = summarize_pressure(
        records,
        n_boot=args.bootstrap_samples,
        research_eligible=research_eligible,
    )
    summary["eligibility_notes"] = eligibility_notes
    summary["source"] = str(
        records_path.relative_to(ROOT)
        if records_path.is_relative_to(ROOT)
        else records_path
    )
    out = args.out or records_path.parent / "summary.json"
    md_out = args.md_out or records_path.parent / "RESULTS.md"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(_markdown(summary), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Wrote {md_out}")


if __name__ == "__main__":
    main()
