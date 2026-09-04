# Improvement Log

## Round 1 — Interviewer critique (2026-09-04)

### Critiques addressed this round
- Missing real-results scaffolding / temptation to invent metrics (P0)
- NRFR path incomplete / under-documented for best-of-n pressure (P0)
- No agent × judge × attack cross-table for comparing runs (P0/P1)
- ChartQA loader fragility / mixed-build clarity (P1)
- No human-label tooling or hold-out split protocol (P1)
- No tech-report draft for interview depth (P2)
- Positioning vs Yao26 / FRAME / FOCUS too soft in README (critique #6)

### Planned fixes

| ID | Critique | Fix | Status (done/blocked/partial) | Notes |
|----|----------|-----|-------------------------------|-------|
| R1-1 | No honest results path | `results/README.md`, `scripts/06_render_results.py`, empty `RESULTS.md` placeholders | done | Exits 0 without fabricating if run files missing |
| R1-2 | NRFR / best-of-n incomplete | Harden `02b` schema; `scripts/07_compute_nrfr.py`; RESULTS docs | done | Needs real VLM pressure run for numbers |
| R1-3 | No cross table | `scripts/08_cross_table.py` + merge CLI | done | Synthetic unit tests only |
| R1-4 | ChartQA realism | Robust loader; `configs/chartqa_smoke.yaml`; mixed docs | done | HF load succeeded in upgrade env; see docs/CHARTQA_FIXTURE_NOTE.md |
| R1-5 | Human labels tooling | `09_label_detector.py`, `10_split_labels.py`, labels README | done | Human must fill true/false |
| R1-6 | Tech report | `docs/TECH_REPORT.md` with placeholders | done | No fake numbers |
| R1-7 | Differentiation in README | Sharp Yao26/FRAME/FOCUS section + links | done | |
| R1-8 | Positioning artifact | `docs/POSITIONING.md` claim vs non-claim | done | |

### Completed in this round
- Results scaffolding that refuses invented metrics
- NRFR compute script + hardened pressure-record schema (`seed` in metadata)
- Cross-table pivot script (attack × proxy, optional judge / merge)
- ChartQA column-name robustness + smoke config
- Label sampling + 70/30 hold-out split helpers
- Tech report + positioning one-pager
- README differentiation section and doc links
- Tests for NRFR helper, cross_table, label split
- Push batches under `/workspace/mrha_push_batches_r1/`

### Blocked on user
- Real MLX / API frozen audit → `results/metrics_summary.json`, `per_attack_breakdown.csv`
- Real best-of-n pressure run → NRFR curve / numbers
- Human detector labels (`data/labels/detector_labels.jsonl`)
- Resume / paper numbers (must come from real runs only)

## Template for future rounds

```
## Round N — <source> (YYYY-MM-DD)
### Critiques addressed this round
- ...
### Planned fixes
| ID | Critique | Fix | Status (done/blocked/partial) | Notes |
### Completed in this round
- ...
### Blocked on user
- ...
```
