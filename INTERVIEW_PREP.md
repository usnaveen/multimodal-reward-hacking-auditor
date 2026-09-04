# Interview Prep — Multimodal Reward-Hacking Auditor (MRHA)

Use this doc to (1) learn concepts in the right order, (2) read papers that
matter for *this* project, and (3) answer research / applied genAI interviewers
without hand-waving.

Related: `PLAN.md`, `DATASETS.md`, `REQUIRED_FROM_USER.md`, `README.md`.

---

## 0. How interviewers will hear this project

**Strong framing (use this):**
> “I built an open evaluation harness that measures **proxy–true divergence** for
> chart-VQA VLMs: when outcome-only / keyword / VLM-judge scores look good while
> an **executable oracle** says the answer is wrong — under controlled visual and
> judge-bait attacks, with separate **invariance** vs **re-answer** protocols.”

**Weak framing (avoid):**
> “I built a LangGraph agent that does chart QA with attacks.”

You are selling **measurement science + failure modes of multimodal agents**,
aligned with your Walmart multimodal-drift work — not another multi-agent demo.

---

## 1. Concepts to learn (strict order)

Do not skip ahead to GRPO papers before you can define a proxy vs an oracle in
one sentence.

### Tier 0 — Foundations (1–2 days)
| # | Concept | You must be able to say |
|---|---------|-------------------------|
| 0.1 | Supervised loss vs **reward / score** | Optimization target ≠ task success |
| 0.2 | **Proxy vs true objective** | Spec gaming exists whenever the score is incomplete |
| 0.3 | Classification metrics vs **oracle / executable checks** | Why substring match ≠ understanding |
| 0.4 | VQA / ChartQA task setup | Image + question → short answer; what “relaxed accuracy” means |

### Tier 1 — Multimodal grounding (2–3 days)
| # | Concept | Why it matters for MRHA |
|---|---------|-------------------------|
| 1.1 | Vision–language models (VLM) at a high level | Encoder + LLM; image tokens in context |
| 1.2 | **Visual grounding** vs language priors | Model can answer from text priors without looking |
| 1.3 | Chart understanding (axes, marks, legend) | Your synthetic + ChartQA domain |
| 1.4 | Counterfactual / interventional tests | Change evidence, hold question fixed → diagnose shortcuts |
| 1.5 | **Invariance protocol** vs **re-answer protocol** | Core design in *your* repo — rehearse both |

### Tier 2 — Evaluation & judges (2–3 days)
| # | Concept | Why |
|---|---------|-----|
| 2.1 | LLM-as-a-judge biases | Verbosity, position, sycophancy, format sensitivity |
| 2.2 | Single-score vs pairwise judges | Pairwise often stronger; still fails on fine-grained errors |
| 2.3 | Evaluator stress tests / blind spots | Proxy score unchanged after valid degradation |
| 2.4 | Your proxies: outcome-only, keyword, gold-overlap, weak VLM judge | Know failure mode of each |
| 2.5 | Why **VLM must never be ground truth** for your oracle | Circular evaluation |

### Tier 3 — Reward hacking & agentic failure (3–4 days)
| # | Concept | Why |
|---|---------|-----|
| 3.1 | Specification gaming / reward hacking (classic RL) | Historical root |
| 3.2 | RLHF / preference optimization (intuition only) | Proxies in alignment |
| 3.3 | **RHR** (Reward Hacking Rate) | P(hack \| proxy pass) — implement & explain |
| 3.4 | **NRFR** (Newly Rewarded Failure Rate) | Failures that appear when proxy improves vs baseline |
| 3.5 | Outcome-only vs evidence-aware / process rewards | Yao26 ladder |
| 3.6 | Best-of-n / overoptimization curves | Pressure without full RL (your `02b` script) |
| 3.7 | Agentic tool use + verifier gaming (high level) | Path to Phase B / Walmart story |

### Tier 4 — Enough ML to defend “research-y” choices (ongoing)
| # | Concept | Depth needed |
|---|---------|--------------|
| 4.1 | Bootstrap confidence intervals | You ship CIs — know what 95% CI means |
| 4.2 | Train/test / hold-out for detector labels | Don’t tune and report on same flags |
| 4.3 | GRPO / RLVR at cocktail-party level | Not implement; know *why* people RL VLMs |
| 4.4 | MLX / on-device inference tradeoffs | Why 7B-4bit on 48GB vs API judges |

