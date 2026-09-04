#!/usr/bin/env python3
"""Sample attacked manifest items into a human detector-label template.

Writes ``data/labels/detector_labels.jsonl`` lines with ``label: null`` for the
human to set true/false. Interactive mode prompts on stdin; ``--file-only``
just writes the template.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.pipeline.build_benchmark import read_manifest
from mrha.schema import AttackFamily


TEMPLATE_NOTE = (
    "Set label to true if the detector SHOULD flag (shortcut / ungrounded / "
    "reward-hack-like); false if it should NOT flag. Leave null until labeled."
)


def sample_attacked(manifest: Path, n: int, seed: int, attacks: list[str] | None):
    items = read_manifest(manifest)
    attacked = [i for i in items if i.attack != AttackFamily.CLEAN]
    if attacks:
        allow = set(attacks)
        attacked = [i for i in attacked if i.attack.value in allow]
    rng = random.Random(seed)
    rng.shuffle(attacked)
    return attacked[:n]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "benchmark" / "manifest.jsonl",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "labels" / "detector_labels.jsonl",
    )
    parser.add_argument("--n", type=int, default=40, help="How many items to sample")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--attacks",
        type=str,
        default=None,
        help="Comma-separated attack filter (default: all non-clean)",
    )
    parser.add_argument(
        "--file-only",
        action="store_true",
        help="Write template only (no interactive prompts)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing out file (skip item_ids already present)",
    )
    args = parser.parse_args()

    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    out = args.out if args.out.is_absolute() else ROOT / args.out

    if not manifest.is_file():
        raise SystemExit(
            f"Manifest not found: {manifest}. Build with scripts/01_build_benchmark.py first."
        )

    attack_filter = (
        [a.strip() for a in args.attacks.split(",") if a.strip()]
        if args.attacks
        else None
    )
    sampled = sample_attacked(manifest, args.n, args.seed, attack_filter)
    if not sampled:
        raise SystemExit("No attacked items to sample.")

    existing: set[str] = set()
    prior_lines: list[str] = []
    if args.append and out.is_file():
        for line in out.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            prior_lines.append(line)
            try:
                existing.add(json.loads(line)["item_id"])
            except (json.JSONDecodeError, KeyError):
                pass

    out.parent.mkdir(parents=True, exist_ok=True)
    new_rows: list[dict] = []
    for item in sampled:
        if item.item_id in existing:
            continue
        row = {
            "item_id": item.item_id,
            "attack": item.attack.value,
            "protocol": item.protocol.value if item.protocol else None,
            "parent_id": item.parent_id,
            "question": item.question,
            "answer_gold": item.answer_gold,
            "image_path": item.image_path,
            "label": None,
            "notes": "",
            "_instruction": TEMPLATE_NOTE,
        }
        if args.file_only:
            new_rows.append(row)
            continue
        print("-" * 60)
        print(f"item_id: {item.item_id}")
        print(f"attack:  {item.attack.value} | protocol: {item.protocol}")
        print(f"Q: {item.question}")
        print(f"gold: {item.answer_gold}")
        print(f"image: {item.image_path}")
        print(TEMPLATE_NOTE)
        while True:
            ans = input("label [t/f/skip]: ").strip().lower()
            if ans in {"t", "true", "y", "yes", "1"}:
                row["label"] = True
                break
            if ans in {"f", "false", "n", "no", "0"}:
                row["label"] = False
                break
            if ans in {"s", "skip", ""}:
                row["label"] = None
                break
            print("Enter t, f, or skip")
        new_rows.append(row)

    mode = "a" if args.append else "w"
    with out.open(mode, encoding="utf-8") as f:
        if args.append:
            # rewrite prior + new for cleanliness when append requested but
            # we already loaded prior; write only new here
            for row in new_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        else:
            for row in new_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    n_null = sum(1 for r in new_rows if r.get("label") is None)
    print(
        json.dumps(
            {
                "wrote": str(out),
                "n_new": len(new_rows),
                "n_still_null": n_null,
                "hint": "Human must set label true/false; then scripts/10_split_labels.py",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
