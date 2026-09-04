# Results directory

This folder holds **outputs of real audit / pressure runs only**.

## How results get produced

1. **Build** a manifest:
   ```bash
   python scripts/01_build_benchmark.py --config configs/default.yaml
   # or: configs/chartqa_smoke.yaml for a tiny mixed smoke
   ```
2. **Frozen audit** (real VLM or `echo` plumbing):
   ```bash
   python scripts/02_run_audit.py --backend mlx --model-id <id>
   # optional judge:
   python scripts/02_run_audit.py --backend mlx --judge-backend same
   ```
   Writes e.g. `results/audit_records.jsonl`.
3. **Metrics**:
   ```bash
   python scripts/03_compute_metrics.py
   ```
   Writes `results/metrics_summary.json`, `metrics_summary.csv`,
   `per_attack_breakdown.csv`, `audit_records.csv`.
4. **Best-of-n pressure → NRFR** (separate from frozen audit):
   ```bash
   python scripts/02b_best_of_n_pressure.py --backend mlx --k 8
   python scripts/07_compute_nrfr.py --pressure-jsonl results/best_of_n/pressure_records.jsonl
   ```
5. **Render markdown / figures** (only if real files exist):
   ```bash
   python scripts/06_render_results.py
   ```
6. **Cross-table** (agent-only vs agent+judge, etc.):
   ```bash
   python scripts/08_cross_table.py \
     --records results/audit_records.jsonl \
     --out results/cross_table
   ```

## Forbidden

- **Do not invent** audit accuracies, RHR, NRFR, blind-spot rates, or CIs.
- **Do not commit** fabricated `metrics_summary.json` that looks like a completed model run.
- Echo-stub plumbing runs are for CI/smoke only — do not present them as research numbers.

## What is safe to commit

| Path | OK? |
|------|-----|
| `results/.gitkeep` | yes |
| `results/example_schema.json` | yes (schema only) |
| `results/README.md` | yes |
| `results/figures/.gitkeep` | yes |
| Real `metrics_*.json/csv` from your machine | optional; prefer local until reviewed |
| Invented metrics | **never** |

See root `RESULTS.md` (placeholders only) and `REQUIRED_FROM_USER.md`.
