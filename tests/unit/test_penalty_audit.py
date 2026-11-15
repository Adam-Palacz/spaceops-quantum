"""λ=41 penalty audit: QUBO minimum versus original task feasibility."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from spaceops_quantum.domain import evaluate_solution, load_scenario
from spaceops_quantum.encoding import (
    EncodingError,
    SlackValues,
    assess_sample,
    build_qubo,
    encode_assignment,
    find_qubo_minima,
)

FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"
PENALTIES = {"energy": 41, "storage": 41, "downlink": 41}


def test_feasible_and_infeasible_samples_are_not_confused() -> None:
    scenario = load_scenario(FIXTURE)
    model = build_qubo(scenario, PENALTIES)
    optimum = evaluate_solution(scenario, [1, 1, 0, 0, 1, 1])
    feasible_but_wrong_slack = assess_sample(
        model,
        scenario,
        encode_assignment(model.bit_layout, optimum.bit_vector, SlackValues(0, 0, 0)),
    )
    infeasible = assess_sample(
        model,
        scenario,
        encode_assignment(model.bit_layout, [1, 1, 1, 1, 1, 1], SlackValues(0, 0, 0)),
    )

    assert optimum.priority == 27
    assert optimum.used.energy == 9
    assert feasible_but_wrong_slack.task_feasible is True
    assert feasible_but_wrong_slack.equality_satisfied is False
    assert feasible_but_wrong_slack.residual.energy == -1
    assert feasible_but_wrong_slack.priority == 27
    assert feasible_but_wrong_slack.qubo_energy == -27 + 41
    assert infeasible.task_feasible is False
    assert infeasible.priority == 40
    assert infeasible.equality_satisfied is False
    assert infeasible.weighted_penalty >= 41
    assert infeasible.qubo_energy >= 1
    assert infeasible.qubo_energy == -infeasible.priority + infeasible.weighted_penalty
    assert "qiskit" not in sys.modules


def test_empty_selection_is_feasible_only_with_slack_equal_to_the_budgets() -> None:
    scenario = load_scenario(FIXTURE)
    model = build_qubo(scenario, PENALTIES)
    task_bits = [0, 0, 0, 0, 0, 0]
    satisfied = assess_sample(
        model,
        scenario,
        encode_assignment(model.bit_layout, task_bits, SlackValues(10, 10, 10)),
    )
    zero_slack = assess_sample(
        model,
        scenario,
        encode_assignment(model.bit_layout, task_bits, SlackValues(0, 0, 0)),
    )

    assert satisfied.task_feasible is True
    assert satisfied.equality_satisfied is True
    assert satisfied.priority == 0
    assert satisfied.qubo_energy == 0
    assert zero_slack.task_feasible is True
    assert zero_slack.equality_satisfied is False
    assert zero_slack.qubo_energy == model.constant


def test_lambda_41_global_minimum_is_the_reference_optimum() -> None:
    scenario = load_scenario(FIXTURE)
    model = build_qubo(scenario, PENALTIES)
    priority_27 = []
    feasible_count = 0
    for mask in range(64):
        bits = [(mask >> index) & 1 for index in range(6)]
        evaluation = evaluate_solution(scenario, bits)
        if evaluation.feasible:
            feasible_count += 1
            if evaluation.priority == 27:
                priority_27.append(evaluation.selected_task_ids)
    optimum_bits = encode_assignment(
        model.bit_layout,
        [1, 1, 0, 0, 1, 1],
        SlackValues(1, 0, 0),
    )

    minima = find_qubo_minima(model, scenario)
    assessments = [assess_sample(model, scenario, bits) for bits in minima.bitstrings]

    assert feasible_count == 37
    assert priority_27 == [("T1", "T2", "T5", "T6")]
    assert minima.examined_assignments == 2**18
    assert minima.nonpositive_infeasible_samples == 0
    assert minima.energy == -27
    assert minima.bitstrings == (optimum_bits,)
    assert len(assessments) == 1
    winner = assessments[0]
    assert winner.task_feasible is True
    assert winner.equality_satisfied is True
    assert winner.selected_task_ids == ("T1", "T2", "T5", "T6")
    assert winner.priority == 27
    assert (winner.used.energy, winner.used.storage, winner.used.downlink) == (9, 10, 10)
    assert winner.slack == SlackValues(1, 0, 0)
    assert winner.qubo_energy == -winner.priority + winner.weighted_penalty


def test_search_refuses_more_than_18_logical_qubits() -> None:
    scenario = load_scenario(FIXTURE)
    model = build_qubo(scenario, PENALTIES)
    too_wide = type(model)(
        variable_names=model.variable_names,
        linear=model.linear,
        quadratic=model.quadratic,
        constant=model.constant,
        lambda_by_constraint=model.lambda_by_constraint,
        bit_layout=model.bit_layout,
        n_task_bits=model.n_task_bits,
        n_slack_bits=model.n_slack_bits,
        n_logical_qubits=19,
        scenario_hash=model.scenario_hash,
    )

    with pytest.raises(EncodingError, match="at most 18 logical qubits, got 19"):
        find_qubo_minima(too_wide, scenario)


def test_assessment_rejects_a_different_scenario() -> None:
    scenario = load_scenario(FIXTURE)
    model = build_qubo(scenario, PENALTIES)
    other = type(scenario)(
        schema_version=scenario.schema_version,
        scenario_id="different",
        description=scenario.description,
        budgets=scenario.budgets,
        tasks=scenario.tasks,
        reference=scenario.reference,
    )

    with pytest.raises(EncodingError, match="does not match the QUBO instance"):
        assess_sample(model, other, [0] * 18)
