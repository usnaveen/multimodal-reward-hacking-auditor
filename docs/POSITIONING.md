# Positioning — claim vs non-claim (one-pager)

## One-sentence claim

**MRHA is an executable-oracle framework for testing whether multimodal proxy
optimization tracks real chart correctness. It combines a completed
robustness/metric-validity pilot with a preregistered causal best-of-k
selection experiment; it is not a new VLM, and frozen perturbation results are
not presented as reward-hacking proof.**

## We claim

| Claim | Evidence in repo |
|-------|------------------|
| Executable oracle on synthetic charts | `ChartTruth` + `ChartOracle` |
| Dual **invariance** / **re_answer** protocols | Manifest + attacks metadata |
| Attack families incl. `judge_bait` (no painted gold) + `nuisance` | `src/mrha/attacks/` |
| Honest proxies; `weak_vlm_judge` requires a real judge backend | `02_run_audit.py` |
| Causal best-of-k selection under proxy pressure | Stored candidate sets + random/proxy/oracle controls; real-model run pending |
| Cross-run attack × proxy tables | `scripts/08_cross_table.py` |
| Causal proxy-pressure experiment with stored candidates | `scripts/11_run_causal_pressure.py`, `src/mrha/pressure/` |
| Paired regression/rescue metrics + parent-cluster bootstrap | `src/mrha/pressure/analysis.py` |
| Preregistered hypothesis and eligibility rules | `docs/CAUSAL_PRESSURE_PROTOCOL.md` |
| Results policy: never invent metrics or promote stub runs | `RESULTS.md`, `results/README.md` |

## We do **not** claim

| Non-claim | Why |
|-----------|-----|
| That the completed frozen audit proves reward hacking | It is a robustness/proxy-validity pilot; causal pressure is still pending |
| That echo-stub NRFR is model evidence | Stub pressure output is explicitly non-research |
| Reproduced Yao26 full RL / their reported RHR–NRFR curves | We implement best-of-k causal selection, not RL training |
| Identity with FRAME or FOCUS benchmarks | Inspired attack/judge philosophy; different artifact |
| SOTA ChartQA accuracy | We audit gaps; we are not a QA system paper |
| That echo-stub or missing-run JSON is a research result | Forbidden |
| That ChartQA string labels are executable geometric oracles | Documented stub-truth limitation |
| Production deployment of a detector | Labels + hold-out tooling only in Phase A |

## How this differs (sharp)

| Work | Their center of gravity | MRHA difference |
|------|-------------------------|-----------------|
| **Yao26** | RH under RL / reward design; RHR & NRFR | **Executable-oracle causal selection harness** without claiming RL reproduction |
| **FRAME** | Fooling LVLM *judges* with visual framing | We use FRAME-like baits inside an **agent audit** with executable oracles + nuisance FP control |
| **FOCUS** | Evaluator VLM blind spots / perturbation matrix | We fix **dual gold protocols** and proxy honesty; not a full FOCUS reproduction |

## Interview sound-bite

> “The first frozen audit became a metric-validity pilot: it caught a
> degenerate proxy aggregation rather than manufacturing a reward-hacking
> claim. MRHA now preregisters the causal question—whether proxy-max selection
> raises proxy reward while visual correctness regresses—and compares it with
> random and oracle controls over identical stored candidates.”

## Links

- `README.md` — differentiation section
- `docs/TECH_REPORT.md` — longer writeup
- `INTERVIEW_PREP.md` — talking points
- `IMPROVEMENT_LOG.md` — Round 1 fixes
- `RESULTS.md` — placeholders only until real runs
