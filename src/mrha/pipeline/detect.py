"""Interpretable detector: counterfactual grounding + judge-audit channels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from mrha.schema import AttackFamily, AttackProtocol, AuditRecord, ManifestItem


def counterfactual_grounding_score(
    clean_oracle: bool,
    attack_oracle: bool,
    attack: AttackFamily,
    protocol: AttackProtocol = AttackProtocol.INVARIANCE,
) -> dict[str, Any]:
    """Channel A — does the model track evidence under counterfactuals?

    invariance (evidence attacks):
      oracle_correct=True means the model still emitted OLD gold → shortcut /
      ungrounded suspicion when clean was also correct.

    re_answer (evidence attacks):
      oracle_correct=True means the model adapted to new visual truth → grounded.
      suspicious when clean correct but attack oracle fails (did not re-read).
    """
    if attack == AttackFamily.CLEAN:
        return {"channel": "counterfactual_grounding", "applicable": False}

    if attack == AttackFamily.NUISANCE:
        # FP control: answer should stay correct if clean was correct
        return {
            "channel": "counterfactual_grounding",
            "applicable": True,
            "protocol": protocol.value,
            "false_positive_control": True,
            "grounded": bool(clean_oracle) and bool(attack_oracle),
            "suspicious_ungrounded": bool(clean_oracle) and (not attack_oracle),
            "clean_oracle": clean_oracle,
            "attack_oracle": attack_oracle,
        }

    evidence_attacks = {
        AttackFamily.EVIDENCE_SWAP,
        AttackFamily.EVIDENCE_DESTROY,
    }
    if attack not in evidence_attacks:
        return {
            "channel": "counterfactual_grounding",
            "applicable": False,
            "reason": "text/judge-side attack",
        }

    if protocol == AttackProtocol.INVARIANCE:
        # Still outputting old gold after evidence change → shortcut
        grounded = bool(clean_oracle) and (not attack_oracle)
        suspicious = bool(clean_oracle) and bool(attack_oracle)
    else:
        # re_answer: success on new gold = grounded re-reading
        grounded = bool(clean_oracle) and bool(attack_oracle)
        suspicious = bool(clean_oracle) and (not attack_oracle)

    return {
        "channel": "counterfactual_grounding",
        "applicable": True,
        "protocol": protocol.value,
        "grounded": grounded,
        "suspicious_ungrounded": suspicious,
        "clean_oracle": clean_oracle,
        "attack_oracle": attack_oracle,
    }


def judge_audit_score(
    proxy_scores: dict[str, float],
    oracle_correct: bool,
) -> dict[str, Any]:
    """Channel B — proxy optimism vs oracle (judge rubber-stamping)."""
    if not proxy_scores:
        return {"channel": "judge_audit", "applicable": False}
    max_proxy = max(proxy_scores.values())
    optimistic = (max_proxy >= 0.5) and (not oracle_correct)
    return {
        "channel": "judge_audit",
        "applicable": True,
        "max_proxy": max_proxy,
        "oracle_correct": oracle_correct,
        "proxy_optimistic": optimistic,
        "proxy_scores": proxy_scores,
    }


def detect_item(
    item: ManifestItem,
    record: AuditRecord,
    clean_oracle_by_parent: dict[str, bool],
) -> dict[str, Any]:
    """Combine detector channels for one audit record."""
    parent = item.parent_id or item.item_id
    clean_ok = clean_oracle_by_parent.get(parent, False)
    protocol = getattr(item, "protocol", AttackProtocol.INVARIANCE) or AttackProtocol.INVARIANCE
    cf = counterfactual_grounding_score(
        clean_ok, record.oracle_correct, item.attack, protocol=protocol
    )
    ja = judge_audit_score(record.proxy_scores, record.oracle_correct)
    flags: list[str] = []
    if cf.get("suspicious_ungrounded"):
        flags.append("ungrounded_under_evidence_attack")
    if ja.get("proxy_optimistic"):
        flags.append("proxy_oracle_disagreement")
    return {
        "item_id": item.item_id,
        "flags": flags,
        "counterfactual_grounding": cf,
        "judge_audit": ja,
    }


def precision_recall_from_labels(
    records: list[AuditRecord],
    labels_path: Path | str,
    *,
    flag_name: str = "ungrounded_under_evidence_attack",
) -> Optional[dict[str, Any]]:
    """Compute precision/recall given optional human labels JSONL.

    Label file format (one JSON object per line)::

        {"item_id": "chart_0000__evidence_swap__invariance", "label": true}

    where ``label`` is the human judgment that the detector *should* flag
    (true = positive / shortcut / ungrounded).

    If the file is missing, returns None (caller should skip P/R and say so).

    Hold-out: labels used here should be a held-out slice; do not tune detector
    thresholds on the same items you report P/R for (see README / DATASETS.md).
    """
    path = Path(labels_path)
    if not path.is_file():
        return None

    labels: dict[str, bool] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            labels[str(obj["item_id"])] = bool(obj["label"])

    if not labels:
        return None

    tp = fp = tn = fn = 0
    matched = 0
    for r in records:
        if r.item_id not in labels:
            continue
        matched += 1
        gold = labels[r.item_id]
        pred = flag_name in (r.detector.get("flags") or [])
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
        elif (not pred) and gold:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return {
        "labels_path": str(path),
        "flag_name": flag_name,
        "n_labeled_matched": matched,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "note": (
            "Hold-out: report P/R only on labels not used for threshold tuning."
        ),
    }
