"""Attack interface: transform a clean chart into an adversarial variant."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from mrha.schema import AttackFamily, AttackProtocol, ChartTruth, ManifestItem


class Attack(ABC):
    """Base class for attack families."""

    family: AttackFamily
    # Evidence attacks support dual protocols; others default to invariance.
    supports_protocols: bool = False

    @abstractmethod
    def apply(
        self,
        clean: ManifestItem,
        truth: ChartTruth,
        out_dir: Path,
        seed: int = 0,
        protocol: AttackProtocol = AttackProtocol.INVARIANCE,
    ) -> ManifestItem:
        """Produce an attacked ManifestItem; write new image if needed."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(family={self.family})"


def registry() -> dict[AttackFamily, Attack]:
    """Lazy registry of concrete attacks."""
    from mrha.attacks.evidence_destroy import EvidenceDestroyAttack
    from mrha.attacks.evidence_swap import EvidenceSwapAttack
    from mrha.attacks.judge_bait import JudgeBaitAttack
    from mrha.attacks.nuisance import NuisanceAttack
    from mrha.attacks.wrong_caption import WrongCaptionAttack

    attacks = [
        EvidenceSwapAttack(),
        EvidenceDestroyAttack(),
        WrongCaptionAttack(),
        JudgeBaitAttack(),
        NuisanceAttack(),
    ]
    return {a.family: a for a in attacks}
