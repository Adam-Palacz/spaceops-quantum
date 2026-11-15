"""Encode/decode tests for the T06 logical bit layout."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from spaceops_quantum.domain import Resources, Scenario, Task, evaluate_solution, load_scenario
from spaceops_quantum.encoding import (
    EncodingError,
    SlackValues,
    allocate_layout,
    decode_sample,
    encode_assignment,
    logical_bits_from_qiskit_bitstring,
    qiskit_bitstring_from_logical_bits,
    slack_bit_count,
)

FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"


def _scenario(
    tasks: tuple[Task, ...],
    budgets: tuple[int, int, int],
    scenario_id: str = "layout",
) -> Scenario:
    return Scenario(
        schema_version=1,
        scenario_id=scenario_id,
        description="bit-layout fixture",
        budgets=Resources(*budgets),
        tasks=tasks,
    )


def test_slack_width_follows_ceil_log2_of_budget_plus_one() -> None:
    assert [(budget, slack_bit_count(budget)) for budget in (0, 1, 2, 3, 10, 15, 16)] == [
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 2),
        (10, 4),
        (15, 4),
        (16, 5),
    ]


def test_fixture_allocates_18_logical_variables() -> None:
    layout = allocate_layout(load_scenario(FIXTURE))

    assert layout.n_task_bits == 6
    assert layout.n_slack_bits == 12
    assert layout.n_logical_qubits == 18
    assert layout.variable_names == (
        "x_T1",
        "x_T2",
        "x_T3",
        "x_T4",
        "x_T5",
        "x_T6",
        "e_s0",
        "e_s1",
        "e_s2",
        "e_s3",
        "m_s0",
        "m_s1",
        "m_s2",
        "m_s3",
        "d_s0",
        "d_s1",
        "d_s2",
        "d_s3",
    )
    assert [register.n_bits for register in layout.registers] == [4, 4, 4]
    assert [variable.index for variable in layout.variables] == list(range(18))
    assert "qiskit" not in sys.modules
    assert "qiskit_aer" not in sys.modules


def test_eight_tasks_with_the_same_budgets_use_20_logical_qubits() -> None:
    tasks = tuple(
        Task(f"T{number}", priority=1, energy=0, storage=0, downlink=0) for number in range(1, 9)
    )

    layout = allocate_layout(_scenario(tasks, (10, 10, 10), scenario_id="eight"))

    assert layout.n_task_bits == 8
    assert layout.n_slack_bits == 12
    assert layout.n_logical_qubits == 20


def test_registers_use_each_budget_width() -> None:
    scenario = _scenario((Task("A", priority=1, energy=0, storage=0, downlink=0),), (10, 1, 0))

    layout = allocate_layout(scenario)

    assert [(register.resource, register.n_bits) for register in layout.registers] == [
        ("energy", 4),
        ("storage", 1),
        ("downlink", 0),
    ]
    assert layout.variable_names == ("x_A", "e_s0", "e_s1", "e_s2", "e_s3", "m_s0")
    assert layout.n_logical_qubits == 6


def test_task_bit_order_follows_the_scenario_not_the_alphabet() -> None:
    scenario = _scenario(
        (
            Task("Z", priority=1, energy=0, storage=0, downlink=0),
            Task("A", priority=1, energy=0, storage=0, downlink=0),
        ),
        (0, 0, 0),
    )

    layout = allocate_layout(scenario)

    assert layout.variable_names == ("x_Z", "x_A")
    assert layout.n_logical_qubits == 2


def test_optimum_slack_roundtrip_uses_the_original_budgets() -> None:
    scenario = load_scenario(FIXTURE)
    evaluation = evaluate_solution(scenario, [1, 1, 0, 0, 1, 1])
    slack = SlackValues(
        energy=scenario.budgets.energy - evaluation.used.energy,
        storage=scenario.budgets.storage - evaluation.used.storage,
        downlink=scenario.budgets.downlink - evaluation.used.downlink,
    )
    layout = allocate_layout(scenario)

    encoded = encode_assignment(layout, evaluation.bit_vector, slack)
    decoded = decode_sample(encoded, layout)

    assert evaluation.used == Resources(9, 10, 10)
    assert slack == SlackValues(1, 0, 0)
    assert encoded[6:10] == (1, 0, 0, 0)
    assert decoded.task_bits == (1, 1, 0, 0, 1, 1)
    assert decoded.slack_values == slack
    assert len(encoded) == 18


def test_slack_ten_sets_bits_one_and_three() -> None:
    scenario = _scenario((Task("A", priority=1, energy=0, storage=0, downlink=0),), (10, 10, 10))
    layout = allocate_layout(scenario)

    encoded = encode_assignment(layout, [0], SlackValues(10, 0, 0))

    assert encoded[1:5] == (0, 1, 0, 1)
    assert decode_sample(encoded, layout).slack_values.energy == 10


@pytest.mark.parametrize("value", range(16))
def test_every_representable_slack_roundtrips(value: int) -> None:
    scenario = _scenario((Task("A", priority=1, energy=0, storage=0, downlink=0),), (10, 1, 0))
    layout = allocate_layout(scenario)
    storage = value % 2

    encoded = encode_assignment(layout, [1], SlackValues(value, storage, 0))
    decoded = decode_sample(encoded, layout)

    assert decoded.task_bits == (1,)
    assert decoded.slack_values == SlackValues(value, storage, 0)


def test_slack_beyond_the_register_is_rejected() -> None:
    scenario = _scenario((Task("A", priority=1, energy=0, storage=0, downlink=0),), (10, 0, 0))
    layout = allocate_layout(scenario)

    with pytest.raises(EncodingError, match="energy slack 16 does not fit in 4 bits"):
        encode_assignment(layout, [0], SlackValues(16, 0, 0))
    with pytest.raises(EncodingError, match="storage slack 1 does not fit in 0 bits"):
        encode_assignment(layout, [0], SlackValues(0, 1, 0))


def test_qiskit_string_keeps_qubit_zero_on_the_right() -> None:
    logical = (0, 1, 1)

    rendered = qiskit_bitstring_from_logical_bits(logical)

    assert rendered == "110"
    assert logical_bits_from_qiskit_bitstring(rendered) == logical
    assert logical_bits_from_qiskit_bitstring("10") == (0, 1)


def test_decode_rejects_a_raw_qiskit_string() -> None:
    layout = allocate_layout(
        _scenario((Task("A", priority=1, energy=0, storage=0, downlink=0),), (1, 0, 0))
    )

    with pytest.raises(EncodingError, match="logical_bits_from_qiskit_bitstring"):
        decode_sample("10", layout)


def test_qiskit_string_decodes_after_the_explicit_reversal() -> None:
    scenario = load_scenario(FIXTURE)
    layout = allocate_layout(scenario)
    logical = encode_assignment(layout, [1, 1, 0, 0, 1, 1], SlackValues(1, 0, 0))
    displayed = qiskit_bitstring_from_logical_bits(logical)

    decoded = decode_sample(logical_bits_from_qiskit_bitstring(displayed), layout)

    assert decoded.task_bits == (1, 1, 0, 0, 1, 1)
    assert decoded.slack_values == SlackValues(1, 0, 0)


def test_invalid_logical_bits_are_rejected() -> None:
    layout = allocate_layout(
        _scenario((Task("A", priority=1, energy=0, storage=0, downlink=0),), (1, 0, 0))
    )

    with pytest.raises(EncodingError, match="expected 2 logical bits, got 1"):
        decode_sample([0], layout)
    with pytest.raises(EncodingError, match=r"logical bits\[1\] must be 0 or 1, got 2"):
        decode_sample([0, 2], layout)
    with pytest.raises(EncodingError, match="got bool"):
        decode_sample([0, True], layout)
