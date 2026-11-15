"""Shot-record accounting without a simulator."""

from __future__ import annotations

import sys

import pytest

from spaceops_quantum.domain import Resources, Scenario, Task
from spaceops_quantum.encoding import build_qubo
from spaceops_quantum.quantum import (
    BackendSample,
    SampledRecordError,
    build_sampled_record,
)

_PENALTIES = {"energy": 6, "storage": 0, "downlink": 0}


def _scenario() -> Scenario:
    return Scenario(
        schema_version=1,
        scenario_id="sampled-two-tasks",
        description="two tasks sharing one energy unit",
        budgets=Resources(1, 0, 0),
        tasks=(
            Task("A", priority=3, energy=1, storage=0, downlink=0),
            Task("B", priority=2, energy=1, storage=0, downlink=0),
        ),
    )


def _sample(bits: tuple[int, ...], count: int, shots: int) -> BackendSample:
    return BackendSample(bits=bits, probability=count / shots, count=count)


def test_record_keeps_counts_and_the_feasible_priority() -> None:
    scenario = _scenario()
    qubo = build_qubo(scenario, _PENALTIES)
    shots = 4
    record = build_sampled_record(
        scenario,
        qubo,
        (
            _sample((1, 0, 0), 1, shots),
            _sample((0, 0, 0), 1, shots),
            _sample((1, 1, 0), 2, shots),
        ),
        p=1,
        seed=3,
        shots=shots,
        backend="aer-sampled",
        parameters=(0.2, 0.3),
        versions=(("qiskit", "2.4.1"),),
    )
    assert record.shots == 4
    assert sum(item.count for item in record.samples) == 4
    assert [item.probability for item in record.samples] == [0.25, 0.25, 0.5]
    assert record.best_feasible_priority == 3
    assert record.best_feasible_task_ids == ("A",)
    assert record.feasibility_rate == 0.5
    assert record.sampled_optimum_probability == 0.25
    assert record.approx_ratio == 1
    assert record.relative_gap == 0
    infeasible = next(item for item in record.samples if item.bits == (1, 1, 0))
    assert infeasible.assessment.task_feasible is False
    assert infeasible.assessment.priority == 5
    assert "qiskit" not in sys.modules


def test_zero_feasible_shots_leave_the_best_empty() -> None:
    scenario = _scenario()
    qubo = build_qubo(scenario, _PENALTIES)
    shots = 4
    record = build_sampled_record(
        scenario,
        qubo,
        (_sample((1, 1, 0), shots, shots),),
        p=1,
        seed=0,
        shots=shots,
        backend="aer-sampled",
        parameters=(0.0, 0.0),
        versions=(),
    )
    assert record.best_feasible_priority is None
    assert record.best_feasible_task_ids is None
    assert record.feasibility_rate == 0
    assert record.sampled_optimum_probability == 0
    assert record.approx_ratio is None
    assert record.relative_gap is None
    assert record.samples[0].assessment.priority == 5
    assert record.samples[0].assessment.task_feasible is False


def test_counts_must_match_the_shot_budget() -> None:
    scenario = _scenario()
    qubo = build_qubo(scenario, _PENALTIES)
    with pytest.raises(SampledRecordError, match="counts sum"):
        build_sampled_record(
            scenario,
            qubo,
            (_sample((0, 0, 0), 3, 4),),
            p=1,
            seed=0,
            shots=4,
            backend="aer-sampled",
            parameters=(0.0, 0.0),
            versions=(),
        )
