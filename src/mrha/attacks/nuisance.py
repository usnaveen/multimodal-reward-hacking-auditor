"""Nuisance attack: harmless visual change that should NOT change the answer.

Used as a false-positive control for detectors / shortcut flags.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

from mrha.attacks.base import Attack
from mrha.schema import AttackFamily, AttackProtocol, ChartTruth, ManifestItem


class NuisanceAttack(Attack):
    """Slight crop/pad/color shift — answer must remain the clean gold."""

    family = AttackFamily.NUISANCE

    def apply(
        self,
        clean: ManifestItem,
        truth: ChartTruth,
        out_dir: Path,
        seed: int = 0,
        protocol: AttackProtocol = AttackProtocol.INVARIANCE,
    ) -> ManifestItem:
        del truth, protocol
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        img = Image.open(clean.image_path).convert("RGB")
        w, h = img.size

        mode = ["pad", "crop", "color"][seed % 3]
        if mode == "pad":
            pad = 10 + (seed % 6)
            canvas = Image.new("RGB", (w + 2 * pad, h + 2 * pad), (250, 250, 250))
            canvas.paste(img, (pad, pad))
            out_img = canvas
            detail = f"pad_{pad}"
        elif mode == "crop":
            margin = 4 + (seed % 4)
            cropped = img.crop((margin, margin, w - margin, h - margin))
            out_img = cropped.resize((w, h), Image.Resampling.BILINEAR)
            detail = f"crop_margin_{margin}"
        else:
            factor = 0.92 + (seed % 5) * 0.02  # mild
            out_img = ImageEnhance.Color(img).enhance(factor)
            out_img = ImageOps.autocontrast(out_img, cutoff=1)
            detail = f"color_{factor:.2f}"

        item_id = f"{clean.item_id}__{self.family.value}"
        out = out_dir / f"{item_id}.png"
        out_img.save(out)

        return ManifestItem(
            item_id=item_id,
            parent_id=clean.item_id,
            attack=self.family,
            protocol=AttackProtocol.INVARIANCE,
            chart_type=clean.chart_type,
            image_path=str(out),
            truth_path=clean.truth_path,
            question=clean.question,
            question_type=clean.question_type,
            answer_gold=clean.answer_gold,
            answer_numeric=clean.answer_numeric,
            caption=clean.caption,
            prompt_prefix=clean.prompt_prefix,
            metadata={
                "attack_detail": f"nuisance_{detail}",
                "nuisance_mode": mode,
                "should_change_answer": False,
                "seed": seed,
            },
        )
