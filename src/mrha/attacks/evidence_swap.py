"""Evidence swap: alter bar/line/pie values while keeping the question fixed."""

from __future__ import annotations

import copy
from pathlib import Path

from mrha.attacks.base import Attack
from mrha.charts.generate import render_chart, save_truth
from mrha.schema import AttackFamily, ChartTruth, ManifestItem


class EvidenceSwapAttack(Attack):
    """Swap or permute series values so the visual evidence no longer matches gold."""

    family = AttackFamily.EVIDENCE_SWAP

    def apply(
        self,
        clean: ManifestItem,
        truth: ChartTruth,
        out_dir: Path,
        seed: int = 0,
    ) -> ManifestItem:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        attacked = copy.deepcopy(truth)
        vals = list(attacked.values)
        if len(vals) < 2:
            raise ValueError("Need >=2 categories for evidence_swap")
        # Reverse order — max becomes min for typical charts
        attacked.values = list(reversed(vals))
        # Also swap first/last category labels relative to values? Keep labels,
        # only change heights so the chart lies about the stored gold.
        item_id = f"{clean.item_id}__{self.family.value}"
        img = out_dir / f"{item_id}.png"
        truth_path = out_dir / f"{item_id}_truth.json"
        render_chart(attacked, img)
        # Store *attacked visual* truth for debugging, but gold answer stays
        # from the clean oracle (question unchanged).
        save_truth(attacked, truth_path)
        return ManifestItem(
            item_id=item_id,
            parent_id=clean.item_id,
            attack=self.family,
            chart_type=clean.chart_type,
            image_path=str(img),
            truth_path=clean.truth_path,  # oracle uses CLEAN truth
            question=clean.question,
            question_type=clean.question_type,
            answer_gold=clean.answer_gold,
            answer_numeric=clean.answer_numeric,
            caption=clean.caption,
            prompt_prefix=clean.prompt_prefix,
            metadata={
                "attack_detail": "reversed_values",
                "visual_truth_path": str(truth_path),
                "seed": seed,
            },
        )