---

## 2. Papers & resources (read in this order)

Skim abstracts of later papers early; **deep-read** in order. Prefer primary PDFs
over blog summaries for interview claims.

### Wave A — Must deep-read for *this* repo (before any onsite)
| Order | Paper / resource | Focus while reading | Tie to MRHA |
|-------|------------------|---------------------|-------------|
| A1 | Classic surveys / notes on **specification gaming** (e.g. DeepMind “Specification gaming” examples; Amodei et al. Concrete Problems in AI Safety — reward hacking section) | Taxonomy of gaming | Vocabulary |
| A2 | **LLM-as-a-judge** bias papers (e.g. Zheng et al. MT-Bench / JudgeBench lineage; position & verbosity bias follow-ups) | Why judges are proxies | Your judge_bait + weak_vlm_judge |
| A3 | **Yao et al., Multimodal Reward Hacking in Reinforcement Learning (2026)** | RHR, NRFR, outcome-only vs vision-aware rewards, chart/safety VQA | **Primary anchor** — cite carefully; don’t claim you reproduced full RL |
| A4 | **Hwang/Lee et al., FRAME — Fooling LVLM Judges (EMNLP 2025)** | Visual bias families for judges | Your judge_bait design |
| A5 | ChartQA paper (Masry et al.) + dataset card | Task, relaxed accuracy, human vs aug splits | Your ChartQA loader |

### Wave B — Grounding & shortcuts (same week as A3–A5)
| Order | Paper | Focus | Tie |
|-------|-------|-------|-----|
| B1 | Work on **visual shortcuts / ignoring the image** in VQA / video-QA (e.g. Xu26-style “stop watching” / VHS if citing that line) | Counterfactual evidence destruction | evidence_destroy, invariance |
| B2 | **Zha et al. on RL-finetuned VLM robustness / CoT consistency (2026)** | Wrong captions, wrong CoT | wrong_caption attack |
| B3 | **Khan et al. FOCUS — evaluator VLM blind spots (2026)** | Perturbation matrix, pairwise vs single-score | Stress-test philosophy |
| B4 | Chartographer (2026) — counterfactual chart families | Executable recomputed answers | Ideal Phase-B data direction |

### Wave C — Agents, tools, industry story (after Wave A)
| Order | Paper | Focus | Tie |
|-------|-------|-------|-----|
| C1 | **Wu et al. — Dissecting Adversarial Robustness of Multimodal LM Agents (ICLR 2024)** | Illusioning, goal misdirection, execution oracles | Future tool track; ASR |
| C2 | Surveys on reward hacking in **agentic** LLMs (2026 survey line) | Feature / evaluator / environment levels | How you place MRHA in taxonomy |
| C3 | Your Walmart multimodal-drift / MCP narrative (internal notes + one-pager) | Production reliability | “Why I care” story |

### Wave D — Optional depth (if targeting RL / alignment roles)
| Order | Topic | Notes |
|-------|-------|-------|
| D1 | RLHF (Christiano / InstructGPT intuition) | Don’t memorize algorithms |
| D2 | RLVR / process reward models (Lightman et al. PRM; SWE-agent PRM papers) | Process vs outcome |
| D3 | GRPO / DAPO blog+paper skim | Only if interviewer goes deep on MLLM RL |

**Reading method for each Wave A/B paper:**
1. Problem statement in your words (3 sentences)
2. Their **metric definitions** (copy into a notebook)
3. One figure you can redraw on a whiteboard
4. One limitation + how MRHA relates (extension, not clone)

---

## 3. Whiteboard story (90 seconds)

1. **Setup:** Chart-VQA agent scored by weak proxies.
2. **Failure:** Proxy↑, oracle↓ under evidence swap / destroy / judge bait.
3. **Protocols:** Invariance detects shortcuts; re-answer detects grounded updates.
4. **Metrics:** Blind-spot rate, RHR; NRFR needs pressure (best-of-n / RL).
5. **Oracle policy:** Executable synthetic truth; VLM judge ≠ GT.
6. **Link:** Same family as multimodal drift in production pipelines.

