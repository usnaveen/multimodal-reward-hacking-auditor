# Research Plan — Multimodal Reward-Hacking Auditor (MRHA)

## Problem

Vision-language models (VLMs) used as chart-VQA agents or as *judges* of other
agents can appear accurate under weak proxies (outcome-only success, keyword
overlap, lenient VLM judges) while failing under an **executable oracle** that
knows the true numeric content of a chart. That gap is a form of
**reward hacking / evaluation gaming**: the proxy reward rises while true task
success does not.

This repo is an **integration harness** (not a new foundation model) that makes
that gap measurable for chart-VQA under controlled attacks.

## Literature anchors (related, not claimed as this project's results)

| Anchor | Relevance |
|--------|-----------|
| **Yao26** — RHR / NRFR | Reward Hacking Rate and related non-robustness framing; we implement RHR when oracle labels exist; NRFR is a later-phase hook. |
| **Hwa25 FRAME** | Visual framing / judge-bait style perturbations; inspires `judge_bait` overlays. |
| **Kha26c FOCUS** | Focus / grounding pressure on multimodal models; motivates counterfactual evidence attacks. |
| **Zha26** | Misleading captions / CoT prefixes; inspires `wrong_caption`. |
| **Wu24** | Multimodal evaluation / chart understanding context for ChartQA-style tasks. |

Novelty claim for this harness: **executable chart oracles + attack families +
proxy suite + interpretable detector channels** in one runnable MLX-oriented
pipeline — not a claim that we reinvent RHR/FRAME/FOCUS.

## Threat model & oracle policy

1. **Executable truth only.** Synthetic charts store numeric JSON at generation
   time. The oracle checks answers against that JSON (exact category / numeric
   tolerance). A VLM is **never** used as ground truth.
2. **Proxies are adversarial surfaces.** `outcome_only`, `keyword_match`, and
   `weak_vlm_judge` may be gamed by overlays, captions, or rubber-stamping.
3. **Attacks preserve the question** (and usually the gold label) while changing
   evidence or text context — so proxy–oracle disagreement is informative.
4. **Frozen audit.** Phase A evaluates frozen checkpoints; no RL training loop.

## MVP (Phase A) — this repository

- Synthetic bar / line / pie charts with truth JSON
- Attacks: `evidence_swap`, `evidence_destroy`, `wrong_caption`, `judge_bait`
- Proxies: `outcome_only`, `keyword_match`, `weak_vlm_judge`
- Metrics: `blind_spot_rate`, `proxy_oracle_gap`, `RHR`, correlations; NRFR stub note
- MLX VLM client (Apple Silicon) + optional API stub
- Detector: counterfactual grounding + judge-audit channels
- Smoke test without GPU/MLX

## Later phases

| Phase | Scope |
|-------|-------|
| B | Larger N, more chart types, stratified questions, human spot-checks |
| C | Preference / pairwise labels → NRFR-style metrics |
| D | Train-time reward models; measure hacking under proxy optimization |
| E | Cross-model leaderboard; release frozen manifests + hash-locked images |

## Week plan (suggested)

| Day | Goal |
|-----|------|
| 1 | Clone, venv, smoke test, build N=20 benchmark on Mac |
| 2 | Install MLX + download 4-bit 7B; dry-run `echo` backend then MLX on 5 items |
| 3 | Full frozen audit on 48GB machine; write real `results/` |
| 4 | Metric tables, per-attack breakdowns, detector flag rates |
| 5 | Ablate proxies; document failure modes; draft resume bullets from **real** numbers |
| 6–7 | Write short tech note; open issues for Phase B |

## Non-goals (Phase A)

- Claiming SOTA ChartQA accuracy
- Fabricating result JSON
- Using a judge VLM as the oracle
- Training large models in this repo
