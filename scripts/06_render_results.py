#!/usr/bin/env python3
"""Render RESULTS.md snippet + optional figures from *real* metric files.

If ``results/metrics_summary.json`` and/or per-attack CSV are missing,
prints a clear "no real run yet" message and exits 0 **without fabricating**.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_summary(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Invalid JSON at {path}: {e}", file=sys.stderr)
        return None


def _load_per_attack_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _md_summary_table(summary: dict) -> str:
    rows = [
        ("n_items", summary.get("n_items"), ""),
        ("n_clean", summary.get("n_clean"), ""),
        ("n_attack", summary.get("n_attack"), ""),
        ("blind_spot_rate", summary.get("blind_spot_rate"), summary.get("blind_spot_rate_ci95")),
        ("rhr", summary.get("rhr"), summary.get("rhr_ci95")),
        ("nrfr", summary.get("nrfr"), ""),
    ]
    lines = [
        "## Summary metrics (from real run)",
        "",
        "| Metric | Value | 95% CI |",
        "|--------|-------|--------|",
    ]
    for name, val, ci in rows:
        lines.append(f"| {name} | {val} | {ci} |")
    gaps = summary.get("proxy_oracle_gap") or {}
    if gaps:
        lines.append("")
        lines.append("### proxy_oracle_gap")
        lines.append("")
        lines.append("| proxy | gap |")
        lines.append("|-------|-----|")
        for k, v in sorted(gaps.items()):
            lines.append(f"| {k} | {v} |")
    notes = summary.get("notes") or []
    if notes:
        lines.append("")
        lines.append("### notes")
        for n in notes:
            lines.append(f"- {n}")
    return "\n".join(lines) + "\n"


def _md_per_attack(rows: list[dict]) -> str:
    lines = [
        "## Per-attack breakdown (from real run)",
        "",
        "| attack_protocol | n | oracle_acc | blind_spot_rate |",
        "|-----------------|---|------------|-----------------|",
    ]
    for r in rows:
        lines.append(
            "| {attack_protocol} | {n} | {oracle_acc} | {blind_spot_rate} |".format(
                attack_protocol=r.get("attack_protocol", ""),
                n=r.get("n", ""),
                oracle_acc=r.get("oracle_acc", ""),
                blind_spot_rate=r.get("blind_spot_rate", ""),
            )
        )
    return "\n".join(lines) + "\n"


def _maybe_plot(summary: dict, per_attack: list[dict], fig_dir: Path) -> list[Path]:
    """Optional matplotlib PNGs. Skip quietly if matplotlib unavailable."""
    written: list[Path] = []
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping PNGs")
        return written

    fig_dir.mkdir(parents=True, exist_ok=True)

    if per_attack:
        labels = [r.get("attack_protocol", "") for r in per_attack]
        vals = []
        for r in per_attack:
            try:
                vals.append(float(r["blind_spot_rate"]) if r.get("blind_spot_rate") not in (None, "") else 0.0)
            except (TypeError, ValueError):
                vals.append(0.0)
        fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.6), 4))
        ax.bar(range(len(labels)), vals)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_ylabel("blind_spot_rate")
        ax.set_title("Per-attack blind-spot rate (real run)")
        fig.tight_layout()
        p = fig_dir / "blind_spot_per_attack.png"
        fig.savefig(p, dpi=120)
        plt.close(fig)
        written.append(p)

    gaps = summary.get("proxy_oracle_gap") or {}
    if gaps:
        names = sorted(gaps.keys())
        gvals = [float(gaps[n]) for n in names]
        fig, ax = plt.subplots(figsize=(max(5, len(names) * 0.8), 4))
        ax.bar(range(len(names)), gvals)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=30, ha="right")
        ax.set_ylabel("mean(proxy) - mean(oracle)")
        ax.set_title("Proxy–oracle gap (real run)")
        fig.tight_layout()
        p = fig_dir / "proxy_oracle_gap.png"
        fig.savefig(p, dpi=120)
        plt.close(fig)
        written.append(p)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT / "results",
        help="Directory containing metrics_summary.json and CSVs",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=None,
        help="Override path to metrics_summary.json",
    )
    parser.add_argument(
        "--per-attack-csv",
        type=Path,
        default=None,
        help="Override path to per_attack_breakdown.csv",
    )
    parser.add_argument(
        "--snippet-out",
        type=Path,
        default=None,
        help="Write markdown snippet here (default: results/RESULTS_SNIPPET.md)",
    )
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    results_dir = args.results_dir
    if not results_dir.is_absolute():
        results_dir = ROOT / results_dir
    summary_path = args.summary or (results_dir / "metrics_summary.json")
    if not summary_path.is_absolute():
        summary_path = ROOT / summary_path
    csv_path = args.per_attack_csv or (results_dir / "per_attack_breakdown.csv")
    if not csv_path.is_absolute():
        csv_path = ROOT / csv_path

    summary = _load_summary(summary_path)
    per_attack = _load_per_attack_csv(csv_path)

    if summary is None and not per_attack:
        print(
            "no real run yet — missing metrics_summary.json and "
            "per_attack_breakdown.csv under "
            f"{results_dir}. Run audit + scripts/03_compute_metrics.py first. "
            "Refusing to fabricate numbers. Exit 0."
        )
        raise SystemExit(0)

    parts: list[str] = [
        "<!-- Auto-rendered from real metric files; do not hand-edit invented values -->",
        "",
    ]
    if summary is not None:
        parts.append(_md_summary_table(summary))
    else:
        parts.append("_metrics_summary.json missing — summary table skipped._\n")
    if per_attack:
        parts.append(_md_per_attack(per_attack))
    else:
        parts.append("_per_attack_breakdown.csv missing — per-attack table skipped._\n")

    snippet = "\n".join(parts)
    snippet_out = args.snippet_out or (results_dir / "RESULTS_SNIPPET.md")
    if not snippet_out.is_absolute():
        snippet_out = ROOT / snippet_out
    snippet_out.parent.mkdir(parents=True, exist_ok=True)
    snippet_out.write_text(snippet, encoding="utf-8")
    print(f"Wrote snippet: {snippet_out}")

    if not args.no_figures and summary is not None:
        figs = _maybe_plot(summary, per_attack, results_dir / "figures")
        for p in figs:
            print(f"Wrote figure: {p}")

    print("Done (real files only — nothing fabricated).")


if __name__ == "__main__":
    main()