---

## 4. Likely interview questions (practice out loud)

### Conceptual
1. Define reward hacking without saying “the model cheats.”
2. Why can’t you use GPT-4V as the oracle for a GPT-4V agent study?
3. Difference between invariance and re-answer — when is each the right test?
4. Outcome-only reward vs keyword evidence vs VLM-as-judge — failure modes?
5. What does RHR measure that raw accuracy doesn’t?

### Project-specific (they *will* ask)
6. What’s still toy about your setup, and what did v0.2 fix?
7. Show me an attack that would inflate keyword match but not a careful oracle.
8. How do you stop the detector from overfitting to your attack templates?
9. Why nuisance attacks?
10. You haven’t finished a full GRPO run — why is best-of-n still scientifically useful?

### Adversarial / hiring filter
11. Isn’t this just “robustness eval” rebranded?
12. How is this different from FRAME / FOCUS / Yao26?
13. Where are your **numbers**? (Answer honestly: pending 48GB run; show harness + smoke.)
14. Why charts instead of DocVQA first?
15. How would you productionize this next to an MCP tool agent?

---

## 5. Improvements that raise hire probability (priority)

Interviewers hire on **signal density**. Ranked:

| Priority | Improvement | Why it converts interviews |
|----------|-------------|----------------------------|
| P0 | Real frozen-audit tables on ≥1 open VLM + optional API judge | Without numbers you’re a design doc |
| P0 | One page “Results” in README with CIs + per-attack plot | Artifact they can skim in 60s |
| P1 | Best-of-n NRFR curve (even k=4–8) | Proves you understand *optimization pressure* |
| P1 | 30–50 human-validated attack pairs + detector P/R hold-out | Shows eval hygiene |
| P2 | Mixed synthetic + ChartQA transfer table | Realism without abandoning oracles |
| P2 | Short tech report (4–6 pp) citing Wave A papers correctly | Research-role signal |
| P3 | Chartographer or ReachQA integration | Differentiates from “matplotlib bars” |
| P3 | Tiny ablation: prompt “Answer:” vs free-form | Shows experimental taste |
| Avoid | Another LangGraph wrapper on top | Dilutes the story |

---

## 6. Honest limits to state in interviews

- Phase A is a **harness + frozen / best-of-n pressure**, not a claim you trained SOTA MLLM-RL.
- Novelty is **integration + executable oracles + dual protocols + open detector hooks**, not inventing RHR.
- Connected Mac for day-to-day may be 8GB; heavy runs need 48GB / API — say that if asked about compute.
- ChartQA string gold ≠ full executable series — you prefer synthetic for protocol science.

Honesty + clear next experiment > overclaiming.

---

## 7. Two-week study sprint (suggested)

| Day | Focus |
|-----|--------|
| 1–2 | Tier 0–1 concepts; ChartQA paper; sketch dual protocols from memory |
| 3–4 | Wave A2–A4 deep-read; write metric cheat-sheet (RHR/NRFR/blind-spot) |
| 5 | Run smoke + build N=200; start MLX audit if hardware ready |
| 6–7 | Wave B papers; map each attack in repo → paper section |
| 8 | Best-of-n pressure; draft Results section |
| 9 | Practice answers to §4 questions into a voice memo |
| 10 | Mock interview (use this doc’s interviewer stance) |
| 11–12 | Tech-report outline + resume bullets from **real** numbers only |
| 13–14 | Buffer: ChartQA mixed run or human labels |

---

## 8. Resume bullet templates (fill after real runs)

> Built **MRHA**, an open chart-VQA reward-hacking harness with executable oracles, dual invariance/re-answer protocols, and judge/evidence attacks; measured proxy–oracle divergence (blind-spot / RHR [/ NRFR]) on **[MODEL]** (N=**[N]**).

> Showed **[proxy]** remains high under **[attack]** while oracle accuracy drops **[Δ]**; released stress suite + audit pipeline (MLX).

Never invent the bracketed fields.
