# MRHA Technical Report (Phase A draft)

**Multimodal Reward-Hacking Auditor** — evaluation harness for chart-VQA
proxy–oracle gaps under controlled attacks.

> Status: completed frozen robustness/metric-validity pilot plus implemented,
> preregistered causal pressure protocol. The real-model causal run is pending.
> Do not promote frozen perturbations or echo-stub pressure output as
> reward-hacking evidence.

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

- `blind_spot_rate` (+ bootstrap 95% CI), defined as oracle failure while
  at least one non-trivial proxy passes; always-pass `outcome_only` is
  excluded from this max-proxy metric and reported separately as a gap
- `proxy_oracle_gap`, proxy–oracle correlation
- **RHR** — P(proxy pass ∧ oracle fail) / P(proxy pass)
- **NRFR** — among `proxy_improved` items under best-of-n pressure, fraction
  where oracle did not newly become correct vs baseline
  (`scripts/02b_best_of_n_pressure.py`, `scripts/07_compute_nrfr.py`)

### 3.6 Causal proxy pressure

The confirmatory protocol stores one greedy baseline and `k` stochastic
real-model candidates per item. Random, proxy-max, and oracle-max selectors
operate on the identical candidate set. Primary outcomes are selected-minus-
baseline visual accuracy, proxy gain, correct-to-incorrect regression,
incorrect-to-correct rescue, and false acceptance. Confidence intervals
resample parent charts rather than correlated attack derivatives. See
`docs/CAUSAL_PRESSURE_PROTOCOL.md` and scripts 11–12.

Evidence-attack invariance rows are excluded from visual correctness endpoints:
matching their intentionally retained old gold measures answer persistence,
not correctness for the displayed chart.

---

## 4. Experimental protocol

1. Build a hash-recorded manifest (`synthetic` default; optional transfer data).
2. Treat the completed frozen audit as a robustness/proxy-validity pilot.
3. Run causal pressure with a greedy baseline and stored stochastic candidates.
4. Apply random, proxy, independent-judge, and oracle selectors to the same candidates.
5. Report transition metrics and parent-cluster bootstrap confidence intervals.
6. Re-analyze stored candidates offline without new model calls.
7. Keep human-label detector evaluation optional and held out.

Hardware / secrets: see `REQUIRED_FROM_USER.md` (48GB MLX Mac, API keys, HF).

---

## 5. Results

The completed Claude Haiku frozen pilot contains 1600 records (200 clean,
1400 attacked). After excluding always-pass `outcome_only` from max-proxy
aggregation, the meaningful-proxy blind-spot rate is 0.005 (7/1400), with
bootstrap 95% CI [0.0014, 0.0086]. This is a proxy-validity and robustness
result, not causal reward-hacking evidence.

| Pilot metric | Value |
|--------------|-------|
| Clean visual accuracy | 0.83 |
| Evidence-swap re-answer accuracy | 0.80 |
| Meaningful-proxy blind-spot rate | 0.005 |
| Outcome-only proxy-oracle gap | +0.354 |
| Keyword-match RHR | 0.0 |
| Research-eligible causal pressure result | pending |

The earlier 0.381 blind-spot figure was degenerate because `outcome_only=1.0`
for every non-empty response. Existing best-of-4 pressure records use
`echo-stub`; their diagnostic output is explicitly excluded from claims.

---

## 6. Limitations

- Phase A synthetic charts are simplified (bar/line/pie generators).
- ChartQA integration uses string gold; stubbed series weaken protocol science.
- Echo-stub audits are plumbing only — not research evidence.
- The completed real-model run is a frozen robustness/proxy-validity pilot,
  not causal reward-hacking evidence.
- Existing best-of-4 records use `echo-stub` and are plumbing only.
- The preregistered causal protocol is implemented but still needs a reviewed
  real-model run.
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
