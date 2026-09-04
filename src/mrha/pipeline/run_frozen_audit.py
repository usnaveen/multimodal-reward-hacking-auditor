"""Run frozen model audit: clean+attacks → proxies + oracle → results/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from mrha.metrics.compute import compute_all, write_metrics
from mrha.models.base import VLMClient, build_prompt
from mrha.oracles.chart_oracle import ChartOracle
from mrha.pipeline.build_benchmark import read_manifest
from mrha.pipeline.detect import detect_item, precision_recall_from_labels
from mrha.proxies import gold_overlap_proxy, keyword_match, outcome_only, weak_vlm_judge
from mrha.schema import AttackFamily, AttackProtocol, AuditRecord, ManifestItem


ProxyFn = Callable[[str, ManifestItem], float]


def default_proxies(
    judge_client: VLMClient | None = None,
) -> dict[str, ProxyFn]:
    """Named proxy scorers.

    By default: outcome_only + keyword_match + gold_overlap_proxy.
    ``weak_vlm_judge`` is added only when ``judge_client`` is provided.
    """
    proxies: dict[str, ProxyFn] = {
        "outcome_only": lambda r, i: outcome_only.score(r, i),
        "keyword_match": keyword_match.score,
        "gold_overlap": gold_overlap_proxy.score,
    }
    if judge_client is not None:
        client = judge_client

        def _weak(resp: str, item: ManifestItem) -> float:
            return weak_vlm_judge.score(resp, item, client=client)

        proxies["weak_vlm_judge"] = _weak
    return proxies


def run_audit(
    manifest_path: Path | str,
    client: VLMClient,
    results_dir: Path | str = "results",
    *,
    judge_client: VLMClient | None = None,
    use_weak_vlm_client: bool = False,
    limit: int | None = None,
    labels_path: Path | str | None = None,
) -> list[AuditRecord]:
    """Score model on each manifest item; write audit JSONL + metrics stub.

    Does not invent metrics — only writes what was measured.

    ``weak_vlm_judge`` runs only when ``judge_client`` is set, or when
    ``use_weak_vlm_client=True`` (uses the same ``client`` with the judge prompt).
    """
    items = read_manifest(manifest_path)
    if limit is not None:
        items = items[:limit]
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    jclient = judge_client
    if jclient is None and use_weak_vlm_client:
        jclient = client

    oracle = ChartOracle()
    proxies = default_proxies(jclient)
    records: list[AuditRecord] = []

    for item in items:
        prompt = build_prompt(item.question, item.caption, item.prompt_prefix)
        response = client.answer(item.image_path, prompt)
        ok = oracle.score(response, item)
        proxy_scores = {name: fn(response, item) for name, fn in proxies.items()}
        protocol = getattr(item, "protocol", AttackProtocol.INVARIANCE)
        records.append(
            AuditRecord(
                item_id=item.item_id,
                attack=item.attack,
                protocol=protocol,
                parent_id=item.parent_id,
                model_id=client.model_id,
                response=response,
                oracle_correct=ok,
                proxy_scores=proxy_scores,
                metadata={
                    "prompt": prompt,
                    "oracle_mode": item.metadata.get("oracle_mode"),
                    "protocol": protocol.value if protocol else None,
                },
            )
        )

    clean_map = {
        r.item_id: r.oracle_correct
        for r in records
        if r.attack == AttackFamily.CLEAN
    }
    item_by_id = {it.item_id: it for it in items}
    for rec in records:
        it = item_by_id[rec.item_id]
        rec.detector = detect_item(it, rec, clean_map)

    # Optional detector P/R
    default_labels = Path("data/labels/detector_labels.jsonl")
    lab_path = Path(labels_path) if labels_path else default_labels
    pr = precision_recall_from_labels(records, lab_path)
    if pr is None:
        detector_pr_note = (
            f"Detector P/R skipped — labels file not found at {lab_path}. "
            "See data/labels/ format in README / REQUIRED_FROM_USER.md."
        )
    else:
        detector_pr_note = None
        (results_dir / "detector_precision_recall.json").write_text(
            json.dumps(pr, indent=2), encoding="utf-8"
        )

    out_jsonl = results_dir / "audit_records.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(r.model_dump_json() + "\n")

    summary = compute_all(records)
    if detector_pr_note:
        summary.notes.append(detector_pr_note)
    elif pr is not None:
        summary.notes.append(
            f"Detector P/R: precision={pr.get('precision')} recall={pr.get('recall')} "
            f"(n_labeled={pr.get('n_labeled_matched')}); hold-out recommended."
        )
    write_metrics(summary, results_dir, records=records)

    meta = {
        "model_id": client.model_id,
        "n_records": len(records),
        "manifest": str(manifest_path),
        "audit_records": str(out_jsonl),
        "judge_enabled": jclient is not None,
        "proxies": list(proxies.keys()),
    }
    (results_dir / "run_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return records


class EchoVLM:
    """Deterministic stub VLM for offline tests (returns gold from lookup).

    Not for research claims — smoke / CI only.
    """

    model_id = "echo-stub"

    def __init__(self, mode: str = "gold_from_metadata") -> None:
        self.mode = mode
        self._gold_lookup: dict[str, str] = {}

    def set_gold_lookup(self, mapping: dict[str, str]) -> None:
        self._gold_lookup = mapping

    def answer(self, image_path: str, prompt: str) -> str:
        stem = Path(image_path).stem.split("__")[0]
        if stem in self._gold_lookup:
            return f"Answer: {self._gold_lookup[stem]}"
        if self.mode == "empty":
            return ""
        return "Answer: unknown"
