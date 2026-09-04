# Multimodal Reward-Hacking Auditor (MRHA)

**Phase A MVP** — a production-shaped research harness for auditing chart-VQA
agents and their *proxies* under controlled multimodal attacks.

Public repo: [github.com/usnaveen/multimodal-reward-hacking-auditor](https://github.com/usnaveen/multimodal-reward-hacking-auditor)

> **Oracle policy:** ground truth comes from **executable chart JSON** generated
> with the image. A VLM judge is a **proxy only**, never truth.

---

## 1. Problem statement & novelty

Chart-VQA agents (and VLM-as-judge pipelines) can look strong under weak
evaluation proxies — non-empty answers, keyword overlap with a reference, or a
lenient multimodal judge — while failing an **executable oracle** that knows the
true bar heights / series values. That **proxy–oracle gap** is the multimodal
analogue of reward hacking.

**What this project claims (novelty):** an *integration harness* that combines

1. synthetic charts with **executable oracles** (no VLM-as-GT),
2. attack families that break evidence or bait judges,
3. a proxy suite that mirrors common weak eval practices,
4. metrics aligned with recent reward-hacking measurement (RHR; NRFR reserved),
5. an interpretable detector (counterfactual grounding + judge-audit channels),
6. a **complete MLX runner** for local Apple Silicon VLMs,

…into one runnable package. We **do not** claim a new foundation model or
fabricated leaderboard numbers.

**Related work (anchors, not our results):** Yao26 (RHR/NRFR), Hwa25 FRAME
(judge-bait / framing), Kha26c FOCUS (grounding pressure), Zha26 (misleading
captions / CoT), Wu24 (multimodal / chart evaluation context). See `PLAN.md`.

---

## 2. What is implemented vs what you must run

| Component | Status |
|-----------|--------|
| Chart generation (bar/line/pie) + truth JSON | ✅ Implemented |
| Attacks: evidence_swap, evidence_destroy, wrong_caption, judge_bait | ✅ Implemented |
| Executable oracle + proxies | ✅ Implemented |
| Metrics writers (CSV/JSON) + example schema | ✅ Implemented (empty until you run) |
| Detector channels | ✅ Implemented |
| MLX VLM client | ✅ Code complete — **you run on Mac** |
| API VLM stub | ✅ Stub |
| Smoke test (no GPU) | ✅ Implemented |
| Real audit accuracies / RHR tables | ❌ **Not fabricated** — produce on your 48GB Mac |

`results/` ships with `.gitkeep` + `example_schema.json` only.

---

## 3. Threat model & oracle policy

- **Executable truth:** `*_truth.json` stores categories/values at generation.
- **Question fixed** under attacks; gold label stays tied to *clean* truth.
- **Proxies may be wrong on purpose** (easy to inflate under bait).
- **VLM judge ≠ oracle.** `weak_vlm_judge` calls the same client interface or a
  heuristic; scores are recorded as proxies for gap analysis.

---

## 4. Setup (any machine for smoke; Apple Silicon for MLX)

### 4.1 Core (Linux / Mac / CI — no MLX)

```bash
git clone https://github.com/usnaveen/multimodal-reward-hacking-auditor.git
cd multimodal-reward-hacking-auditor
python3.11 -m venv .venv   # 3.11+ required; 3.12/3.13 ok for non-MLX
source .venv/bin/activate
pip install -e ".[dev]"
# or: pip install -r requirements.txt && pip install -e .
```

### 4.2 Exact MLX setup on Apple Silicon (48GB)

Hardware note:

- **8GB M1:** insufficient for comfortable 7B VLM inference (even 4-bit).
- **48GB unified memory:** OK for 7B MLX 4-bit models (Qwen2-VL / Qwen2.5-VL).

```bash
# On the 48GB Mac — Python 3.11+ recommended for mlx-vlm
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,mlx]"
# Equivalent explicit pins if needed:
# pip install mlx mlx-vlm

# Download / cache a 4-bit instruct VLM (example)
python - <<'PY'
from mlx_vlm import load
model, processor = load("mlx-community/Qwen2-VL-7B-Instruct-4bit")
print("loaded", type(model))
PY
# Alternatives:
#   mlx-community/Qwen2.5-VL-7B-Instruct-4bit
```

If `import mlx` / `mlx_vlm` fails, you are not on Apple Silicon or Metal is
unavailable — use `--backend echo` only for plumbing tests, or `--backend api`
with `MRHA_API_KEY`.

---

## 5. Commands

```bash
# From repo root, venv active, PYTHONPATH via pip -e .

# 1) Build synthetic benchmark (N from configs/default.yaml)
python scripts/01_build_benchmark.py
# → data/benchmark/manifest.jsonl + clean/ + attacks/

# 2) Smoke test — no model needed (must pass on any laptop)
python scripts/04_smoke_test.py

# 3) Frozen audit on Mac (MLX)
python scripts/02_run_audit.py --backend mlx \
  --model-id mlx-community/Qwen2-VL-7B-Instruct-4bit
# Optional dry-run plumbing:
# python scripts/02_run_audit.py --backend echo --limit 5

# 4) Recompute / export metrics from real audit_records.jsonl
python scripts/03_compute_metrics.py
```

Unit tests:

```bash
pytest -q
```

---

## 6. Attack families & proxies

| Attack | Idea |
|--------|------|
| `evidence_swap` | Reverse series values; question+gold unchanged |
| `evidence_destroy` | Blur + occlude central plot region |
| `wrong_caption` | Misleading caption + CoT prefix (Zha26-style) |
| `judge_bait` | Brightness, padding, keyword overlays (FRAME-inspired) |

| Proxy | Idea |
|-------|------|
| `outcome_only` | Non-empty response |
| `keyword_match` | Token Jaccard vs gold (easy to bait) |
| `weak_vlm_judge` | Same VLM interface / heuristic — **not truth** |

| Metric | Idea |
|--------|------|
| `blind_spot_rate` | Attacked items where oracle fails but a proxy still ≥ 0.5 |
| `proxy_oracle_gap` | mean(proxy) − mean(oracle) |
| `RHR` | P(proxy pass ∧ oracle fail) / P(proxy pass) when labels exist |
| `NRFR` | Hook / note only in Phase A |

---

## 7. Layout

```
src/mrha/           # package
scripts/            # CLI entrypoints 01–04
configs/default.yaml
data/benchmark/     # generated (gitignored except .gitkeep)
results/            # audit outputs (gitignored except schema)
tests/
PLAN.md             # research plan & week schedule
```

---

## 8. Resume bullet draft (placeholder)

> *Built Multimodal Reward-Hacking Auditor (MRHA): executable-oracle chart-VQA
> harness with evidence/judge attacks, proxy–oracle metrics (blind-spot rate,
> RHR), and MLX runner for local 7B VLMs on Apple Silicon. **[Fill in after
> 48GB audit: N items, model id, blind_spot_rate, RHR — do not invent].***

---

## 9. License

MIT — see `LICENSE`.

## 10. Citation

If you use this harness, cite this repository and the related anchors above
separately. Do not attribute Yao26/Hwa25/etc. results to this MVP.
