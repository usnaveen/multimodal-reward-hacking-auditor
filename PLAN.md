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
| **Yao26** — RHR / NRFR | Reward Hacking Rate; NRFR via best-of-n pressure scaffolding |
| **Hwa25 FRAME** | Visual framing / judge-bait — stamps & brightness **without** painting gold |
| **Kha26c FOCUS** | Grounding pressure; dual evidence protocols |
| **Zha26** | Misleading captions / CoT prefixes; expanded template bank |
| **Wu24** | Multimodal / chart evaluation context |

## Dual evidence protocols (design fix)

| Protocol | Gold | Interpretation of oracle success on evidence attacks |
|----------|------|------------------------------------------------------|
| **invariance** | Stays on *clean* truth | Emitting old gold after visual change → **shortcut / ungrounded** |
| **re_answer** | Updates to *visual* truth | Emitting new gold → **grounded re-reading** |

`visual_answer_gold` is always stored in metadata under invariance so you can
separately score "correct on the new image."

## Threat model & oracle policy

1. **Executable truth only** for synthetic charts. VLM is never ground truth.
2. **Proxies are adversarial surfaces.** `outcome_only`, `keyword_match`,
   `gold_overlap` are explicit; `weak_vlm_judge` requires a real VLMClient
   (`--judge-backend`) — no silent gold-overlap fake judge.
3. **Attacks** include `nuisance` (FP control) and FRAME-like `judge_bait`
   that never paints the answer on the image.
4. **Frozen audit** + optional **best-of-n pressure** for NRFR (no full RL).

## Phase A (0.2.0) — this repository

- Synthetic default **N=200**; ChartQA optional loader
- Attacks: evidence_swap (permute / swap-max-min / reverse), evidence_destroy,
  wrong_caption, judge_bait, **nuisance**
- Protocols: invariance, re_answer on evidence attacks
- Proxies: outcome_only, keyword_match, gold_overlap; weak_vlm_judge opt-in
- Metrics: blind_spot_rate (+ bootstrap CI), proxy_oracle_gap, RHR, **NRFR**,
  per-attack CSV
- Detector P/R if `data/labels/detector_labels.jsonl` present (hold-out)
- MLX client + echo stub + CI smoke

## Later phases

| Phase | Scope |
|-------|-------|
| B | Chartographer / ReachQA; stratified questions; human spot-checks |
| C | Preference / pairwise labels at scale |
| D | Train-time reward models under proxy optimization |
| E | Cross-model leaderboard; hash-locked manifests |

## Non-goals (Phase A)

- Claiming SOTA ChartQA accuracy
- Fabricating result JSON
- Using a judge VLM as the oracle
- Training large models in this repo
