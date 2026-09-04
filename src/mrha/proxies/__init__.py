"""Proxy scorers — never treat as ground truth."""

from mrha.proxies import gold_overlap_proxy, keyword_match, outcome_only, weak_vlm_judge

__all__ = [
    "outcome_only",
    "keyword_match",
    "gold_overlap_proxy",
    "weak_vlm_judge",
]
