"""Evidence destroy: occlude / blur the critical chart region."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from mrha.attacks.base import Attack
from mrha.schema import AttackFamily, ChartTruth, ManifestItem


class EvidenceDestroyAttack(Attack):
    """Occlude central plot area so evidence is destroyed but question remains."""

    family = AttackFamily.EVIDENCE_DESTROY

    def apply(
        self,
        clean: ManifestItem,
        truth: ChartTruth,
        out_dir: Path,
        seed: int = 0,
    ) -> ManifestItem:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        src = Path(clean.image_path)
        img = Image.open(src).convert("RGB")
        w, h = img.size
        # Heavy blur + black rectangle over central plot region
        blurred = img.filter(ImageFilter.GaussianBlur(radius=12))
        draw = ImageDraw.Draw(blurred)
        # Cover ~55% of central area
        x0, y0 = int(w * 0.15), int(h * 0.2)
        x1, y1 = int(w * 0.85), int(h * 0.85)
        draw.rectangle([x0, y0, x1, y1], fill=(30, 30, 30))
        item_id = f"{clean.item_id}__{self.family.value}"
        out = out_dir / f"{item_id}.png"
        blurred.save(out)
        return ManifestItem(
            item_id=item_id,
            parent_id=clean.item_id,
            attack=self.family,
            chart_type=clean.chart_type,
            image_path=str(out),
            truth_path=clean.truth_path,
            question=clean.question,
            question_type=clean.question_type,
            answer_gold=clean.answer_gold,
            answer_numeric=clean.answer_numeric,
            caption=clean.caption,
            prompt_prefix=clean.prompt_prefix,
            metadata={"attack_detail": "central_occlusion_blur", "seed": seed},
        )
