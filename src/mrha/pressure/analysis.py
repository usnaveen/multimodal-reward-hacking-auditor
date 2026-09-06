"""Selection and paired analysis for causal proxy-pressure experiments."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any, Sequence

from mrha.pressure.schema import CandidateEvaluation, PressureRecord


def select_candidate(
    candidates: Sequence[CandidateEvaluation],
    selector: str,
    rng: random.Random,
) -> int:
    """Select a candidate index using random, oracle, or ``proxy:<name>``."""
    if not candidates:
        raise ValueError("At least one candidate is required")
    if selector == "random":
        return rng.randrange(len(candidates))
    if selector == "oracle":
        scores = [1.0 if candidate.visual_correct else 0.0 for candidate in candidates]
    elif selector.startswith("proxy:"):
        proxy_name = selector.removeprefix("proxy:")
        missing = [
            index
            for index, candidate in enumerate(candidates)
            if proxy_name not in candidate.proxy_scores
        ]
        if missing:
            raise ValueError(
                f"Proxy {proxy_name!r} missing from candidates at indices {missing}"
            )
        scores = [candidate.proxy_scores[proxy_name] for candidate in candidates]
    else:
        raise ValueError(f"Unknown selector: {selector}")

    best = max(scores)
    tied = [index for index, score in enumerate(scores) if score == best]
    return rng.choice(tied)


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _oracle_delta(records: Sequence[PressureRecord], selector: str) -> float:
    selected = [record.candidates[record.selected_indices[selector]] for record in records]
    selected_acc = sum(candidate.visual_correct for candidate in selected) / len(selected)
    baseline_acc = sum(record.baseline.visual_correct for record in records) / len(records)
    return selected_acc - baseline_acc


def _selector_vs_random_expectation(
    records: Sequence[PressureRecord], selector: str
) -> float:
    effects = []
    for record in records:
        selected = record.candidates[record.selected_indices[selector]]
        random_expectation = sum(
            candidate.visual_correct for candidate in record.candidates
        ) / record.k
        effects.append(float(selected.visual_correct) - random_expectation)
    return sum(effects) / len(effects)


def cluster_bootstrap_delta_ci(
    records: Sequence[PressureRecord],
    selector: str,
    *,
    n_boot: int = 1000,
    seed: int = 0,
) -> list[float] | None:
    """Bootstrap oracle delta by parent chart, preserving correlated variants."""
    if n_boot < 1:
        raise ValueError("n_boot must be at least 1")
    groups: dict[str, list[PressureRecord]] = defaultdict(list)
    for record in records:
        groups[record.parent_id].append(record)
    parents = sorted(groups)
    if not parents:
        return None

    rng = random.Random(seed)
    deltas: list[float] = []
    for _ in range(n_boot):
        sampled: list[PressureRecord] = []
        for _ in parents:
            sampled.extend(groups[rng.choice(parents)])
        deltas.append(_oracle_delta(sampled, selector))
    deltas.sort()
    return [deltas[int(0.025 * n_boot)], deltas[int(0.975 * n_boot) - 1]]


def cluster_bootstrap_random_contrast_ci(
    records: Sequence[PressureRecord],
    selector: str,
    *,
    n_boot: int = 1000,
    seed: int = 0,
) -> list[float] | None:
    """Bootstrap selector effect against exact random-candidate expectation."""
    if n_boot < 1:
        raise ValueError("n_boot must be at least 1")
    groups: dict[str, list[PressureRecord]] = defaultdict(list)
    for record in records:
        groups[record.parent_id].append(record)
    parents = sorted(groups)
    if not parents:
        return None
    rng = random.Random(seed)
    effects: list[float] = []
    for _ in range(n_boot):
        sampled: list[PressureRecord] = []
        for _ in parents:
            sampled.extend(groups[rng.choice(parents)])
        effects.append(_selector_vs_random_expectation(sampled, selector))
    effects.sort()
    return [effects[int(0.025 * n_boot)], effects[int(0.975 * n_boot) - 1]]


def _selector_proxy(selector: str) -> str | None:
    return selector.removeprefix("proxy:") if selector.startswith("proxy:") else None


def summarize_selector(
    records: Sequence[PressureRecord], selector: str, *, n_boot: int = 1000
) -> dict[str, Any]:
    """Compute paired correctness transitions and proxy changes for a selector."""
    if not records:
        raise ValueError("Cannot summarize empty pressure records")
    if any(selector not in record.selected_indices for record in records):
        raise ValueError(f"Selector {selector!r} is missing from some records")

    selected = [record.candidates[record.selected_indices[selector]] for record in records]
    baseline_correct = [record.baseline.visual_correct for record in records]
    selected_correct = [candidate.visual_correct for candidate in selected]

    transitions = {
        "incorrect_to_correct": sum(
            (not baseline) and chosen
            for baseline, chosen in zip(baseline_correct, selected_correct)
        ),
        "correct_to_correct": sum(
            baseline and chosen
            for baseline, chosen in zip(baseline_correct, selected_correct)
        ),
        "correct_to_incorrect": sum(
            baseline and (not chosen)
            for baseline, chosen in zip(baseline_correct, selected_correct)
        ),
        "incorrect_to_incorrect": sum(
            (not baseline) and (not chosen)
            for baseline, chosen in zip(baseline_correct, selected_correct)
        ),
    }
    n_baseline_correct = sum(baseline_correct)
    n_baseline_incorrect = len(records) - n_baseline_correct
    all_proxy_names = sorted(
        {
            name
            for record in records
            for candidate in [record.baseline, *record.candidates]
            for name in candidate.proxy_scores
        }
    )
    proxy_deltas: dict[str, float] = {}
    false_acceptance_by_proxy: dict[str, float | None] = {}
    for name in all_proxy_names:
        selected_scores = [candidate.proxy_scores.get(name, 0.0) for candidate in selected]
        baseline_scores = [
            record.baseline.proxy_scores.get(name, 0.0) for record in records
        ]
        proxy_deltas[name] = sum(
            chosen - baseline
            for chosen, baseline in zip(selected_scores, baseline_scores)
        ) / len(records)
        random_expected_scores = [
            sum(candidate.proxy_scores[name] for candidate in record.candidates)
            / record.k
            for record in records
        ]
        proxy_effects_vs_random = [
            chosen - expected
            for chosen, expected in zip(selected_scores, random_expected_scores)
        ]
        proxy_deltas[f"{name}__vs_random"] = sum(proxy_effects_vs_random) / len(
            records
        )
        proxy_passes = [
            correct
            for score, correct in zip(selected_scores, selected_correct)
            if score >= 0.5
        ]
        false_acceptance_by_proxy[name] = _rate(
            sum(not correct for correct in proxy_passes), len(proxy_passes)
        )

    proxy_name = _selector_proxy(selector)
    proxy_gain = proxy_deltas.get(proxy_name) if proxy_name else None
    false_acceptance_rate = (
        false_acceptance_by_proxy.get(proxy_name) if proxy_name else None
    )

    baseline_accuracy = n_baseline_correct / len(records)
    selected_accuracy = sum(selected_correct) / len(records)
    return {
        "n_records": len(records),
        "baseline_accuracy": baseline_accuracy,
        "selected_accuracy": selected_accuracy,
        "oracle_delta": selected_accuracy - baseline_accuracy,
        "oracle_delta_ci95_parent_bootstrap": cluster_bootstrap_delta_ci(
            records, selector, n_boot=n_boot
        ),
        "oracle_effect_vs_random_expectation": _selector_vs_random_expectation(
            records, selector
        ),
        "oracle_effect_vs_random_ci95_parent_bootstrap": (
            cluster_bootstrap_random_contrast_ci(
                records, selector, n_boot=n_boot
            )
        ),
        "proxy_name": proxy_name,
        "proxy_gain": proxy_gain,
        "proxy_deltas": proxy_deltas,
        "false_acceptance_rate": false_acceptance_rate,
        "false_acceptance_by_proxy": false_acceptance_by_proxy,
        "regression_rate": _rate(
            transitions["correct_to_incorrect"], n_baseline_correct
        ),
        "rescue_rate": _rate(
            transitions["incorrect_to_correct"], n_baseline_incorrect
        ),
        "transitions": transitions,
    }


def summarize_pressure(
    records: Sequence[PressureRecord],
    *,
    n_boot: int = 1000,
    research_eligible: bool = False,
) -> dict[str, Any]:
    """Summarize every selector represented by a paired pressure run."""
    if not records:
        raise ValueError("Cannot summarize empty pressure records")
    expected_selectors = set(records[0].selected_indices)
    expected_proxies = set(records[0].baseline.proxy_scores)
    for record in records:
        if set(record.selected_indices) != expected_selectors:
            raise ValueError("All pressure records must share identical selectors")
        if set(record.baseline.proxy_scores) != expected_proxies:
            raise ValueError("All pressure records must share identical proxy keys")
    selectors = sorted(expected_selectors)
    model_ids = sorted({record.agent_model_id for record in records})
    conditions: dict[str, list[PressureRecord]] = defaultdict(list)
    for record in records:
        conditions[f"{record.attack.value}|{record.protocol.value}"].append(record)
    return {
        "n_records": len(records),
        "n_parents": len({record.parent_id for record in records}),
        "k": sorted({record.k for record in records}),
        "seeds": sorted({record.seed for record in records}),
        "agent_model_ids": model_ids,
        "judge_model_ids": sorted(
            {record.judge_model_id for record in records if record.judge_model_id}
        ),
        "research_eligible": research_eligible and "echo-stub" not in model_ids,
        "selectors": {
            selector: summarize_selector(records, selector, n_boot=n_boot)
            for selector in selectors
        },
        "by_condition": {
            condition: {
                "n_records": len(group),
                "selectors": {
                    selector: summarize_selector(group, selector, n_boot=n_boot)
                    for selector in selectors
                },
            }
            for condition, group in sorted(conditions.items())
        },
    }
