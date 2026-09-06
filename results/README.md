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
4. **Causal proxy pressure** (preferred confirmatory experiment):
   ```bash
   uv run --active --no-sync python scripts/11_run_causal_pressure.py \
     --backend anthropic --model-id <agent-id> --temperature 0.7 \
     --k 4 --parent-limit 100 --results-dir results/causal_pressure/<run> \
     --dry-run
   # Review API volume/cost, then remove --dry-run to execute.
   uv run --active --no-sync python scripts/12_analyze_causal_pressure.py \
     results/causal_pressure/<run>/pressure_records.jsonl
   ```
   This preserves all candidates and reports paired proxy gain, oracle delta,
   regression, rescue, false acceptance, and parent-cluster confidence
   intervals. Different `k` values and seeds require separate directories.
5. **Legacy best-of-n / NRFR plumbing**:
   `02b` and `07` remain for compatibility. Echo output is never evidence.
6. **Render frozen-audit markdown / figures** (only if real files exist):
   ```bash
   python scripts/06_render_results.py
   ```
7. **Cross-table** (agent-only vs agent+judge, etc.):
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
| Real causal `pressure_records.jsonl` + hashed run metadata | optional after review |
| Echo-stub causal/NRFR summaries | no; plumbing only |
| Invented metrics | **never** |

See root `RESULTS.md` for the corrected pilot and
`docs/CAUSAL_PRESSURE_PROTOCOL.md` for the confirmatory design.
