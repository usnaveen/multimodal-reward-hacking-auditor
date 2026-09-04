"""Run frozen model audit: clean+attacks → proxies + oracle → results/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from mrha.metrics.compute import compute_all, write_metrics
from mrha.models.base import VLMClient, build_prompt
from mrha.oracles.chart_oracle import ChartOracle
from mrha.pipeline.build_benchmark import read_manifest
from mrha.pipeline.detect import detect_item
from mrha.proxies import keyword_match, outcome_only, weak_vlm_judge
from mrha.schema import AttackFamily, AuditRecord, ManifestItem


ProxyFn = Callable[[str, ManifestItem], float]


def default_proxies(client: VLMClient | None = None) -> dict[str, ProxyFn]:
    """Named proxy scorers."""

    def _weak(resp: str, item: ManifestItem) -> float:
        return weak_vlm_judge.score(resp, item, client=None)

    return {
        "outcome_only": lambda r, i: outcome_only.score(r, i),
        "keyword_match": keyword_match.score,
        "weak_vlm_judge": _weak,
    }


def run_audit(
    manifest_path: Path | str,
    client: VLMClient,
    results_dir: Path | str = "results",
    *,
    use_weak_vlm_client: bool = False,
    limit: int | None = None,
) -> list[AuditRecord]:
    """Score model on each manifest item; write audit JSONL + metrics stub.

    Does not invent metrics — only writes what was measured.
    """
    items = read_manifest(manifest_path)
    if limit is not None:
        items = items[:limit]
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    oracle = ChartOracle()
    proxies = default_proxies(client if use_weak_vlm_client else None)
    records: list[AuditRecord] = []

    for item in items:
        prompt = build_prompt(item.question, item.caption, item.prompt_prefix)
        response = client.answer(item.image_path, prompt)
        ok = oracle.score(response, item)
        proxy_scores = {name: fn(response, item) for name, fn in proxies.items()}
        records.append(
            AuditRecord(
                item_id=item.item_id,
                attack=item.attack,
                parent_id=item.parent_id,
                model_id=client.model_id,
                response=response,
                oracle_correct=ok,
                proxy_scores=proxy_scores,
                metadata={"prompt": prompt},
            )
        )

    # Detector pass (needs clean oracle map)
    clean_map = {
        r.item_id: r.oracle_correct
        for r in records
        if r.attack == AttackFamily.CLEAN
    }
    # Also index by parent for attacks
    item_by_id = {it.item_id: it for it in items}
    for rec in records:
        it = item_by_id[rec.item_id]
        parent = it.parent_id or it.item_id
        # clean_map keys are clean item_ids
        rec.detector = detect_item(it, rec, clean_map)

    out_jsonl = results_dir / "audit_records.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(r.model_dump_json() + "\n")

    summary = compute_all(records)
    write_metrics(summary, results_dir, records=records)

    meta = {
        "model_id": client.model_id,
        "n_records": len(records),
        "manifest": str(manifest_path),
        "audit_records": str(out_jsonl),
    }
    (results_dir / "run_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return records


class EchoVLM:
    """Deterministic stub VLM for offline tests (returns gold from caption bait).

    Not for research claims — smoke / CI only.
    """

    model_id = "echo-stub"

    def __init__(self, mode: str = "gold_from_metadata") -> None:
        self.mode = mode
        self._gold_lookup: dict[str, str] = {}

    def set_gold_lookup(self, mapping: dict[str, str]) -> None:
        self._gold_lookup = mapping

    def answer(self, image_path: str, prompt: str) -> str:
        # Prefer lookup by image stem
        stem = Path(image_path).stem.split("__")[0]
        if stem in self._gold_lookup:
            return self._gold_lookup[stem]
        # Heuristic: if prompt contains "Answer briefly" return empty-ish
        if self.mode == "empty":
            return ""
        return "unknown"
