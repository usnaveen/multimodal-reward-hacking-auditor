# Positioning — claim vs non-claim (one-pager)

## One-sentence claim

**MRHA is an open evaluation harness that measures proxy–oracle divergence for
chart-VQA agents under dual evidence protocols and controlled attacks
(including judge-bait and nuisance FP controls), with RHR and best-of-n NRFR
scaffolding — not a new VLM and not a fabricated leaderboard.**

## We claim

| Claim | Evidence in repo |
|-------|------------------|
| Executable oracle on synthetic charts | `ChartTruth` + `ChartOracle` |
| Dual **invariance** / **re_answer** protocols | Manifest + attacks metadata |
| Attack families incl. `judge_bait` (no painted gold) + `nuisance` | `src/mrha/attacks/` |
| Honest proxies; `weak_vlm_judge` requires a real judge backend | `02_run_audit.py` |
| Metric definitions for blind-spot, RHR, NRFR (pressure fields) | `metrics/compute.py`, `02b`, `07` |
| Cross-run attack × proxy tables | `scripts/08_cross_table.py` |
| Results policy: never invent metrics | `RESULTS.md`, `results/README.md` |

## We do **not** claim

| Non-claim | Why |
|-----------|-----|
| Reproduced Yao26 full RL / their reported RHR–NRFR curves | We scaffold best-of-n pressure only |
| Identity with FRAME or FOCUS benchmarks | Inspired attack/judge philosophy; different artifact |
| SOTA ChartQA accuracy | We audit gaps; we are not a QA system paper |
| That echo-stub or missing-run JSON is a research result | Forbidden |
| That ChartQA string labels are executable geometric oracles | Documented stub-truth limitation |
| Production deployment of a detector | Labels + hold-out tooling only in Phase A |

## How this differs (sharp)

| Work | Their center of gravity | MRHA difference |
|------|-------------------------|-----------------|
| **Yao26** | RH under RL / reward design; RHR & NRFR | **Harness + protocols + attacks** with NRFR via best-of-n *without* claiming RL runs |
| **FRAME** | Fooling LVLM *judges* with visual framing | We use FRAME-like baits inside an **agent audit** with executable oracles + nuisance FP control |
| **FOCUS** | Evaluator VLM blind spots / perturbation matrix | We fix **dual gold protocols** and proxy honesty; not a full FOCUS reproduction |

## Interview sound-bite

> “Yao26 gives the metric language; FRAME/FOCUS give judge-failure intuition.
> MRHA is the **measurement system** that ties executable chart oracles, dual
> protocols, and proxy pressure together so you can see reward hacking
> without pretending you’ve shipped their full training stacks.”

## Links

- `README.md` — differentiation section
- `docs/TECH_REPORT.md` — longer writeup
- `INTERVIEW_PREP.md` — talking points
- `IMPROVEMENT_LOG.md` — Round 1 fixes
- `RESULTS.md` — placeholders only until real runs
