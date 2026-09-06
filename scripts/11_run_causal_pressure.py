#!/usr/bin/env python3
"""Run a paired, causal best-of-k proxy-selection experiment.

The runner stores every candidate and evaluates random, proxy, and oracle
selectors over the exact same candidate set. Evidence-attack invariance rows
are excluded: their old-gold target measures retention, not visual correctness.

This script may make paid API calls. Use ``--backend echo`` for plumbing, then
explicitly choose a real backend for research runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mrha.models.base import VLMClient, build_prompt
from mrha.oracles.chart_oracle import ChartOracle
from mrha.pipeline.build_benchmark import read_manifest
from mrha.pressure.analysis import select_candidate, summarize_pressure
from mrha.pressure.eligibility import assess_research_eligibility
from mrha.pressure.schema import CandidateEvaluation, PressureRecord
from mrha.proxies import gold_overlap_proxy, keyword_match, outcome_only, weak_vlm_judge
from mrha.schema import AttackFamily, AttackProtocol, ManifestItem

EVIDENCE_ATTACKS = {AttackFamily.EVIDENCE_SWAP, AttackFamily.EVIDENCE_DESTROY}
PROXY_NAMES = ("keyword_match", "gold_overlap", "outcome_only")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _combined_sha256(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted({p.resolve() for p in paths}, key=str):
        identifier = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        digest.update(str(identifier).encode("utf-8"))
        digest.update(bytes.fromhex(_sha256(path)))
    return digest.hexdigest()


def _resolve_item_paths(items: list[ManifestItem]) -> None:
    """Make manifest artifact paths independent of the caller's working directory."""
    for item in items:
        image = Path(item.image_path)
        truth = Path(item.truth_path)
        item.image_path = str(image if image.is_absolute() else (ROOT / image).resolve())
        item.truth_path = str(truth if truth.is_absolute() else (ROOT / truth).resolve())


def _artifact_sha256(items: list[ManifestItem]) -> str:
    paths = [Path(item.image_path) for item in items]
    paths.extend(Path(item.truth_path) for item in items)
    return _combined_sha256(paths)


def _backend_module(backend: str) -> Path:
    modules = {
        "anthropic": ROOT / "src/mrha/models/anthropic_vlm.py",
        "api": ROOT / "src/mrha/models/api_vlm.py",
        "mlx": ROOT / "src/mrha/models/mlx_vlm.py",
        "echo": ROOT / "src/mrha/pipeline/run_frozen_audit.py",
    }
    return modules[backend]


def _provider_endpoint(backend: str) -> str | None:
    if backend == "anthropic":
        return os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    if backend == "api":
        return "https://api.openai.com/v1"
    return None


