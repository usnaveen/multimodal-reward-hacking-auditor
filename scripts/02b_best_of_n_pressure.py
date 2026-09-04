#!/usr/bin/env python3
"""Best-of-n proxy pressure scaffolding — enables NRFR without full RL.

For each manifest item:
  1. Sample k responses (or echo-stub variants)
  2. Pick the response that maximizes a proxy
  3. Score the picked response with the executable oracle
  4. Record baseline_oracle_correct + proxy_improved for NRFR

Does NOT invent research claims — scaffolding only.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.metrics.compute import compute_all, nrfr, write_metrics
from mrha.models.base import build_prompt
from mrha.oracles.chart_oracle import ChartOracle
from mrha.pipeline.build_benchmark import load_config, read_manifest
from mrha.proxies import gold_overlap_proxy, keyword_match, outcome_only
from mrha.schema import AttackFamily, AuditRecord


def _proxy_score(name: str, response: str, item) -> float:
    if name == "outcome_only":
        return outcome_only.score(response, item)
    if name == "keyword_match":
        return keyword_match.score(response, item)
    if name == "gold_overlap":
        return gold_overlap_proxy.score(response, item)
    raise SystemExit(f"Unknown proxy: {name}")


def _sample_responses(client, item, prompt: str, k: int, rng: random.Random) -> list[str]:
    """Sample k responses. Echo stub: synthesize variants around gold/noise."""
    if getattr(client, "model_id", "") == "echo-stub" or client.__class__.__name__ == "EchoVLM":
        base = client.answer(item.image_path, prompt)
        variants = [base]
        # Pressure decoys that may inflate proxies without being correct
        decoys = [
            f"Answer: {item.answer_gold}",
            "Answer: unknown",
            f"I think it might be {item.answer_gold} but unsure.",
            "Answer: placating filler text with keywords",
        ]
        while len(variants) < k:
            variants.append(decoys[rng.randrange(len(decoys))])
        return variants[:k]
    outs = []
    for _ in range(k):
        outs.append(client.answer(item.image_path, prompt))
    return outs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "default.yaml")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--results-dir", type=Path, default=None)
    parser.add_argument("--backend", choices=["mlx", "api", "echo"], default="echo")
    parser.add_argument("--model-id", type=str, default="echo-stub")
    parser.add_argument("--k", type=int, default=4, help="best-of-n sample size")
    parser.add_argument("--proxy", type=str, default="keyword_match")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    cfg = load_config(args.config) if args.config.exists() else {}
    manifest = args.manifest or Path(
        cfg.get("paths", {}).get("manifest", "data/benchmark/manifest.jsonl")
    )
    results = args.results_dir or Path(
        cfg.get("paths", {}).get("results", "results")
    ) / "best_of_n"
    if not manifest.is_absolute():
        manifest = ROOT / manifest
    if not results.is_absolute():
        results = ROOT / results
    results.mkdir(parents=True, exist_ok=True)

    if not manifest.exists():
        raise SystemExit(f"Manifest not found: {manifest}")

    if args.backend == "echo":
        from mrha.pipeline.run_frozen_audit import EchoVLM

        client = EchoVLM()
    elif args.backend == "mlx":
        from mrha.models.mlx_vlm import MLXVLMClient

        client = MLXVLMClient(model_id=args.model_id)
    else:
        from mrha.models.api_vlm import APIVLMClient

        client = APIVLMClient(model_id=args.model_id)

    items = read_manifest(manifest)
    if args.limit is not None:
        items = items[: args.limit]

    oracle = ChartOracle()
    rng = random.Random(args.seed)
    records: list[AuditRecord] = []

    for item in items:
        prompt = build_prompt(item.question, item.caption, item.prompt_prefix)
        # Baseline: first / greedy sample
        baseline_resp = client.answer(item.image_path, prompt)
        baseline_ok = oracle.score(baseline_resp, item)
        baseline_proxy = _proxy_score(args.proxy, baseline_resp, item)

        candidates = _sample_responses(client, item, prompt, args.k, rng)
        scored = [(_proxy_score(args.proxy, r, item), r) for r in candidates]
        scored.sort(key=lambda t: t[0], reverse=True)
        best_proxy, best_resp = scored[0]
        best_ok = oracle.score(best_resp, item)
        proxy_improved = best_proxy > baseline_proxy + 1e-9

        records.append(
            AuditRecord(
                item_id=item.item_id,
                attack=item.attack,
                protocol=item.protocol,
                parent_id=item.parent_id,
                model_id=getattr(client, "model_id", args.model_id),
                response=best_resp,
                oracle_correct=best_ok,
                proxy_scores={args.proxy: best_proxy, "baseline_proxy": baseline_proxy},
                metadata={
                    "baseline_oracle_correct": baseline_ok,
                    "proxy_improved": proxy_improved,
                    "k": args.k,
                    "pressure": "best_of_n",
                    "baseline_response": baseline_resp,
                    "oracle_mode": item.metadata.get("oracle_mode"),
                },
            )
        )

    out_jsonl = results / "pressure_records.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(r.model_dump_json() + "\n")

    summary = compute_all(records, rhr_proxy=args.proxy)
    nval = nrfr(records)
    summary.nrfr = nval
    if nval is None:
        summary.notes.append("NRFR still undefined after pressure run (no proxy_improved).")
    else:
        summary.notes.append(f"NRFR from best-of-{args.k} pressure: {nval}")
    write_metrics(summary, results, records=records)
    print(json.dumps({"n": len(records), "nrfr": nval, "out": str(out_jsonl)}, indent=2))


if __name__ == "__main__":
    main()
