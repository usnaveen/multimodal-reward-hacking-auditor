# ChartQA fixture note (Round 1)

**Status:** `datasets` install + tiny load **succeeded** in the upgrade environment
on 2026-09-04.

- HF repo: `ahmed-masry/ChartQA` (split=test)
- Observed row keys: `['image', 'imgname', 'label', 'query', 'type']`
- Loader smoke: `load_chartqa_items(1, …)` → item_id=`chartqa_0000`,
  question non-empty=True, gold=`'14'`

Use `configs/chartqa_smoke.yaml` for mixed local smokes. Images are not
vendored in-repo (license); re-download via `scripts/05_prepare_datasets.py`.
