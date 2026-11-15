"""QUBO expansion against the direct penalty, including the constant offset."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from spaceops_quantum.domain import (
    Resources,
    Scenario,
    Task,
    evaluate_solution,
    load_scenario,
    parse_scenario,
)
from spaceops_quantum.encoding import (
    QUBO_CONVENTION,
    EncodingError,
    SlackValues,
    build_qubo,
    decode_sample,
    encode_assignment,
    scenario_hash,
)
from spaceops_quantum.encoding.bit_mapping import BitLayout

FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"


def _scenario(
    tasks: tuple[Task, ...],
    budgets: tuple[int, int, int],
    scenario_id: str = "qubo",
) -> Scenario:
    return Scenario(
        schema_version=1,
        scenario_id=scenario_id,
        description="qubo fixture",
        budgets=Resources(*budgets),
        tasks=tasks,
    )


def _direct_energy(
    scenario: Scenario,
    penalties: dict[str, int],
    bits: list[int],
    layout: BitLayout,
) -> int:
    decoded = decode_sample(bits, layout)
    total = 0
    used = {"energy": 0, "storage": 0, "downlink": 0}
    for task, bit in zip(scenario.tasks, decoded.task_bits, strict=True):
        total -= task.priority * bit
        if bit:
            used["energy"] += task.energy
            used["storage"] += task.storage
            used["downlink"] += task.downlink
    slack = decoded.slack_values
    for resource in ("energy", "storage", "downlink"):
        residual = used[resource] + getattr(slack, resource) - getattr(scenario.budgets, resource)
        total += penalties[resource] * residual * residual
    return total


def test_hand_expanded_coefficients_match_the_four_assignments() -> None:
    scenario = _scenario((Task("A", priority=3, energy=1, storage=0, downlink=0),), (1, 0, 0))
    penalties = {"energy": 2, "storage": 0, "downlink": 0}

    model = build_qubo(scenario, penalties)

    assert model.convention == QUBO_CONVENTION
    assert model.constant == 2
    assert model.linear == (("x_A", -5), ("e_s0", -2))
    assert model.quadratic == (("x_A", "e_s0", 4),)
    assert model.n_logical_qubits == 2
    assert [model.evaluate(bits) for bits in ((0, 0), (1, 0), (0, 1), (1, 1))] == [2, -3, 0, -1]
    assert "qiskit" not in sys.modules


def test_full_product_coefficient_is_not_the_halved_matrix_entry() -> None:
    scenario = _scenario((Task("A", priority=3, energy=1, storage=0, downlink=0),), (1, 0, 0))
    model = build_qubo(scenario, {"energy": 2, "storage": 0, "downlink": 0})
    halved = model.constant - 5 - 2 + 2

    assert model.quadratic[0][2] == 4
    assert model.evaluate((1, 1)) == -1
    assert halved != model.evaluate((1, 1))


def test_constant_offset_is_retained_separately() -> None:
    penalties = {"energy": 5, "storage": 3, "downlink": 2}
    scenario = _scenario(
        (
            Task("A", priority=4, energy=1, storage=1, downlink=0),
            Task("B", priority=3, energy=1, storage=0, downlink=1),
        ),
        (1, 1, 1),
    )

    model = build_qubo(scenario, penalties)
    zeros = [0] * model.n_logical_qubits

    assert model.constant == 10
    assert model.evaluate(zeros) == model.constant
    assert model.evaluate(zeros) == _direct_energy(scenario, penalties, zeros, model.bit_layout)


def test_expansion_matches_direct_penalty_on_every_tiny_bitstring() -> None:
    penalties = {"energy": 5, "storage": 3, "downlink": 2}
    scenario = _scenario(
        (
            Task("A", priority=4, energy=1, storage=1, downlink=0),
            Task("B", priority=3, energy=1, storage=0, downlink=1),
        ),
        (1, 1, 1),
    )
    model = build_qubo(scenario, penalties)

    assert model.n_task_bits == 2
    assert model.n_slack_bits == 3
    assert model.n_logical_qubits == 5
    for mask in range(1 << model.n_logical_qubits):
        bits = [(mask >> index) & 1 for index in range(model.n_logical_qubits)]
        direct = _direct_energy(scenario, penalties, bits, model.bit_layout)
        assert model.evaluate(bits) == direct


def test_zero_penalty_leaves_only_the_priority_term() -> None:
    scenario = _scenario((Task("A", priority=4, energy=2, storage=1, downlink=1),), (3, 3, 3))
    model = build_qubo(scenario, {"energy": 0, "storage": 0, "downlink": 0})

    assert model.constant == 0
    assert model.quadratic == ()
    assert model.linear[0] == ("x_A", -4)
    assert model.evaluate([1, *([0] * (model.n_logical_qubits - 1))]) == -4


def test_fixture_constant_and_sample_match_the_direct_square() -> None:
    scenario = load_scenario(FIXTURE)
    penalties = {"energy": 41, "storage": 41, "downlink": 41}
    model = build_qubo(scenario, penalties)
    evaluation = evaluate_solution(scenario, [1, 1, 0, 0, 1, 1])
    slack = SlackValues(
        energy=scenario.budgets.energy - evaluation.used.energy,
        storage=scenario.budgets.storage - evaluation.used.storage,
        downlink=scenario.budgets.downlink - evaluation.used.downlink,
    )
    optimum_bits = list(encode_assignment(model.bit_layout, evaluation.bit_vector, slack))
    infeasible_bits = [1] * model.n_task_bits + [0] * model.n_slack_bits

    assert model.n_logical_qubits == 18
    assert model.constant == 3 * 41 * 100
    assert model.evaluate([0] * 18) == model.constant
    assert slack == SlackValues(1, 0, 0)
    for bits in (optimum_bits, infeasible_bits):
        assert model.evaluate(bits) == _direct_energy(scenario, penalties, bits, model.bit_layout)


def test_scenario_hash_ignores_the_reference_block() -> None:
    base = {
        "schema_version": 1,
        "scenario_id": "hash-me",
        "description": "first description",
        "budgets": {"energy": 1, "storage": 1, "downlink": 1},
        "tasks": [{"id": "A", "priority": 2, "energy": 1, "storage": 0, "downlink": 0}],
    }
    other = parse_scenario({**base, "description": "different prose"})
    with_reference = parse_scenario(
        {
            **base,
            "reference": {
                "source": "wrong",
                "selected_task_ids": ["A"],
                "optimal_priority": 99,
                "used": {"energy": 0, "storage": 0, "downlink": 0},
                "feasible_subsets": 1,
                "total_subsets": 2,
            },
        }
    )
    changed = parse_scenario(
        {
            **base,
            "tasks": [{"id": "A", "priority": 3, "energy": 1, "storage": 0, "downlink": 0}],
        }
    )

    assert scenario_hash(parse_scenario(base)) == scenario_hash(other)
    assert scenario_hash(parse_scenario(base)) == scenario_hash(with_reference)
    assert scenario_hash(changed) != scenario_hash(parse_scenario(base))


def test_penalty_mapping_must_name_the_three_resources() -> None:
    scenario = _scenario((Task("A", priority=1, energy=0, storage=0, downlink=0),), (0, 0, 0))

    with pytest.raises(EncodingError, match="missing penalty fields: downlink"):
        build_qubo(scenario, {"energy": 1, "storage": 1})
    with pytest.raises(EncodingError, match="unknown penalty fields: orbit"):
        build_qubo(scenario, {"energy": 1, "storage": 1, "downlink": 1, "orbit": 1})
    with pytest.raises(EncodingError, match="lambda energy must be an integer >= 0"):
        build_qubo(scenario, {"energy": -1, "storage": 0, "downlink": 0})
