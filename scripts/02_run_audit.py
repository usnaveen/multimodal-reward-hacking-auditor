#!/usr/bin/env python3
"""Run frozen VLM audit (MLX on Apple Silicon, Anthropic Claude, or API stub)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.pipeline.build_benchmark import load_config
from mrha.pipeline.run_frozen_audit import run_audit


def _make_client(backend: str, model_id: str):
    if backend == "mlx":
        from mrha.models.mlx_vlm import MLXVLMClient

        return MLXVLMClient(model_id=model_id)
    if backend == "api":
        from mrha.models.api_vlm import APIVLMClient

        return APIVLMClient(model_id=model_id)
    if backend == "anthropic":
        from mrha.models.anthropic_vlm import AnthropicVLMClient

        return AnthropicVLMClient(model_id=model_id)
    if backend == "echo":
        from mrha.pipeline.run_frozen_audit import EchoVLM

        return EchoVLM()
    raise SystemExit(f"Unknown backend: {backend}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "default.yaml")
    parser.add_argument("--backend", choices=["mlx", "api", "anthropic", "echo"], default=None)
    parser.add_argument("--model-id", type=str, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--results-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--judge-backend",
        choices=["mlx", "api", "anthropic", "echo", "same"],
        default=None,
        help="Enable weak_vlm_judge. 'same' reuses the audit model with the judge prompt.",
    )
    parser.add_argument("--judge-model-id", type=str, default=None)
    parser.add_argument(
        "--labels",
        type=Path,
        default=None,
        help="Optional detector labels JSONL for precision/recall.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        default=False,
        help="Ignore any existing progress and start from scratch.",
    )
    args = parser.parse_args()

    cfg = load_config(args.config) if args.config.exists() else {}
    backend = args.backend or cfg.get("model", {}).get("backend", "mlx")
    model_id = args.model_id or cfg.get("model", {}).get(
        "id", "mlx-community/Qwen2-VL-7B-Instruct-4bit"
    )
    manifest = args.manifest or Path(
        cfg.get("paths", {}).get("manifest", "data/benchmark/manifest.jsonl")
    )
    results = args.results_dir or Path(
        cfg.get("paths", {}).get("results", "results")
    )
    if not manifest.is_absolute():
        manifest = ROOT / manifest
    if not results.is_absolute():
        results = ROOT / results

    if not manifest.exists():
        raise SystemExit(
            f"Manifest not found: {manifest}\nRun: python scripts/01_build_benchmark.py"
        )

    client = _make_client(backend, model_id)

    judge_backend = args.judge_backend
    if judge_backend is None:
        jb = cfg.get("judge", {}) or {}
        judge_backend = jb.get("backend")

    judge_client = None
    use_same = False
    if judge_backend in ("same", True):
        use_same = True
    elif judge_backend in ("mlx", "api", "anthropic", "echo"):
        jid = args.judge_model_id or (cfg.get("judge") or {}).get("id") or model_id
        judge_client = _make_client(judge_backend, jid)

    labels = args.labels
    if labels is None:
        lp = cfg.get("paths", {}).get("labels")
        labels = ROOT / lp if lp else None

    records = run_audit(
        manifest,
        client,
        results_dir=results,
        limit=args.limit,
        judge_client=judge_client,
        use_weak_vlm_client=use_same,
        labels_path=labels,
        resume=not args.no_resume,
    )
    print(f"Audited {len(records)} items → {results}")


if __name__ == "__main__":
    main()
