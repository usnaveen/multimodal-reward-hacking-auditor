# Required from the human (you)

This harness is complete as *code*. The following can **only** be provided by
you — agents must not invent them.

## 1. Real VLM runs (Apple Silicon / API)

| What | Why only you |
|------|----------------|
| 48GB (or similar) Mac with Metal + `mlx` / `mlx-vlm` | Box/CI has no MLX GPU |
| Cached model weights (e.g. Qwen2-VL-7B-Instruct-4bit) | Large download + license acceptance |
| Optional API key (`MRHA_API_KEY` or provider env) | Secrets stay on your machine |
| Actual `results/audit_records.jsonl` from a frozen audit | **Never fabricate metrics** |

```bash
python scripts/01_build_benchmark.py --n-items 200
python scripts/02_run_audit.py --backend mlx \
  --model-id mlx-community/Qwen2-VL-7B-Instruct-4bit
# Optional weak judge:
python scripts/02_run_audit.py --backend mlx --judge-backend same
```

## 2. Human detector labels (optional P/R)

File: `data/labels/detector_labels.jsonl`

Format (one JSON object per line):

```json
{"item_id": "chart_0000__evidence_swap__invariance", "label": true}
```

- `label: true` = human says the detector *should* flag (shortcut / ungrounded).
- `label: false` = should *not* flag.
- Use a **held-out** slice for reported precision/recall; do not tune on the
  same items you publish.

If the file is missing, the audit **skips P/R** and notes that in metrics.

## 3. Dataset downloads you authorize

| Source | Action |
|--------|--------|
| ChartQA (`ahmed-masry/ChartQA`) | `pip install datasets` then `python scripts/05_prepare_datasets.py --source chartqa --limit 200` |
| Chartographer / ReachQA / DocVQA | Manual clone or HF download per their licenses — see `DATASETS.md` |

Offline machines: stay on `--source synthetic` (default).

## 4. Resume / paper numbers

Fill blind-spot rate, RHR, NRFR, per-attack tables **only** from your real
`results/` outputs. Placeholders in README stay blank until then.

## 5. Best-of-n pressure (for NRFR)

NRFR needs `baseline_oracle_correct` + `proxy_improved` fields from a pressure
run — not a plain frozen audit:

```bash
python scripts/02b_best_of_n_pressure.py --backend echo --k 4   # plumbing
python scripts/02b_best_of_n_pressure.py --backend mlx --k 8    # real
```

## Checklist before claiming Phase-A results

- [ ] Built manifest with intended `n_items` / protocols / attacks
- [ ] Ran frozen audit on a real VLM (not echo-stub)
- [ ] Confirmed `results/metrics_summary.json` is from that run
- [ ] (Optional) Labeled hold-out for detector P/R
- [ ] (Optional) Best-of-n pressure for NRFR
- [ ] No invented CSV/JSON numbers committed
