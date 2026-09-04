"""Keyword-match proxy: crude string overlap with gold (easy to bait)."""

from __future__ import annotations

import re

from mrha.schema import ManifestItem


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def score(response: str, item: ManifestItem) -> float:
    """Jaccard overlap between response tokens and gold answer tokens.

    Judge-bait overlays that print the gold answer can inflate this proxy
    even when visual evidence is destroyed.
    """
    g = _tokens(item.answer_gold)
    r = _tokens(response)
    if not g:
        return 0.0
    inter = len(g & r)
    union = len(g | r) or 1
    return inter / union
