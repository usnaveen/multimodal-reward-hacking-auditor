"""Causal pressure selection, transitions, and provenance tests."""

from __future__ import annotations

import random

import pytest

from mrha.pressure.analysis import select_candidate, summarize_pressure
from mrha.pressure.eligibility import assess_research_eligibility
from mrha.pressure.schema import CandidateEvaluation, PressureRecord
from mrha.schema import AttackFamily, AttackProtocol


def _candidate(correct: bool, proxy: float) -> CandidateEvaluation:
    return CandidateEvaluation(
        response=f"Answer: {'right' if correct else 'wrong'}",
        visual_correct=correct,
        proxy_scores={"weak": proxy},
    )


def _record(
    item_id: str,
    *,
    baseline_correct: bool,
    candidates: list[CandidateEvaluation],
    selections: dict[str, int],
) -> PressureRecord:
    return PressureRecord(
        item_id=item_id,
        parent_id=item_id.split("__")[0],
        attack=AttackFamily.CLEAN,
        protocol=AttackProtocol.INVARIANCE,
        agent_model_id="real-model",
        baseline=_candidate(baseline_correct, 0.2 if baseline_correct else 0.1),
        candidates=candidates,
        selected_indices=selections,
        k=len(candidates),
        seed=0,
    )


def test_select_candidate_supports_random_proxy_and_oracle() -> None:
    candidates = [_candidate(False, 1.0), _candidate(True, 0.0)]

    assert select_candidate(candidates, "proxy:weak", random.Random(0)) == 0
    assert select_candidate(candidates, "oracle", random.Random(0)) == 1
    assert select_candidate(candidates, "random", random.Random(0)) in {0, 1}
    with pytest.raises(ValueError, match="Unknown selector"):
        select_candidate(candidates, "mystery", random.Random(0))


def test_summary_reports_regressions_rescues_and_proxy_divergence() -> None:
    candidates = [_candidate(False, 1.0), _candidate(True, 0.0)]
    selections = {"proxy:weak": 0, "oracle": 1, "random": 0}
    records = [
        _record(
            "chart_1",
            baseline_correct=True,
            candidates=candidates,
            selections=selections,
        ),
        _record(
            "chart_2",
            baseline_correct=False,
            candidates=candidates,
            selections=selections,
        ),
    ]

    summary = summarize_pressure(records, n_boot=100, research_eligible=True)
    proxy = summary["selectors"]["proxy:weak"]
    assert proxy["baseline_accuracy"] == 0.5
    assert proxy["selected_accuracy"] == 0.0
    assert proxy["oracle_delta"] == -0.5
    assert proxy["regression_rate"] == 1.0
    assert proxy["rescue_rate"] == 0.0
    assert proxy["false_acceptance_rate"] == 1.0
    assert proxy["proxy_gain"] == pytest.approx(0.85)
    assert summary["selectors"]["random"]["proxy_deltas"]["weak"] == pytest.approx(
        0.85
    )
    assert proxy["transitions"] == {
        "incorrect_to_correct": 0,
        "correct_to_correct": 0,
        "correct_to_incorrect": 1,
        "incorrect_to_incorrect": 1,
    }

    oracle = summary["selectors"]["oracle"]
    assert oracle["selected_accuracy"] == 1.0
    assert oracle["regression_rate"] == 0.0
    assert oracle["rescue_rate"] == 1.0
    assert summary["research_eligible"] is True
    assert summary["by_condition"]["clean|invariance"]["n_records"] == 2


def test_pressure_schema_rejects_inconsistent_candidates_and_selections() -> None:
    with pytest.raises(ValueError, match="finite"):
        _candidate(False, float("nan"))

    with pytest.raises(ValueError, match="Candidate count"):
        PressureRecord(
            item_id="bad",
            parent_id="bad",
            attack=AttackFamily.CLEAN,
            protocol=AttackProtocol.INVARIANCE,
            agent_model_id="real-model",
            baseline=_candidate(True, 0.5),
            candidates=[_candidate(True, 0.5)],
            selected_indices={"oracle": 0},
            k=2,
            seed=0,
        )

    with pytest.raises(ValueError, match="out of range"):
        _record(
            "bad-index",
            baseline_correct=True,
            candidates=[_candidate(True, 0.5)],
            selections={"oracle": 3},
        )


def test_bootstrap_requires_positive_sample_count() -> None:
    record = _record(
        "chart_1",
        baseline_correct=True,
        candidates=[_candidate(True, 1.0)],
        selections={"oracle": 0},
    )
    with pytest.raises(ValueError, match="n_boot"):
        summarize_pressure([record], n_boot=0, research_eligible=True)


def test_research_eligibility_fails_closed_for_noncausal_configs() -> None:
    eligible, reasons = assess_research_eligibility(
        agent_model_id="real-agent",
        k=1,
        temperature=0.0,
        judge_model_id="real-agent",
    )
    assert eligible is False
    assert len(reasons) == 3

    eligible, reasons = assess_research_eligibility(
        agent_model_id="real-agent",
        k=4,
        temperature=0.7,
        judge_model_id="independent-judge",
    )
    assert eligible is True
    assert reasons == []


def test_echo_stub_is_never_research_eligible() -> None:
    record = _record(
        "chart_1",
        baseline_correct=True,
        candidates=[_candidate(True, 1.0)],
        selections={"oracle": 0},
    ).model_copy(update={"agent_model_id": "echo-stub"})

    assert (
        summarize_pressure([record], n_boot=10, research_eligible=True)[
            "research_eligible"
        ]
        is False
    )
