# Datasets for MRHA Phase A / B

Synthetic charts remain the **default** Phase-A source (executable oracles).
External datasets extend coverage; each has different oracle strength and
license constraints.

## Synthetic (default)

| | |
|--|--|
| **Module** | `src/mrha/datasets/synthetic.py` |
| **Default N** | 200 (`configs/default.yaml`) |
| **Oracle** | Full executable JSON (categories + values) at generation |
| **Use** | Dual protocols, all attacks, detector FP control (`nuisance`) |
| **License** | Generated in-repo (MIT harness); no third-party image license |

```bash
python scripts/01_build_benchmark.py --source synthetic --n-items 200
```

## ChartQA (`ahmed-masry/ChartQA`)

| | |
|--|--|
| **Module** | `src/mrha/datasets/chartqa.py` |
| **HF** | `ahmed-masry/ChartQA` (test / human-oriented subset) |
| **What it gives** | Real chart images + human/model questions and answers |
| **Oracle strength** | **String gold** from HF labels; structured series often **stubbed** |
| **Use** | Realism / transfer checks; prefer synthetic for protocol science |
| **License** | Follow ChartQA / source chart licenses; check HF card before release |
| **Prep** | `pip install 'mrha[datasets]'` then `python scripts/05_prepare_datasets.py --source chartqa --limit 200` |

Offline: loader raises a clear error → use `--source synthetic`.
Tiny mixed smoke: `configs/chartqa_smoke.yaml` (see `docs/CHARTQA_FIXTURE_NOTE.md`).

```bash
python scripts/01_build_benchmark.py --source chartqa --n-items 50
python scripts/01_build_benchmark.py --source mixed --n-items 200
```

## Chartographer

| | |
|--|--|
| **URL** | https://github.com/compling-wat/Chartographer |
| **What it gives** | Chart understanding / grounding-oriented resources from CompLing @ Waterloo |
| **Oracle strength** | Depends on release artifacts — often richer structure than plain VQA string labels |
| **Use (planned)** | Phase B grounding pressure; align with counterfactual evidence attacks |
| **License** | See upstream repo LICENSE before bundling images/annotations |
| **Integration** | Not auto-downloaded in 0.2.0 — document path + adapter later |

## ReachQA

| | |
|--|--|
| **What it gives** | Reasoning-oriented chart/document QA (reach / multi-hop style questions) |
| **Oracle strength** | Answer strings; reasoning traces if released |
| **Use (planned)** | Stress wrong_caption / CoT bait under longer reasoning |
| **License** | Check the authors' release terms / HF card |
| **Integration** | Phase B+ loader TBD |

## DocVQA / DAM-QA

| | |
|--|--|
| **What they give** | Document VQA (DocVQA) and related document/diagram QA (DAM-QA family) |
| **Oracle strength** | Typically span / string answers; layout-sensitive |
| **Use (planned)** | Generalize attacks beyond pure charts (occlusion, caption bait on docs) |
| **License** | DocVQA has its own terms; DAM-QA — follow paper/repo |
| **Integration** | Out of Phase-A scope; keep synthetic+ChartQA first |

## How we will use them

1. **Protocol science & RHR/blind-spot** → synthetic (executable oracle).
2. **External validity** → ChartQA subset with honest stub-truth notes.
3. **Grounding / reasoning stress** → Chartographer, ReachQA (Phase B).
4. **Modality transfer** → DocVQA/DAM-QA (Phase C+).

Always record `metadata.source` on manifest items. Never claim ChartQA string
labels are executable geometric oracles.

## Detector labels hold-out

Human labels in `data/labels/detector_labels.jsonl` are **not** a dataset of
charts — they are detector evaluation labels. Keep a hold-out for reported
precision/recall (see `REQUIRED_FROM_USER.md`).
