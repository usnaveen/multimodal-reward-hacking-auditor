# Results

> **Policy:** Do not invent numbers. Fill sections only from real
> `results/metrics_summary.json` / pressure JSONL produced on your machine.
> See `results/README.md` and `scripts/06_render_results.py`.

## Summary metrics

<!-- FILL_FROM_REAL_RUN -->

| Metric | Value | 95% CI | Notes |
|--------|-------|--------|-------|
| n_items | — | — | <!-- FILL_FROM_REAL_RUN --> |
| blind_spot_rate | — | — | <!-- FILL_FROM_REAL_RUN --> |
| RHR | — | — | <!-- FILL_FROM_REAL_RUN --> |
| NRFR | — | — | Requires best-of-n pressure; see below |
| proxy_oracle_gap | — | — | <!-- FILL_FROM_REAL_RUN --> |

## Per-attack breakdown

<!-- FILL_FROM_REAL_RUN -->

| attack_protocol | n | oracle_acc | blind_spot_rate |
|-----------------|---|------------|-----------------|
| — | — | — | — |

## Agent × proxy × attack (cross-table)

Produce with:

```bash
python scripts/08_cross_table.py \
  --records results/audit_records.jsonl \
  --out results/cross_table
# Merge agent-only vs agent+judge:
python scripts/08_cross_table.py \
  --records results/agent_only/audit_records.jsonl \
  --records-b results/agent_judge/audit_records.jsonl \
  --label-a agent_only --label-b agent_plus_judge \
  --out results/cross_table_merged
```

<!-- FILL_FROM_REAL_RUN -->

## NRFR curve (best-of-n pressure)

NRFR is **undefined** on a plain frozen audit. Produce pressure records first:

```bash
python scripts/02b_best_of_n_pressure.py --backend mlx --k 4 --seed 0
python scripts/02b_best_of_n_pressure.py --backend mlx --k 8 --seed 0
# …vary k as needed…
python scripts/07_compute_nrfr.py \
  --pressure-jsonl results/best_of_n/pressure_records.jsonl \
  --out results/nrfr_summary.json
python scripts/06_render_results.py  # renders tables/figures if inputs exist
```

### Pressure record schema (required fields)

Each JSONL line from `02b` includes AuditRecord fields plus metadata:

| Field | Where | Meaning |
|-------|-------|---------|
| `oracle_correct` | top-level | Oracle on **best-of-k** (proxy-max) response |
| `metadata.baseline_oracle_correct` | metadata | Oracle on baseline / greedy response |
| `metadata.proxy_improved` | metadata | Best proxy score > baseline proxy |
| `metadata.k` | metadata | Sample size `k` |
| `metadata.seed` | metadata | RNG seed for this pressure run |
| `metadata.pressure` | metadata | `"best_of_n"` |
| `proxy_scores[<proxy>]` | top-level | Best-of-k proxy score |
| `proxy_scores.baseline_proxy` | top-level | Baseline proxy score |

<!-- FILL_FROM_REAL_RUN: NRFR vs k table / figure — no fake curve data -->

| k | n | NRFR | notes |
|---|---|------|-------|
| — | — | — | <!-- FILL_FROM_REAL_RUN --> |

## Figures

Optional PNGs land in `results/figures/` when `scripts/06_render_results.py`
finds real metric files. Do not hand-draw fake charts.

## Detector P/R (human labels)

See `data/labels/README.md`. Hold-out split via `scripts/10_split_labels.py`.

<!-- FILL_FROM_REAL_RUN -->
