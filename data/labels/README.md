# Detector labels (human)

Optional precision/recall for shortcut / reward-hack detectors.

## Protocol

1. Build a benchmark manifest (`scripts/01_build_benchmark.py`).
2. Sample attacked items into a template:
   ```bash
   python scripts/09_label_detector.py --file-only --n 40 --seed 0
   ```
   Or interactive:
   ```bash
   python scripts/09_label_detector.py --n 40
   ```
3. Open `detector_labels.jsonl` and set each `label` to `true` or `false`:
   - `true` — detector **should** flag (shortcut / ungrounded / gaming-like)
   - `false` — detector **should not** flag (e.g. nuisance / still grounded)
4. **Hold-out split** (default 70% train / 30% eval) — do **not** tune and
   report on the same slice:
   ```bash
   python scripts/10_split_labels.py --train-frac 0.7 --seed 0
   ```
   Writes `detector_labels_train.jsonl` and `detector_labels_eval.jsonl`.
5. Report P/R only on the **eval** file.

## Schema

```json
{"item_id": "...", "attack": "evidence_swap", "protocol": "invariance", "label": true, "notes": ""}
```

Rows with `"label": null` are ignored by the split script until filled.

## Policy

- Humans only set labels — agents must not invent gold detector flags.
- Prefer labeling a mix of attacks including `nuisance` (FP control).
