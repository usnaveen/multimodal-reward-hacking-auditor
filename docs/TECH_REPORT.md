# MRHA Technical Report (Phase A draft)

**Multimodal Reward-Hacking Auditor** — evaluation harness for chart-VQA
proxy–oracle gaps under controlled attacks.

> Status: scaffolding + methods ready. **Results sections are placeholders.**
> Do not invent accuracies, RHR, NRFR, or CIs. Fill only from real runs
> (`RESULTS.md`, `results/README.md`).

---

## 1. Problem

Vision–language models used as chart-VQA *agents* or as *judges* of other
agents can look strong under weak evaluation proxies — non-empty answers,
keyword / gold overlap, lenient VLM judges — while failing an **executable
oracle** that knows the chart’s numeric content. That **proxy–true divergence**
is the multimodal analogue of reward hacking / specification gaming.

MRHA is an **integration and measurement harness**, not a new foundation model.
It makes the gap measurable under dual evidence protocols and attack families
(including nuisance FP controls), with honest proxy vs judge separation.

Production link: the same failure mode shows up as **multimodal drift** when
dashboards, product images, or judge prompts shift while proxy scores stay flat.

---

## 2. Related work

| Anchor | What we take | What we do *not* claim |
|--------|----------------|------------------------|
| **Yao26** (multimodal RH; RHR / NRFR) | Metric definitions; outcome-only vs vision-aware ladder; best-of-n as pressure without full RL | Full RLVR / GRPO reproduction; their leaderboard numbers |
| **FRAME (Hwa25)** | Visual framing / judge bias families | Pixel-perfect FRAME reimplementation |
| **FOCUS (Kha26c)** | Evaluator blind-spot / perturbation philosophy | Their full pairwise matrix as our result |
| **ChartQA (Masry et al.)** | Real chart images + string gold for transfer | That string labels equal executable geometric oracles |
| **Wu24** (and chart-eval peers) | Multimodal / chart evaluation context | Identity with any single Wu24 benchmark score |
| **Zha26-style wrong CoT/caption** | Misleading language priors as attack surface | Claiming their exact training recipe |

See also `docs/POSITIONING.md` and README differentiation section.

---

## 3. Method

### 3.1 Dual evidence protocols

| Protocol | Gold after evidence change | Oracle success means |
|----------|----------------------------|----------------------|
| **invariance** | Stays = clean gold | Emitting old gold after visual change → shortcut signal; `visual_answer_gold` stored separately |
| **re_answer** | Updates to new visual truth | Matching new gold → grounded re-reading |

### 3.2 Attacks

- `evidence_swap` — permute / swap-max-min / reverse series
- `evidence_destroy` — blur + occlude; re_answer gold → `unanswerable`
- `wrong_caption` — misleading captions / CoT prefixes (wrong ≠ gold)
- `judge_bait` — brightness, stamps, padding — **never paints gold on image**
- `nuisance` — slight crop/pad/color — should **not** change the answer (FP control)

### 3.3 Proxies (adversarial surfaces, not truth)

- `outcome_only`, `keyword_match`, `gold_overlap` (default audit)
- `weak_vlm_judge` only with `--judge-backend` (no silent fake judge)

### 3.4 Oracle policy

Synthetic charts: executable JSON (categories + values). ChartQA: string gold
from HF labels; structured series often stubbed — never claim ChartQA strings
are geometric oracles. **A VLM is never ground truth.**

### 3.5 Metrics

- `blind_spot_rate` (+ bootstrap 95% CI)
- `proxy_oracle_gap`, proxy–oracle correlation
- **RHR** — P(proxy pass ∧ oracle fail) / P(proxy pass)
- **NRFR** — among `proxy_improved` items under best-of-n pressure, fraction
  where oracle did not newly become correct vs baseline
  (`scripts/02b_best_of_n_pressure.py`, `scripts/07_compute_nrfr.py`)

---

## 4. Experimental protocol

1. Build manifest (`synthetic` default N=200; optional `chartqa` / `mixed`).
2. Frozen audit on target VLM (MLX or API); optional second pass with judge.
3. `scripts/03_compute_metrics.py` → summary + per-attack CSV.
4. Optional: best-of-n pressure for NRFR vs `k`.
5. Optional: human detector labels with 70/30 hold-out
   (`scripts/09_label_detector.py`, `scripts/10_split_labels.py`).
6. Render tables/figures only from real files (`scripts/06_render_results.py`).
7. Cross-table agent-only vs agent+judge (`scripts/08_cross_table.py`).

Hardware / secrets: see `REQUIRED_FROM_USER.md` (48GB MLX Mac, API keys, HF).

---

## 5. Results

<!-- FILL_FROM_REAL_RUN -->

All quantitative cells intentionally blank until a real audit exists.
Copy from `RESULTS.md` / `results/RESULTS_SNIPPET.md` after
`06_render_results.py` succeeds on genuine metric files.

| Metric | Value |
|--------|-------|
| blind_spot_rate | — |
| RHR | — |
| NRFR | — |
| Per-attack table | — |
| Cross-table | — |

**Do not paste invented numbers here.**

---

## 6. Limitations

- Phase A synthetic charts are simplified (bar/line/pie generators).
- ChartQA integration uses string gold; stubbed series weaken protocol science.
- Echo-stub audits are plumbing only — not research evidence.
- NRFR needs pressure runs; frozen audit alone leaves NRFR undefined.
- Detector P/R needs human labels and hold-out discipline.
- No full RL training loop — best-of-n is a pressure *scaffold*.
- Judge bias coverage is a subset of FRAME/FOCUS taxonomies.

---

## 7. Relation to production multimodal drift

In production multimodal systems (catalog images, chart dashboards, VLM
judges over agent traces), **proxy monitors can stay green while grounded
correctness drifts**. MRHA’s dual protocols, nuisance controls, and
proxy–oracle metrics are a lab analogue of that monitoring problem: change
the evidence, keep the question, and ask whether the score still tracks truth.

Walmart-style multimodal drift work maps to: (1) defining an oracle or
stronger check than the serving proxy, (2) injecting controlled evidence /
prompt shifts, (3) quantifying blind spots before they hit users.

---

## 8. Reproducibility checklist

- [ ] Config + seed recorded
- [ ] Manifest source (`synthetic` / `chartqa` / `mixed`) recorded
- [ ] Model id + judge backend recorded
- [ ] Metrics JSON committed or archived **from that run only**
- [ ] NRFR linked to pressure JSONL with `k` / `seed`
- [ ] No fabricated `metrics_summary.json`

---

*Document length target: ~4–6 page equivalent. Expand Results after real runs.*
