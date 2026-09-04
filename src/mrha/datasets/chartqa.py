"""ChartQA loader via HuggingFace ``datasets`` (optional dependency).

Uses ``ahmed-masry/ChartQA`` (test / human-oriented subset) when available.
Degrades gracefully offline with a clear message.

Column-name variants handled (HF cards differ across revisions):
  question: query | question | Question
  answer:   label | answers | answer | Answer | label_text
  image:    image | img | chart | Image
  type/src: type | split | source | human_or_augmented
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mrha.charts.generate import save_truth
from mrha.schema import (
    AttackFamily,
    AttackProtocol,
    ChartTruth,
    ChartType,
    ManifestItem,
    QuestionType,
)


_QUESTION_KEYS = ("query", "question", "Question", "query_text")
_ANSWER_KEYS = ("label", "answers", "answer", "Answer", "label_text", "ground_truth")
_IMAGE_KEYS = ("image", "img", "chart", "Image", "table_image")
_TYPE_KEYS = ("type", "split", "source", "human_or_augmented", "qa_type")


def _first(row: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for k in keys:
        if k in row and row[k] is not None:
            return row[k]
    return default


def _normalize_answer(answer: Any) -> str:
    if answer is None:
        return ""
    if isinstance(answer, list):
        if not answer:
            return ""
        answer = answer[0]
    return str(answer).strip()


def _row_keys_hint(row: dict[str, Any]) -> str:
    return ", ".join(sorted(str(k) for k in row.keys()))


def _try_load_hf(split: str = "test", subset: str = "human"):
    try:
        from datasets import load_dataset
    except ImportError as e:
        raise RuntimeError(
            "HuggingFace `datasets` is not installed. "
            "Install with: pip install 'mrha[datasets]'  "
            "or: pip install datasets  "
            "Otherwise use --source synthetic."
        ) from e
    errors: list[str] = []
    # ChartQA configs vary across HF revisions; try common patterns.
    attempts = [
        ("ahmed-masry/ChartQA", {"split": split}),
        ("ahmed-masry/ChartQA", {"name": subset, "split": split}),
        ("ahmed-masry/ChartQA", {"name": "default", "split": split}),
    ]
    for repo, kwargs in attempts:
        try:
            return load_dataset(repo, **kwargs)
        except Exception as e:  # noqa: BLE001 — surface aggregated errors
            errors.append(f"{repo} {kwargs}: {e}")
    raise RuntimeError(
        "Failed to download/load ahmed-masry/ChartQA.\n"
        + "\n".join(f"  - {e}" for e in errors)
        + "\nIf offline, use --source synthetic. "
        "See scripts/05_prepare_datasets.py and DATASETS.md."
    )


def load_chartqa_items(
    n_items: int,
    out_dir: Path | str,
    *,
    seed: int = 42,
    split: str = "test",
) -> list[ManifestItem]:
    """Load up to ``n_items`` ChartQA examples into ManifestItems.

    Images are saved under ``out_dir``. When structured truth is unavailable,
    a stub truth JSON is written; oracle uses string ``answer_gold``.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ds = _try_load_hf(split=split)

    rows: list[dict[str, Any]] = []
    for i, row in enumerate(ds):
        row = dict(row)
        src = str(_first(row, _TYPE_KEYS, "") or "")
        if "human" in src.lower() or not src:
            rows.append(row)
        if len(rows) >= n_items * 3:
            break
    if not rows:
        # Fall back to raw prefix of the split
        for i, row in enumerate(ds):
            rows.append(dict(row))
            if len(rows) >= n_items * 2:
                break
    if not rows:
        raise RuntimeError(
            "ChartQA dataset loaded but yielded zero rows. "
            f"split={split!r}. Check HF card / network."
        )
    rows = rows[:n_items]

    # Validate we can find question/answer on first row
    sample = rows[0]
    if _first(sample, _QUESTION_KEYS) is None:
        raise RuntimeError(
            "ChartQA row missing question field. "
            f"Tried keys {_QUESTION_KEYS}. Available: {_row_keys_hint(sample)}"
        )
    if _first(sample, _ANSWER_KEYS) is None:
        raise RuntimeError(
            "ChartQA row missing answer/label field. "
            f"Tried keys {_ANSWER_KEYS}. Available: {_row_keys_hint(sample)}"
        )

    items: list[ManifestItem] = []
    for i, row in enumerate(rows):
        item_id = f"chartqa_{i:04d}"
        question = str(_first(row, _QUESTION_KEYS, "") or "")
        answer_gold = _normalize_answer(_first(row, _ANSWER_KEYS))
        if not question:
            raise RuntimeError(
                f"Empty question for ChartQA row {i}. Keys: {_row_keys_hint(row)}"
            )

        img_path = out_dir / f"{item_id}.png"
        image = _first(row, _IMAGE_KEYS)
        if image is not None and hasattr(image, "save"):
            image.convert("RGB").save(img_path)
        elif isinstance(image, (str, Path)) and Path(image).is_file():
            from shutil import copy2

            copy2(str(image), img_path)
        else:
            from PIL import Image as PILImage

            PILImage.new("RGB", (400, 300), (240, 240, 240)).save(img_path)

        truth = ChartTruth(
            chart_type=ChartType.BAR,
            title=f"ChartQA {item_id}",
            categories=["A", "B"],
            values=[1.0, 2.0],
            seed=seed + i,
        )
        truth_path = out_dir / f"{item_id}_truth.json"
        save_truth(truth, truth_path)

        qtype = QuestionType.MAX_CATEGORY
        anum = None
        try:
            anum = float(str(answer_gold).replace(",", "").replace("%", ""))
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
                    "hf_split": split,
                    "row_keys": sorted(str(k) for k in row.keys()),
                    "note": "Structured series may be stubbed; gold from HF labels.",
                },
            )
        )
    return items
