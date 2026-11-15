"""Edge-case tests for the T03 independent constraint evaluator."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from spaceops_quantum.domain import (
    Resources,
    ResourceViolations,
    Scenario,
    SolutionEvaluationError,
    Task,
    evaluate_solution,
    load_scenario,
    parse_scenario,
)

FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"
_NO_VIOLATION = ResourceViolations(0, 0, 0)


def _scenario(
    tasks: tuple[Task, ...],
    budgets: tuple[int, int, int] = (10, 10, 10),
    scenario_id: str = "eval",
) -> Scenario:
    return Scenario(
        schema_version=1,
        scenario_id=scenario_id,
        description="evaluator fixture",
        budgets=Resources(*budgets),
        tasks=tasks,
    )


def test_golden_subset_matches_documented_objective() -> None:
    scenario = load_scenario(FIXTURE)

    result = evaluate_solution(scenario, [1, 1, 0, 0, 1, 1])

    assert result.scenario_id == "eo-six-tasks-v1"
    assert result.selected_task_ids == ("T1", "T2", "T5", "T6")
    assert result.bit_vector == (1, 1, 0, 0, 1, 1)
    assert result.priority == 27
    assert result.used == Resources(9, 10, 10)
    assert result.feasible is True
    assert result.violations == _NO_VIOLATION
    assert "qiskit" not in sys.modules
    assert "qiskit_aer" not in sys.modules


def test_empty_selection_is_feasible() -> None:
    scenario = load_scenario(FIXTURE)

    result = evaluate_solution(scenario, [0, 0, 0, 0, 0, 0])

    assert result.selected_task_ids == ()
    assert result.priority == 0
    assert result.used == Resources(0, 0, 0)
    assert result.feasible is True
    assert result.violations == _NO_VIOLATION


def test_selecting_every_fixture_task_keeps_priority_and_reports_excess() -> None:
    scenario = load_scenario(FIXTURE)

    result = evaluate_solution(scenario, [1, 1, 1, 1, 1, 1])

    assert result.selected_task_ids == ("T1", "T2", "T3", "T4", "T5", "T6")
    assert result.priority == 40
    assert result.used == Resources(17, 17, 17)
    assert result.feasible is False
    assert result.violations == ResourceViolations(7, 7, 7)


def test_exact_budget_is_feasible() -> None:
    scenario = _scenario((Task("A", priority=4, energy=2, storage=3, downlink=1),), (2, 3, 1))

    result = evaluate_solution(scenario, [1])

    assert result.priority == 4
    assert result.used == Resources(2, 3, 1)
    assert result.feasible is True
    assert result.violations == _NO_VIOLATION


def test_one_resource_violation_leaves_the_others_at_zero() -> None:
    scenario = _scenario(
        (
            Task("A", priority=4, energy=3, storage=1, downlink=1),
            Task("B", priority=5, energy=3, storage=1, downlink=1),
        ),
        (5, 5, 5),
    )

    result = evaluate_solution(scenario, [1, 1])

    assert result.selected_task_ids == ("A", "B")
    assert result.priority == 9
    assert result.used == Resources(6, 2, 2)
    assert result.feasible is False
    assert result.violations == ResourceViolations(1, 0, 0)


def test_zero_cost_task_is_feasible_on_a_zero_budget() -> None:
    scenario = _scenario(
        (
            Task("Z", priority=6, energy=0, storage=0, downlink=0),
            Task("C", priority=1, energy=2, storage=0, downlink=0),
        ),
        (0, 0, 0),
    )

    free = evaluate_solution(scenario, [1, 0])
    costly = evaluate_solution(scenario, [0, 1])
    both = evaluate_solution(scenario, [1, 1])

    assert free.priority == 6
    assert free.used == Resources(0, 0, 0)
    assert free.feasible is True
    assert costly.priority == 1
    assert costly.used == Resources(2, 0, 0)
    assert costly.feasible is False
    assert costly.violations == ResourceViolations(2, 0, 0)
    assert both.priority == 7
    assert both.feasible is False
    assert both.violations == ResourceViolations(2, 0, 0)


def test_selected_ids_follow_task_order() -> None:
    scenario = _scenario(
        (
            Task("low", priority=1, energy=0, storage=0, downlink=0),
            Task("high", priority=9, energy=0, storage=0, downlink=0),
        )
    )

    result = evaluate_solution(scenario, [0, 1])

    assert result.selected_task_ids == ("high",)
    assert result.priority == 9


def test_reference_block_is_not_used_as_the_objective() -> None:
    scenario = parse_scenario(
        {
            "schema_version": 1,
            "scenario_id": "lying-reference",
            "description": "reference must not override the tasks",
            "budgets": {"energy": 5, "storage": 5, "downlink": 5},
            "tasks": [
                {"id": "A", "priority": 3, "energy": 1, "storage": 1, "downlink": 1},
                {"id": "B", "priority": 4, "energy": 1, "storage": 1, "downlink": 1},
            ],
            "reference": {
                "source": "deliberately-wrong",
                "selected_task_ids": ["A"],
                "optimal_priority": 99,
                "used": {"energy": 9, "storage": 9, "downlink": 9},
                "feasible_subsets": 1,
                "total_subsets": 4,
            },
        }
    )

    result = evaluate_solution(scenario, [1, 1])

    assert result.priority == 7
    assert result.used == Resources(2, 2, 2)
    assert result.feasible is True
    assert scenario.reference is not None
    assert result.priority != scenario.reference.optimal_priority


def test_caller_can_mutate_the_input_after_evaluation() -> None:
    scenario = _scenario((Task("A", priority=2, energy=1, storage=0, downlink=0),))
    bits = [1]

    result = evaluate_solution(scenario, bits)
    bits[0] = 0

    assert result.bit_vector == (1,)
    assert result.priority == 2


def test_generator_bits_are_accepted() -> None:
    scenario = _scenario(
        (
            Task("A", priority=2, energy=1, storage=0, downlink=0),
            Task("B", priority=3, energy=1, storage=0, downlink=0),
        )
    )

    result = evaluate_solution(scenario, (bit for bit in (0, 1)))

    assert result.selected_task_ids == ("B",)
    assert result.priority == 3


@pytest.mark.parametrize(
    ("bits", "fragment"),
    [
        ([1], "expected 2 bits in task order [A, B], got 1"),
        ([1, 0, 1], "expected 2 bits in task order [A, B], got 3"),
        ([2, 0], "bit 0 (task A) must be 0 or 1, got 2"),
        ([True, 0], "bit 0 (task A) must be 0 or 1, got bool"),
        ([1, 1.0], "bit 1 (task B) must be 0 or 1, got float"),
        ([1, None], "bit 1 (task B) must be 0 or 1, got null"),
    ],
)
def test_invalid_bits_are_rejected(bits: list[object], fragment: str) -> None:
    scenario = _scenario(
        (
            Task("A", priority=1, energy=0, storage=0, downlink=0),
            Task("B", priority=1, energy=0, storage=0, downlink=0),
        )
    )

    with pytest.raises(SolutionEvaluationError) as exc_info:
        evaluate_solution(scenario, bits)  # type: ignore[arg-type]

    assert fragment in str(exc_info.value)


def test_bitstring_text_is_rejected() -> None:
    scenario = _scenario((Task("A", priority=1, energy=0, storage=0, downlink=0),))

    with pytest.raises(SolutionEvaluationError, match="got str"):
        evaluate_solution(scenario, "1")


def test_non_sequence_is_rejected() -> None:
    scenario = _scenario((Task("A", priority=1, energy=0, storage=0, downlink=0),))

    with pytest.raises(SolutionEvaluationError, match="got int"):
        evaluate_solution(scenario, 1)  # type: ignore[arg-type]
