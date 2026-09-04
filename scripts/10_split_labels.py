#!/usr/bin/env python3
"""Hold-out split for detector labels (default 70/30 train/eval).

Reads ``data/labels/detector_labels.jsonl`` (rows with non-null ``label``),
writes ``detector_labels_train.jsonl`` and ``detector_labels_eval.jsonl``.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_labeled(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("label") is None:
            continue
        rows.append(obj)
    return rows


def split_rows(
    rows: list[dict],
    *,
    train_frac: float = 0.7,
    seed: int = 0,
) -> tuple[list[dict], list[dict]]:
    if not 0.0 < train_frac < 1.0:
        raise ValueError("train_frac must be in (0, 1)")
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    n_train = int(len(shuffled) * train_frac)
    # Ensure both sides non-empty when possible
    if len(shuffled) >= 2:
        n_train = max(1, min(n_train, len(shuffled) - 1))
    return shuffled[:n_train], shuffled[n_train:]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--labels",
        type=Path,
        default=ROOT / "data" / "labels" / "detector_labels.jsonl",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "data" / "labels",
    )
    parser.add_argument("--train-frac", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    labels = args.labels if args.labels.is_absolute() else ROOT / args.labels
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir

    if not labels.is_file():
        raise SystemExit(
            f"No labels at {labels}. Create with scripts/09_label_detector.py "
            "and set label true/false."
        )

    rows = load_labeled(labels)
    if not rows:
        raise SystemExit(
            f"No non-null labels in {labels}. Fill label fields before splitting."
        )

    train, eval_ = split_rows(rows, train_frac=args.train_frac, seed=args.seed)
    train_path = out_dir / "detector_labels_train.jsonl"
    eval_path = out_dir / "detector_labels_eval.jsonl"
    write_jsonl(train_path, train)
    write_jsonl(eval_path, eval_)
    print(
        json.dumps(
            {
                "n_labeled": len(rows),
                "n_train": len(train),
                "n_eval": len(eval_),
                "train": str(train_path),
                "eval": str(eval_path),
                "seed": args.seed,
                "train_frac": args.train_frac,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
