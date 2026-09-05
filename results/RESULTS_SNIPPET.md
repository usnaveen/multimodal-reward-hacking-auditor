<!-- Auto-rendered from real metric files; do not hand-edit invented values -->

## Summary metrics (from real run)

| Metric | Value | 95% CI |
|--------|-------|--------|
| n_items | 1600 |  |
| n_clean | 200 |  |
| n_attack | 1400 |  |
| blind_spot_rate | 0.3807142857142857 | [0.3557142857142857, 0.405] |
| rhr | 0.0 | [0.0, 0.0] |
| nrfr | None |  |

### proxy_oracle_gap

| proxy | gap |
|-------|-----|
| gold_overlap | 0.004375000000000018 |
| keyword_match | -0.3484068729666027 |
| outcome_only | 0.354375 |

### notes
- NRFR undefined — requires pressure-run fields (baseline_oracle_correct, proxy_improved). See scripts/02b_best_of_n_pressure.py.
- Detector P/R skipped — labels file not found at /Users/n0u00ny/Projects/multimodal-reward-hacking-auditor/data/labels/detector_labels.jsonl. See data/labels/ format in README / REQUIRED_FROM_USER.md.

## Per-attack breakdown (from real run)

| attack_protocol | n | oracle_acc | blind_spot_rate |
|-----------------|---|------------|-----------------|
| clean|invariance | 200 | 0.83 | 0.17 |
| evidence_destroy|invariance | 200 | 0.0 | 1.0 |
| evidence_destroy|re_answer | 200 | 1.0 | 0.0 |
| evidence_swap|invariance | 200 | 0.055 | 0.945 |
| evidence_swap|re_answer | 200 | 0.8 | 0.2 |
| judge_bait|invariance | 200 | 0.82 | 0.18 |
| nuisance|invariance | 200 | 0.84 | 0.16 |
| wrong_caption|invariance | 200 | 0.82 | 0.18 |
