"""ChartQA loader via HuggingFace ``datasets`` (optional dependency).

Uses ``ahmed-masry/ChartQA`` test/human split subset when available.
Degrades gracefully offline with a clear message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mrha.charts.generate import render_chart, save_truth
from mrha.schema import (
    AttackFamily,
    AttackProtocol,
    ChartTruth,
    ChartType,
    ManifestItem,
    QuestionType,
)


def _try_load_hf(split: str = "test", subset: str = "human"):
    try:
        from datasets import load_dataset
    except ImportError as e:
        raise RuntimeError(
            "HuggingFace `datasets` is not installed. "
            "Install with: pip install datasets  "
            "or use --source synthetic."
        ) from e
    try:
        # ChartQA configs vary; try common patterns
        try:
            ds = load_dataset("ahmed-masry/ChartQA", split=split)
        except Exception:
            ds = load_dataset("ahmed-masry/ChartQA", subset, split=split)
        return ds
    except Exception as e:
        raise RuntimeError(
            f"Failed to download/load ahmed-masry/ChartQA ({e}). "
            "If offline, use --source synthetic. "
            "See scripts/05_prepare_datasets.py."
        ) from e


def _row_to_truth(row: dict[str, Any], seed: int) -> ChartTruth | None:
    """Best-effort extract categories/values if present; else None."""
    # Many ChartQA rows lack structured series; we store QA gold only.
    return None


def load_chartqa_items(
    n_items: int,
    out_dir: Path | str,
    *,
    seed: int = 42,
    split: str = "test",
) -> list[ManifestItem]:
    """Load up to ``n_items`` ChartQA human-split examples into ManifestItems.

    Images are copied/saved under ``out_dir``. When structured truth is
    unavailable, a stub truth JSON is written with the string gold answer in
    metadata (oracle still uses answer_gold substring / Answer: parsing).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = _try_load_hf(split=split)
    # Filter human if column exists
    rows = []
    for i, row in enumerate(ds):
        # human split heuristics
        src = str(row.get("type") or row.get("split") or row.get("source") or "")
        if "human" in src.lower() or not src:
            rows.append(row)
        if len(rows) >= n_items * 3:  # oversample then truncate
            break
    if not rows:
        rows = list(ds)[: n_items * 2]
    rows = rows[:n_items]

    items: list[ManifestItem] = []
    for i, row in enumerate(rows):
        item_id = f"chartqa_{i:04d}"
        question = str(row.get("query") or row.get("question") or "")
        answer = row.get("label") or row.get("answers") or row.get("answer")
        if isinstance(answer, list):
            answer = answer[0] if answer else ""
        answer_gold = str(answer)

        img_path = out_dir / f"{item_id}.png"
        # Image may be PIL or path
        image = row.get("image")
        if image is not None and hasattr(image, "save"):
            image.convert("RGB").save(img_path)
        elif isinstance(image, str) and Path(image).is_file():
            from shutil import copy2

            copy2(image, img_path)
        else:
            # Placeholder blank if image missing
            from PIL import Image as PILImage

            PILImage.new("RGB", (400, 300), (240, 240, 240)).save(img_path)

        # Stub truth — ChartQA often lacks executable series
        truth = ChartTruth(
            chart_type=ChartType.BAR,
            title=f"ChartQA {item_id}",
            categories=["A", "B"],
            values=[1.0, 2.0],
            seed=seed + i,
        )
        truth_path = out_dir / f"{item_id}_truth.json"
        save_truth(truth, truth_path)

        # Guess question type
        qtype = QuestionType.MAX_CATEGORY
        anum = None
        try:
            anum = float(str(answer_gold).replace(",", ""))
            qtype = QuestionType.VALUE_OF
        except ValueError:
            pass

        items.append(
            ManifestItem(
                item_id=item_id,
                parent_id=None,
                attack=AttackFamily.CLEAN,
                protocol=AttackProtocol.INVARIANCE,
                chart_type=ChartType.BAR,
                image_path=str(img_path),
                truth_path=str(truth_path),
                question=question,
                question_type=qtype,
                answer_gold=answer_gold,
                answer_numeric=anum,
                caption=None,
                prompt_prefix=None,
                metadata={
                    "seed": seed + i,
                    "source": "chartqa",
                    "hf_dataset": "ahmed-masry/ChartQA",
                    "note": "Structured series may be stubbed; gold from HF labels.",
                },
            )
        )
    return items
