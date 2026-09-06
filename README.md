# Multimodal Reward-Hacking Auditor (MRHA)

**Phase A research harness (v0.2.1)** — Interview Round 1: results scaffolding,
NRFR path, cross-tables, ChartQA robustness, label tooling, tech report &
positioning (still dual protocols / honest proxies / CI).

Public repo: [github.com/usnaveen/multimodal-reward-hacking-auditor](https://github.com/usnaveen/multimodal-reward-hacking-auditor)

> **Oracle policy:** ground truth comes from **executable chart JSON** (synthetic)
> or dataset labels (ChartQA strings). A VLM judge is a **proxy only**, never truth.
> **Do not invent metric results.**

---

## Upgrade notes (0.1.0 → 0.2.0)

| Area | Change |
|------|--------|
| Protocols | `invariance` vs `re_answer` on evidence attacks (fixes gold/oracle design bug) |
| Proxies | `gold_overlap` explicit; `weak_vlm_judge` **requires** `--judge-backend` |
| Attacks | `judge_bait` never paints gold; added `nuisance`; richer swap modes / captions |
| Oracle | Prefer `Answer: <value>`; exclusive wrong-category reject; `oracle_mode` |
| Metrics | Per-attack CSV, bootstrap 95% CI, `nrfr()` (needs pressure run) |
| Data | Default `n_items: 200`; ChartQA + `DATASETS.md`; `--source mixed` |
| Eng | CI workflow, expanded tests, `REQUIRED_FROM_USER.md` |

---

## 1. Problem statement & novelty

Chart-VQA agents (and VLM-as-judge pipelines) can look strong under weak
evaluation proxies while failing an **executable oracle**. That **proxy–oracle
gap** is the multimodal analogue of reward hacking.

**Novelty claim:** an integration harness with executable oracles, dual
evidence protocols, attack families (incl. FP-control nuisance), honest proxy
split, RHR + NRFR scaffolding, and MLX runner — **not** a new foundation model
and **not** fabricated leaderboard numbers.

Related anchors: Yao26 (RHR/NRFR), Hwa25 FRAME, Kha26c FOCUS, Zha26, Wu24.
See `PLAN.md`.

---


## How this differs from Yao26 / FRAME / FOCUS

| Work | Center of gravity | MRHA |
|------|-------------------|------|
| **Yao26** | Multimodal reward hacking under RL; defines **RHR** & **NRFR** | Same *metric language*; we ship an **audit harness** + best-of-n pressure scaffold — **we do not claim** their full RL runs or numbers |
| **FRAME (Hwa25)** | Fooling LVLM *judges* with visual framing | FRAME-like `judge_bait` **inside** agent audits with executable oracles; baits never paint gold; plus `nuisance` FP control |
| **FOCUS (Kha26c)** | Evaluator blind spots / perturbation thinking | Dual **invariance / re_answer** gold protocols + honest proxy/judge split — **not** a FOCUS reproduction |

**Claim:** measurable proxy–oracle gaps for chart-VQA under controlled attacks.
**Non-claim:** SOTA VLM, full Yao26 RL, or invented leaderboard metrics.

One-pager: [`docs/POSITIONING.md`](docs/POSITIONING.md). Longer: [`docs/TECH_REPORT.md`](docs/TECH_REPORT.md).

---

## 2. Dual evidence protocols

| Protocol | Gold label | Oracle success on evidence attack means |
|----------|------------|----------------------------------------|
| **invariance** | Stays = clean gold | Model still outputs **old** gold → **shortcut flag**; metadata also stores `visual_answer_gold` for separate “correct on new image” scoring |
| **re_answer** | Updates to new visual truth | Model matches **new** gold → grounded re-reading |

Configured in `configs/default.yaml`:

```yaml
protocols: [invariance, re_answer]
```

Manifest + audit records both store `protocol`.

---

## 3. What is implemented vs what you must run

| Component | Status |
|-----------|--------|
| Synthetic charts + truth JSON (default N=200) | ✅ |
| Dual protocols on evidence_swap / evidence_destroy | ✅ |
| Attacks: swap, destroy, wrong_caption, judge_bait, nuisance | ✅ |
| Proxies: outcome_only, keyword_match, gold_overlap | ✅ default |
| weak_vlm_judge | ✅ only with `--judge-backend` |
| Metrics + per-attack CSV + bootstrap CI + NRFR hook | ✅ |
| best-of-n pressure script (`02b`) | ✅ scaffolding |
| ChartQA loader (optional `datasets`) | ✅ graceful offline fail |
| Detector P/R from labels file | ✅ skip if missing |
| MLX / API clients | ✅ you run on Mac / with keys |
| Real audit accuracies | ❌ **you produce — never fabricate** |

See **`REQUIRED_FROM_USER.md`** and **`DATASETS.md`**.

---

## 4. Setup

```bash
git clone https://github.com/usnaveen/multimodal-reward-hacking-auditor.git
cd multimodal-reward-hacking-auditor
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# Optional ChartQA: pip install -e ".[dev,datasets]"
# Apple Silicon MLX: pip install -e ".[dev,mlx]"
```

---

## 5. Commands

```bash
# Build (synthetic default)
python scripts/01_build_benchmark.py
python scripts/01_build_benchmark.py --source chartqa --n-items 50
python scripts/01_build_benchmark.py --source mixed --n-items 200

# Smoke (any machine)
python scripts/04_smoke_test.py
pytest -q

# Frozen audit
python scripts/02_run_audit.py --backend echo --limit 5          # plumbing
python scripts/02_run_audit.py --backend mlx --model-id mlx-community/Qwen2-VL-7B-Instruct-4bit
python scripts/02_run_audit.py --backend mlx --judge-backend same  # adds weak_vlm_judge

# Legacy best-of-n plumbing (echo output is never research evidence)
python scripts/02b_best_of_n_pressure.py --backend echo --k 4

# Causal pressure smoke: paired selectors, complete candidates, stub-gated
uv run --active --no-sync python scripts/11_run_causal_pressure.py \
  --backend echo --model-id echo-stub --k 4 --parent-limit 2 \
  --results-dir results/causal_pressure_smoke

# Re-analyze stored candidates without new model/API calls
uv run --active --no-sync python scripts/12_analyze_causal_pressure.py \
  results/causal_pressure_smoke/pressure_records.jsonl

# Metrics recompute
python scripts/03_compute_metrics.py

# Optional dataset prep / tiny mixed smoke
python scripts/05_prepare_datasets.py --source chartqa --limit 200
python scripts/01_build_benchmark.py --config configs/chartqa_smoke.yaml

# Render tables/figures (no-op fabricate: exits 0 if no real metrics)
python scripts/06_render_results.py
python scripts/07_compute_nrfr.py --pressure-jsonl results/best_of_n/pressure_records.jsonl
python scripts/08_cross_table.py --records results/audit_records.jsonl --out results/cross_table

# Human detector labels + hold-out split
python scripts/09_label_detector.py --file-only --n 40
python scripts/10_split_labels.py --train-frac 0.7
```

---

## 6. Causal pressure experiment

The frozen audit is a robustness/proxy-calibration pilot, not causal evidence
of reward hacking. The confirmatory experiment generates and preserves `k`
real-model candidates, then applies random, proxy, and oracle selectors to the
same candidate set. It reports proxy gain, paired visual-oracle delta,
correct-to-incorrect regression, incorrect-to-correct rescue, false acceptance,
and parent-cluster bootstrap confidence intervals.

Evidence-attack `invariance` rows are excluded from visual-correctness
endpoints because they intentionally retain old gold. `echo-stub` runs are
always marked non-research. See
[`docs/CAUSAL_PRESSURE_PROTOCOL.md`](docs/CAUSAL_PRESSURE_PROTOCOL.md) for the
predeclared hypothesis, controls, eligibility rules, and real-run commands.

---

## 7. Attacks & proxies

| Attack | Idea |
|--------|------|
| `evidence_swap` | permute / swap-max-min / reverse; before/after values in metadata |
| `evidence_destroy` | blur + occlude; re_answer gold → `unanswerable` |
| `wrong_caption` | expanded CoT/caption templates; wrong ≠ gold |
| `judge_bait` | brightness, padding, VERIFIED/HIGH QUALITY stamps — **no gold on image** |
| `nuisance` | slight crop/pad/color — should **not** change answer (FP control) |

| Proxy | Idea |
|-------|------|
| `outcome_only` | non-empty response |
| `keyword_match` | token Jaccard vs gold |
| `gold_overlap` | explicit gold substring proxy (not a VLM) |
| `weak_vlm_judge` | strict YES/NO (or 0–10) via VLMClient — **requires judge backend** |

| Metric | Idea |
|--------|------|
| `blind_spot_rate` | attack items: oracle fail ∧ max **non-trivial** proxy ≥ 0.5; excludes always-pass `outcome_only` (+ bootstrap CI) |
| `proxy_oracle_gap` | mean(proxy) − mean(oracle) |
| `RHR` | P(proxy pass ∧ oracle fail) / P(proxy pass) |
| `NRFR` | needs pressure-run metadata; see `02b_best_of_n_pressure.py` |

---

## 8. Layout & docs

```
src/mrha/           # package (datasets/, attacks/, proxies/, …)
scripts/            # build/audit plus causal pressure runner + offline analysis
configs/            # default.yaml, chartqa_smoke.yaml
data/benchmark/     # generated
data/labels/        # detector labels + hold-out (see data/labels/README.md)
results/            # audit outputs (never invent) — see results/README.md
docs/               # TECH_REPORT.md, POSITIONING.md
RESULTS.md          # real frozen-audit results + explicit limitations
IMPROVEMENT_LOG.md  # Round 1+ interview fixes
INTERVIEW_PREP.md
DATASETS.md
REQUIRED_FROM_USER.md
PLAN.md
.github/workflows/ci.yml
```

| Doc | Role |
|-----|------|
| [docs/CAUSAL_PRESSURE_PROTOCOL.md](docs/CAUSAL_PRESSURE_PROTOCOL.md) | Preregistered causal hypothesis, controls, metrics, commands |
| [INTERVIEW_PREP.md](INTERVIEW_PREP.md) | Concepts, papers, talking points |
| [IMPROVEMENT_LOG.md](IMPROVEMENT_LOG.md) | Interviewer critiques → fixes |
| [RESULTS.md](RESULTS.md) | Result placeholders (no fake numbers) |
| [docs/TECH_REPORT.md](docs/TECH_REPORT.md) | 4–6pp methods writeup |
| [docs/POSITIONING.md](docs/POSITIONING.md) | Claim vs non-claim one-pager |

---

## 8. Resume bullet draft (placeholder)

> Built MRHA v0.2: dual-protocol chart-VQA reward-hacking harness with
> executable oracles, nuisance FP controls, honest proxy/judge split, RHR/NRFR
> scaffolding, and MLX runner. **[Fill after real 48GB audit — do not invent].**

---

## 9. License

MIT — see `LICENSE`. Third-party datasets: see `DATASETS.md`.
