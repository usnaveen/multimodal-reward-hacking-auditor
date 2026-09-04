#!/usr/bin/env python3
"""Pivot audit JSONL into attack × proxy (and optional judge) tables.

Supports merging two runs (e.g. agent-only vs agent+judge) via ``--records-b``.
Does not invent metrics — empty input → empty tables / clear message.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.schema import AuditRecord


def load_records(path: Path) -> list[AuditRecord]:
    out: list[AuditRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(AuditRecord.model_validate_json(line))
    return out


def _attack_key(r: AuditRecord) -> str:
    proto = r.protocol.value if r.protocol else ""
    return f"{r.attack.value}|{proto}" if proto else r.attack.value


def _judge_id(r: AuditRecord) -> str:
    """Optional judge model id from metadata or proxy presence."""
    jid = r.metadata.get("judge_model_id") or r.metadata.get("judge_id")
    if jid:
        return str(jid)
    if "weak_vlm_judge" in r.proxy_scores:
        return str(r.metadata.get("judge_backend", "weak_vlm_judge"))
    return ""


def pivot_records(
    records: Iterable[AuditRecord],
    *,
    run_label: str = "",
) -> list[dict[str, Any]]:
    """Aggregate mean oracle + mean each proxy per attack (and judge if present)."""
    # key: (run_label, attack_key, judge_id)
    buckets: dict[tuple[str, str, str], list[AuditRecord]] = defaultdict(list)
    proxy_names: set[str] = set()
    for r in records:
        buckets[(run_label, _attack_key(r), _judge_id(r))].append(r)
        proxy_names.update(r.proxy_scores.keys())
    proxy_names = sorted(proxy_names)

    rows: list[dict[str, Any]] = []
    for (label, attack, judge), recs in sorted(buckets.items()):
        n = len(recs)
        row: dict[str, Any] = {
            "run": label,
            "attack_protocol": attack,
            "judge_model_id": judge,
            "n": n,
            "oracle_acc": (sum(1 for r in recs if r.oracle_correct) / n) if n else None,
        }
        for pname in proxy_names:
            vals = [float(r.proxy_scores[pname]) for r in recs if pname in r.proxy_scores]
            row[f"mean_proxy__{pname}"] = (sum(vals) / len(vals)) if vals else None
            # blind-ish: oracle fail & this proxy >= 0.5
            blinds = sum(
                1
                for r in recs
                if (not r.oracle_correct)
                and float(r.proxy_scores.get(pname, 0.0)) >= 0.5
            )
            row[f"blind_rate__{pname}"] = (blinds / n) if n else None
        rows.append(row)
    return rows


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("run,attack_protocol,judge_model_id,n,oracle_acc\n", encoding="utf-8")
        return
    # stable column order
    keys: list[str] = []
    seen: set[str] = set()
    preferred = ["run", "attack_protocol", "judge_model_id", "n", "oracle_acc"]
    for k in preferred:
        if any(k in r for r in rows):
            keys.append(k)
            seen.add(k)
    extras = sorted({k for r in rows for k in r.keys() if k not in seen})
    keys.extend(extras)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in keys})


def write_md(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("_No records — nothing to pivot._\n", encoding="utf-8")
        return
    # compact MD: run, attack, judge, n, oracle_acc, mean proxies
    cols = ["run", "attack_protocol", "judge_model_id", "n", "oracle_acc"]
    mean_cols = sorted(k for k in rows[0].keys() if k.startswith("mean_proxy__"))
    cols.extend(mean_cols)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--records",
        type=Path,
        default=ROOT / "results" / "audit_records.jsonl",
        help="Primary audit JSONL (agent-only or full)",
    )
    parser.add_argument(
        "--records-b",
        type=Path,
        default=None,
        help="Optional second JSONL to merge (e.g. agent+judge run)",
    )
    parser.add_argument("--label-a", type=str, default="run_a")
    parser.add_argument("--label-b", type=str, default="run_b")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "cross_table",
        help="Output prefix (writes .csv and .md)",
    )
    args = parser.parse_args()

    path_a = args.records if args.records.is_absolute() else ROOT / args.records
    if not path_a.is_file():
        print(
            f"no audit records at {path_a} — nothing to pivot. "
            "Run audit first. Exit 0 without fabricating."
        )
        raise SystemExit(0)

    recs_a = load_records(path_a)
    rows = pivot_records(recs_a, run_label=args.label_a)

    if args.records_b is not None:
        path_b = args.records_b if args.records_b.is_absolute() else ROOT / args.records_b
        if not path_b.is_file():
            print(f"Warning: --records-b not found: {path_b}", file=sys.stderr)
        else:
            recs_b = load_records(path_b)
            rows.extend(pivot_records(recs_b, run_label=args.label_b))

    out = args.out if args.out.is_absolute() else ROOT / args.out
    csv_path = Path(str(out) + ".csv") if out.suffix == "" else out.with_suffix(".csv")
    md_path = Path(str(out) + ".md") if out.suffix == "" else out.with_suffix(".md")
    # When --out is a prefix without suffix, Path.suffix is ""
    if out.suffix in {".csv", ".md"}:
        csv_path = out.with_suffix(".csv")
        md_path = out.with_suffix(".md")
    else:
        csv_path = Path(str(out) + ".csv")
        md_path = Path(str(out) + ".md")

    write_csv(rows, csv_path)
    write_md(rows, md_path)
    print(json.dumps({"n_rows": len(rows), "csv": str(csv_path), "md": str(md_path)}, indent=2))


if __name__ == "__main__":
    main()
