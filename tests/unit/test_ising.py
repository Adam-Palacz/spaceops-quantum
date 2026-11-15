"""Ising conversion keeps the QUBO energy, including the constant."""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import pytest

from spaceops_quantum.domain import Resources, Scenario, Task, load_scenario
from spaceops_quantum.encoding import (
    ISING_CONVENTION,
    EncodingError,
    SlackValues,
    bits_to_spins,
    build_qubo,
    encode_assignment,
    spins_to_bits,
    to_ising,
)

FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"


def _scenario() -> Scenario:
    return Scenario(
        schema_version=1,
        scenario_id="ising-hand",
        description="hand Ising expansion",
        budgets=Resources(1, 0, 0),
        tasks=(Task("A", priority=3, energy=1, storage=0, downlink=0),),
    )


def test_hand_expansion_matches_every_assignment_including_the_constant() -> None:
    qubo = build_qubo(_scenario(), {"energy": 2, "storage": 0, "downlink": 0})
    ising = to_ising(qubo)

    assert ising.convention == ISING_CONVENTION
    assert ising.variable_names == qubo.variable_names == ("x_A", "e_s0")
    assert ising.constant.numerator == -1
    assert ising.constant.denominator == 2
    assert ising.linear == (("x_A", ising.linear[0][1]), ("e_s0", ising.linear[1][1]))
    assert ising.linear[0][1] == Fraction(-3, 2)
    assert ising.linear[1][1] == 0
    assert ising.quadratic == (("x_A", "e_s0", Fraction(1)),)
    for bits in ((0, 0), (1, 0), (0, 1), (1, 1)):
        spins = bits_to_spins(bits)
        assert ising.evaluate(spins) == qubo.evaluate(bits)
        assert spins_to_bits(spins) == bits
    without_constant = ising.evaluate((-1, -1)) - ising.constant
    assert without_constant != qubo.evaluate((0, 0))
    assert without_constant + ising.constant == qubo.evaluate((0, 0))
    assert "qiskit" not in sys.modules


def test_spin_plus_one_means_the_bit_is_selected() -> None:
    assert bits_to_spins((1, 0)) == (1, -1)
    assert spins_to_bits((1, -1)) == (1, 0)


def test_tiny_instance_matches_on_every_bitstring() -> None:
    scenario = Scenario(
        schema_version=1,
        scenario_id="ising-tiny",
        description="five logical variables",
        budgets=Resources(1, 1, 1),
        tasks=(
            Task("A", priority=4, energy=1, storage=1, downlink=0),
            Task("B", priority=3, energy=1, storage=0, downlink=1),
        ),
    )
    qubo = build_qubo(scenario, {"energy": 5, "storage": 3, "downlink": 2})
    ising = to_ising(qubo)

    assert ising.n_logical_qubits == 5
    assert ising.variable_names == qubo.variable_names
    for mask in range(1 << qubo.n_logical_qubits):
        bits = tuple((mask >> index) & 1 for index in range(qubo.n_logical_qubits))
        assert ising.evaluate(bits_to_spins(bits)) == qubo.evaluate(bits)


def test_fixture_samples_match_including_the_zero_assignment() -> None:
    scenario = load_scenario(FIXTURE)
    qubo = build_qubo(scenario, {"energy": 41, "storage": 41, "downlink": 41})
    ising = to_ising(qubo)
    samples = [
        tuple(0 for _ in range(18)),
        encode_assignment(qubo.bit_layout, [1, 1, 0, 0, 1, 1], SlackValues(1, 0, 0)),
        tuple([1, 1, 1, 1, 1, 1, *([0] * 12)]),
    ]
    samples.extend(
        tuple((mask >> index) & 1 for index in range(18)) for mask in range(0, 2**18, 2**12)
    )

    assert qubo.evaluate(samples[0]) == 12300
    assert ising.n_logical_qubits == 18
    assert ising.variable_names[0] == "x_T1"
    assert ising.variable_names[6] == "e_s0"
    for bits in samples:
        assert ising.evaluate(bits_to_spins(bits)) == qubo.evaluate(bits)


def test_invalid_spins_and_bits_are_rejected() -> None:
    qubo = build_qubo(_scenario(), {"energy": 2, "storage": 0, "downlink": 0})
    ising = to_ising(qubo)

    with pytest.raises(EncodingError, match=r"spins\[1\] must be -1 or \+1, got 0"):
        ising.evaluate((1, 0))
    with pytest.raises(EncodingError, match="got bool"):
        bits_to_spins((True, 0))