def _package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in ("pydantic", "Pillow", "mlx-vlm", "mlx"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = None
    return versions


def _config_hash(config: dict[str, Any]) -> str:
    raw = json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _build_client(
    backend: str,
    model_id: str,
    *,
    temperature: float,
    max_tokens: int,
) -> VLMClient:
    if backend == "echo":
        from mrha.pipeline.run_frozen_audit import EchoVLM

        return EchoVLM()
    if backend == "anthropic":
        from mrha.models.anthropic_vlm import AnthropicVLMClient

        return AnthropicVLMClient(
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if backend == "mlx":
        from mrha.models.mlx_vlm import MLXVLMClient

        return MLXVLMClient(
            model_id=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    from mrha.models.api_vlm import APIVLMClient

    return APIVLMClient(
        model_id=model_id,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _answer(
    client: VLMClient,
    image_path: str,
    prompt: str,
    *,
    temperature: float | None = None,
) -> str:
    """Answer with a temporary temperature when the backend exposes one."""
    if temperature is None or not hasattr(client, "temperature"):
        return client.answer(image_path, prompt)
    previous = client.temperature
    try:
        client.temperature = temperature
        return client.answer(image_path, prompt)
    finally:
        client.temperature = previous


def _score_builtin(name: str, response: str, item: ManifestItem) -> float:
    if name == "keyword_match":
        return keyword_match.score(response, item)
    if name == "gold_overlap":
        return gold_overlap_proxy.score(response, item)
    if name == "outcome_only":
        return outcome_only.score(response, item)
    raise ValueError(f"Unknown proxy: {name}")


def _evaluate(
    response: str,
    item: ManifestItem,
    oracle: ChartOracle,
    proxies: list[str],
    judge_client: VLMClient | None,
) -> CandidateEvaluation:
    scores = {name: _score_builtin(name, response, item) for name in proxies}
    if judge_client is not None:
        scores["vlm_judge"] = weak_vlm_judge.score(
            response,
            item,
            client=judge_client,
            mode="single_score",
        )
    return CandidateEvaluation(
        response=response,
        visual_correct=oracle.score(response, item),
        proxy_scores=scores,
    )


def _eligible_items(
    items: list[ManifestItem], parent_limit: int | None
) -> list[ManifestItem]:
    eligible = [
        item
        for item in items
        if not (
            item.attack in EVIDENCE_ATTACKS
            and item.protocol == AttackProtocol.INVARIANCE
        )
    ]
    if parent_limit is None:
        return eligible
    parent_ids: list[str] = []
    for item in eligible:
        parent = item.parent_id or item.item_id
        if parent not in parent_ids:
            parent_ids.append(parent)
    keep = set(parent_ids[:parent_limit])
    return [item for item in eligible if (item.parent_id or item.item_id) in keep]


def _load_records(path: Path) -> list[PressureRecord]:
    if not path.is_file():
        return []
    return [
        PressureRecord.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "benchmark" / "manifest.jsonl",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT / "results" / "causal_pressure",
    )
    parser.add_argument(
        "--backend", choices=["anthropic", "api", "mlx", "echo"], default="echo"
    )
    parser.add_argument("--model-id", default="echo-stub")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--parent-limit", type=int, default=None)
    parser.add_argument(
        "--proxies",
        default=",".join(PROXY_NAMES),
        help="Comma-separated built-in proxies",
    )
    parser.add_argument(
        "--judge-backend", choices=["anthropic", "api", "mlx"], default=None
    )
    parser.add_argument("--judge-model-id", default=None)
    parser.add_argument("--allow-same-judge", action="store_true")
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print eligible item and API-call counts without loading a model",
    )
    args = parser.parse_args()

    if args.k < 1:
        raise SystemExit("--k must be at least 1")
    proxies = [name.strip() for name in args.proxies.split(",") if name.strip()]
    unknown = sorted(set(proxies) - set(PROXY_NAMES))
    if unknown:
        raise SystemExit(f"Unknown built-in proxies: {unknown}")
    if args.judge_backend and not args.judge_model_id:
        raise SystemExit("--judge-model-id is required with --judge-backend")
    if (
        args.judge_model_id == args.model_id
        and not args.allow_same_judge
    ):
        raise SystemExit(
            "Agent and judge must be independent; use different backends/models "
            "or explicitly pass --allow-same-judge for a non-independent diagnostic."
        )

    manifest = args.manifest.resolve()
    all_items = read_manifest(manifest)
    _resolve_item_paths(all_items)
    items = _eligible_items(all_items, args.parent_limit)
    results_dir = args.results_dir.resolve()
    records_path = results_dir / "pressure_records.jsonl"
    meta_path = results_dir / "run_meta.json"

    experiment_config = {
        "schema_version": 2,
        "manifest_sha256": _sha256(manifest),
        "artifact_sha256": _artifact_sha256(items),
        "implementation_sha256": _combined_sha256(
            [
                Path(__file__),
                _backend_module(args.backend),
                ROOT / "src/mrha/pressure/analysis.py",
                ROOT / "src/mrha/pressure/schema.py",
                ROOT / "src/mrha/pressure/eligibility.py",
                ROOT / "src/mrha/oracles/chart_oracle.py",
                ROOT / "src/mrha/models/base.py",
                ROOT / "src/mrha/proxies/keyword_match.py",
                ROOT / "src/mrha/proxies/gold_overlap_proxy.py",
                ROOT / "src/mrha/proxies/outcome_only.py",
                ROOT / "src/mrha/proxies/weak_vlm_judge.py",
            ]
        ),
        "agent_backend_module_sha256": _sha256(_backend_module(args.backend)),
        "judge_backend_module_sha256": (
            _sha256(_backend_module(args.judge_backend))
            if args.judge_backend
            else None
        ),
        "agent_provider_endpoint": _provider_endpoint(args.backend),
        "judge_provider_endpoint": (
            _provider_endpoint(args.judge_backend) if args.judge_backend else None
        ),
        "python_version": sys.version,
        "package_versions": _package_versions(),
        "backend": args.backend,
        "model_id": args.model_id,
        "temperature": args.temperature,
        "baseline_temperature": 0.0,
        "max_tokens": args.max_tokens,
        "k": args.k,
        "seed": args.seed,
        "parent_limit": args.parent_limit,
        "proxies": proxies,
        "judge_backend": args.judge_backend,
        "judge_model_id": args.judge_model_id,
        "excluded_conditions": [
            "evidence_swap|invariance",
            "evidence_destroy|invariance",
        ],
    }
    run_hash = _config_hash(experiment_config)
    requested_eligible, requested_reasons = assess_research_eligibility(
        agent_model_id=args.model_id,
        k=args.k,
        temperature=args.temperature,
        judge_model_id=args.judge_model_id,
    )
    if args.dry_run:
        conditions: dict[str, int] = {}
        for item in items:
            key = f"{item.attack.value}|{item.protocol.value}"
            conditions[key] = conditions.get(key, 0) + 1
        agent_calls = len(items) * (args.k + 1)
        print(
            json.dumps(
                {
                    "config_hash": run_hash,
                    "eligible_items": len(items),
                    "parent_count": len(
                        {item.parent_id or item.item_id for item in items}
                    ),
                    "conditions": conditions,
                    "estimated_agent_calls": agent_calls,
                    "estimated_judge_calls": (
                        agent_calls if args.judge_backend else 0
                    ),
                    "provisionally_research_eligible": requested_eligible,
                    "eligibility_reasons": requested_reasons,
                    "will_write_results": False,
                },
                indent=2,
            )
        )
        return

    results_dir.mkdir(parents=True, exist_ok=True)
    if records_path.is_file() and not meta_path.is_file():
        raise SystemExit(
            f"Found records without run metadata in {results_dir}; refusing "
            "an unsafe resume. Choose a new --results-dir."
        )
    old_meta: dict[str, Any] | None = None
    if meta_path.is_file():
        old_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if old_meta.get("config_hash") != run_hash:
            raise SystemExit(
                f"Refusing to mix incompatible runs in {results_dir}. "
                "Choose a new --results-dir."
            )

    agent = _build_client(
        args.backend,
        args.model_id,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    judge = None
    if args.judge_backend:
        judge = _build_client(
            args.judge_backend,
            args.judge_model_id,
            temperature=0.0,
            max_tokens=16,
        )

    existing = _load_records(records_path)
    expected_item_ids = {item.item_id for item in items}
    existing_ids = [record.item_id for record in existing]
    if len(existing_ids) != len(set(existing_ids)):
        raise SystemExit("Duplicate item IDs found in existing pressure records")
    unexpected = sorted(set(existing_ids) - expected_item_ids)
    if unexpected:
        raise SystemExit(f"Unexpected existing item IDs: {unexpected[:5]}")
    bad_hashes = [
        record.item_id
        for record in existing
        if record.metadata.get("config_hash") != run_hash
    ]
    if bad_hashes:
        raise SystemExit(
            f"Existing records have incompatible config hashes: {bad_hashes[:5]}"
        )
    completed = set(existing_ids)
    oracle = ChartOracle()
    selectors = ["random", "oracle", *(f"proxy:{name}" for name in proxies)]
    if judge is not None:
        selectors.append("proxy:vlm_judge")
    expected_selectors = set(selectors)
    incompatible_records = [
        record.item_id
        for record in existing
        if set(record.selected_indices) != expected_selectors
        or record.k != args.k
        or record.seed != args.seed
        or record.agent_model_id != agent.model_id
        or record.judge_model_id != (judge.model_id if judge else None)
    ]
    if incompatible_records:
        raise SystemExit(
            "Existing pressure records do not match the current run: "
            f"{incompatible_records[:5]}"
        )

    research_eligible, eligibility_reasons = assess_research_eligibility(
        agent_model_id=agent.model_id,
        k=args.k,
        temperature=args.temperature,
        judge_model_id=judge.model_id if judge else None,
    )
    _write_json(
        meta_path,
        {
            "config_hash": run_hash,
            "config": experiment_config,
            "agent_model_id": agent.model_id,
            "judge_model_id": judge.model_id if judge else None,
            "research_eligible": research_eligible,
            "eligibility_reasons": eligibility_reasons,
            "expected_records": len(items),
            "started_at": (
                old_meta.get("started_at")
                if old_meta
                else datetime.now(timezone.utc).isoformat()
            ),
            "resumed_at": (
                datetime.now(timezone.utc).isoformat() if old_meta else None
            ),
        },
    )

    with records_path.open("a", encoding="utf-8") as stream:
        for position, item in enumerate(items, start=1):
            if item.item_id in completed:
                continue
            prompt = build_prompt(item.question, item.caption, item.prompt_prefix)
            baseline = _evaluate(
                _answer(agent, item.image_path, prompt, temperature=0.0),
                item,
                oracle,
                proxies,
                judge,
            )
            candidates = [
                _evaluate(
                    _answer(agent, item.image_path, prompt),
                    item,
                    oracle,
                    proxies,
                    judge,
                )
                for _ in range(args.k)
            ]
            selected = {
                selector: select_candidate(
                    candidates,
                    selector,
                    random.Random(f"{args.seed}:{item.item_id}:{selector}"),
                )
                for selector in selectors
            }
            record = PressureRecord(
                item_id=item.item_id,
                parent_id=item.parent_id or item.item_id,
                attack=item.attack,
                protocol=item.protocol,
                agent_model_id=agent.model_id,
                judge_model_id=judge.model_id if judge else None,
                baseline=baseline,
                candidates=candidates,
                selected_indices=selected,
                k=args.k,
                seed=args.seed,
                metadata={"prompt": prompt, "config_hash": run_hash},
            )
            stream.write(record.model_dump_json() + "\n")
            stream.flush()
            existing.append(record)
            if position % 10 == 0 or position == len(items):
                print(f"[pressure] {position}/{len(items)} items complete")

    completed_at = datetime.now(timezone.utc).isoformat()
    summary = summarize_pressure(
        existing,
        n_boot=args.bootstrap_samples,
        research_eligible=research_eligible,
    )
    summary.update(
        {
            "config_hash": run_hash,
            "manifest_sha256": experiment_config["manifest_sha256"],
            "research_eligible": research_eligible,
            "completed_at": completed_at,
        }
    )
    _write_json(results_dir / "summary.json", summary)
    final_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    final_meta.update({"completed_at": completed_at, "n_records": len(existing)})
    _write_json(results_dir / "run_meta.final.json", final_meta)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
