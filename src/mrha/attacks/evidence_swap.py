"""Evidence swap: alter bar/line/pie values while keeping the question fixed."""

from __future__ import annotations

import copy
from pathlib import Path

from mrha.attacks.base import Attack
from mrha.charts.answer_from_truth import answer_from_truth, category_from_question
from mrha.charts.generate import render_chart, save_truth
from mrha.schema import AttackFamily, AttackProtocol, ChartTruth, ManifestItem


def _permute_values(vals: list[float], seed: int) -> list[float]:
    """Deterministic rotate/permute (not identity when len >= 2)."""
    if len(vals) < 2:
        return list(vals)
    k = (seed % (len(vals) - 1)) + 1
    return vals[k:] + vals[:k]


def _swap_max_min(vals: list[float]) -> list[float]:
    out = list(vals)
    i_max = max(range(len(out)), key=lambda i: out[i])
    i_min = min(range(len(out)), key=lambda i: out[i])
    out[i_max], out[i_min] = out[i_min], out[i_max]
    return out


class EvidenceSwapAttack(Attack):
    """Swap / permute / swap-max-min series values so visual evidence changes."""

    family = AttackFamily.EVIDENCE_SWAP
    supports_protocols = True

    def apply(
        self,
        clean: ManifestItem,
        truth: ChartTruth,
        out_dir: Path,
        seed: int = 0,
        protocol: AttackProtocol = AttackProtocol.INVARIANCE,
    ) -> ManifestItem:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        attacked = copy.deepcopy(truth)
        before = list(attacked.values)
        if len(before) < 2:
            raise ValueError("Need >=2 categories for evidence_swap")

        mode = ["permute", "swap_max_min", "reverse"][seed % 3]
        if mode == "permute":
            after = _permute_values(before, seed)
        elif mode == "swap_max_min":
            after = _swap_max_min(before)
        else:
            after = list(reversed(before))
        attacked.values = after

        proto_tag = protocol.value
        item_id = f"{clean.item_id}__{self.family.value}__{proto_tag}"
        img = out_dir / f"{item_id}.png"
        visual_truth_path = out_dir / f"{item_id}_visual_truth.json"
        render_chart(attacked, img)
        save_truth(attacked, visual_truth_path)

        cat_hint = category_from_question(clean.question, truth.categories)
        visual_gold, visual_num = answer_from_truth(
            attacked, clean.question_type, category_hint=cat_hint
        )

        if protocol == AttackProtocol.RE_ANSWER:
            answer_gold = visual_gold
            answer_numeric = visual_num
            # Oracle should check against visual truth file
            truth_path = str(visual_truth_path)
        else:
            answer_gold = clean.answer_gold
            answer_numeric = clean.answer_numeric
            truth_path = clean.truth_path

        return ManifestItem(
            item_id=item_id,
            parent_id=clean.item_id,
            attack=self.family,
            protocol=protocol,
            chart_type=clean.chart_type,
            image_path=str(img),
            truth_path=truth_path,
            question=clean.question,
            question_type=clean.question_type,
            answer_gold=answer_gold,
            answer_numeric=answer_numeric,
            caption=clean.caption,
            prompt_prefix=clean.prompt_prefix,
            metadata={
                "attack_detail": mode,
                "swap_mode": mode,
                "values_before": before,
                "values_after": after,
                "visual_truth_path": str(visual_truth_path),
                "visual_answer_gold": visual_gold,
                "visual_answer_numeric": visual_num,
                "clean_answer_gold": clean.answer_gold,
                "protocol": protocol.value,
                "seed": seed,
            },
        )
