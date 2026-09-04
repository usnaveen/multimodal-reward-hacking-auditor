# Multimodal Reward-Hacking Auditor (MRHA)

**Phase A research harness (v0.2.0)** — upgrade from toy MVP: dual evidence
protocols, honest proxies, nuisance controls, ChartQA loader, best-of-n NRFR
scaffolding, and CI.

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

# Best-of-n pressure → NRFR fields
python scripts/02b_best_of_n_pressure.py --backend echo --k 4

# Metrics recompute
python scripts/03_compute_metrics.py

# Optional dataset prep
python scripts/05_prepare_datasets.py --source chartqa --limit 200
```

---

## 6. Attacks & proxies

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
| `blind_spot_rate` | attack items: oracle fail ∧ max proxy ≥ 0.5 (+ bootstrap CI) |
| `proxy_oracle_gap` | mean(proxy) − mean(oracle) |
| `RHR` | P(proxy pass ∧ oracle fail) / P(proxy pass) |
| `NRFR` | needs pressure-run metadata; see `02b_best_of_n_pressure.py` |

---

## 7. Layout

```
src/mrha/           # package (datasets/, attacks/, proxies/, …)
scripts/            # 01 build, 02 audit, 02b pressure, 03 metrics, 04 smoke, 05 data
configs/default.yaml
data/benchmark/     # generated
data/labels/        # optional detector_labels.jsonl
results/            # audit outputs (never invent)
DATASETS.md
REQUIRED_FROM_USER.md
PLAN.md
.github/workflows/ci.yml
```

---

## 8. Resume bullet draft (placeholder)

> Built MRHA v0.2: dual-protocol chart-VQA reward-hacking harness with
> executable oracles, nuisance FP controls, honest proxy/judge split, RHR/NRFR
> scaffolding, and MLX runner. **[Fill after real 48GB audit — do not invent].**

---

## 9. License

MIT — see `LICENSE`. Third-party datasets: see `DATASETS.md`.

## Interview prep

See [`INTERVIEW_PREP.md`](INTERVIEW_PREP.md) for concepts-in-order, paper reading list, and mock interview questions.
