"""Run frozen model audit: clean+attacks → proxies + oracle → results/."""

from __future__ import annotations

import json
import sys
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


def _load_completed_ids(raw_jsonl: Path, model_id: str) -> set[str]:
    """Return item_ids already scored by this model_id in the raw stream file."""
    if not raw_jsonl.exists():
        return set()
    done: set[str] = set()
    with raw_jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("model_id") == model_id:
                    done.add(obj["item_id"])
            except json.JSONDecodeError:
                pass  # partial write from a previous crash — skip
    return done


def finalize_audit(
    raw_jsonl: Path,
    results_dir: Path,
    all_items: list[ManifestItem],
    labels_path: Path | None,
) -> list[AuditRecord]:
    """Post-process a completed raw stream: add detector flags + write metrics.

    Safe to call after the streaming loop finishes. Reads back the JSONL so
    clean_map covers the full run, not just in-memory chunks.
    """
    records: list[AuditRecord] = []
    with raw_jsonl.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(AuditRecord.model_validate_json(line))
            except Exception:
                pass

    clean_map = {
        r.item_id: r.oracle_correct
        for r in records
        if r.attack == AttackFamily.CLEAN
    }
    item_by_id = {it.item_id: it for it in all_items}
    for rec in records:
        it = item_by_id.get(rec.item_id)
        if it is not None:
            rec.detector = detect_item(it, rec, clean_map)

    # Rewrite with detector flags populated
    with raw_jsonl.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(r.model_dump_json() + "\n")

    # Symlink / copy to canonical audit_records.jsonl
    canonical = results_dir / "audit_records.jsonl"
    if raw_jsonl != canonical:
        canonical.write_text(raw_jsonl.read_text(encoding="utf-8"), encoding="utf-8")

    # Optional detector P/R
    default_labels = Path("data/labels/detector_labels.jsonl")
    lab_path = labels_path if labels_path else default_labels
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

    summary = compute_all(records)
    if pr is None:
        summary.notes.append(detector_pr_note)  # type: ignore[arg-type]
    else:
        summary.notes.append(
            f"Detector P/R: precision={pr.get('precision')} recall={pr.get('recall')} "
            f"(n_labeled={pr.get('n_labeled_matched')}); hold-out recommended."
        )
    write_metrics(summary, results_dir, records=records)
    return records


def run_audit(
    manifest_path: Path | str,
    client: VLMClient,
    results_dir: Path | str = "results",
    *,
    judge_client: VLMClient | None = None,
    use_weak_vlm_client: bool = False,
    limit: int | None = None,
    labels_path: Path | str | None = None,
    resume: bool = True,
) -> list[AuditRecord]:
    """Score model on each manifest item; stream-write audit JSONL + metrics.

    Streaming + resume
    ------------------
    Each record is appended to ``<results_dir>/audit_raw_<model_id>.jsonl``
    immediately after scoring so progress survives process kills. On restart
    with ``resume=True``, already-scored item_ids (same model_id) are skipped.
    Detector flags and metrics are computed in a final pass over the full file
    so ``clean_map`` is always built from the complete dataset.

    Does not invent metrics — only writes what was measured.
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

    # Use a model-specific stream file to avoid mixing stale runs
    safe_model_id = client.model_id.replace("/", "_").replace(":", "_")
    raw_jsonl = results_dir / f"audit_raw_{safe_model_id}.jsonl"

    # Resume: load already-completed item_ids for this model
    done_ids: set[str] = set()
    if resume:
        done_ids = _load_completed_ids(raw_jsonl, client.model_id)
        if done_ids:
            print(
                f"[resume] {len(done_ids)} items already scored — skipping.",
                file=sys.stderr,
                flush=True,
            )

    remaining = [it for it in items if it.item_id not in done_ids]
    total = len(items)
    completed = len(done_ids)

    with raw_jsonl.open("a", encoding="utf-8") as stream:
        for i, item in enumerate(remaining, start=1):
            prompt = build_prompt(item.question, item.caption, item.prompt_prefix)
            response = client.answer(item.image_path, prompt)
            ok = oracle.score(response, item)
            proxy_scores = {name: fn(response, item) for name, fn in proxies.items()}
            protocol = getattr(item, "protocol", AttackProtocol.INVARIANCE)
            rec = AuditRecord(
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
            stream.write(rec.model_dump_json() + "\n")
            stream.flush()
            completed += 1
            if i % 10 == 0 or i == len(remaining):
                print(
                    f"[audit] {completed}/{total} scored",
                    file=sys.stderr,
                    flush=True,
                )

    # Final pass: build clean_map from full file, add detector flags, write metrics
    lab_path = Path(labels_path) if labels_path else None
    records = finalize_audit(raw_jsonl, results_dir, items, lab_path)

    meta = {
        "model_id": client.model_id,
        "n_records": len(records),
        "manifest": str(manifest_path),
        "audit_records": str(results_dir / "audit_records.jsonl"),
        "raw_stream": str(raw_jsonl),
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
