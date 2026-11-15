"""Acceptance tests for the T04 exhaustive oracle."""

from __future__ import annotations

import sys
from pathlib import Path

from spaceops_quantum.classical import solve_exact
from spaceops_quantum.domain import (
    Resources,
    Scenario,
    SolutionEvaluation,
    Task,
    evaluate_solution,
    load_scenario,
    parse_scenario,
)

FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"


def _scenario(
    tasks: tuple[Task, ...],
    budgets: tuple[int, int, int] = (10, 10, 10),
    scenario_id: str = "exact",
) -> Scenario:
    return Scenario(
        schema_version=1,
        scenario_id=scenario_id,
        description="exact-solver fixture",
        budgets=Resources(*budgets),
        tasks=tasks,
    )


def test_fixture_optimum_is_27_with_37_feasible_subsets() -> None:
    result = solve_exact(load_scenario(FIXTURE))

    assert result.method == "exact"
    assert result.scenario_id == "eo-six-tasks-v1"
    assert result.examined_subsets == 64
    assert result.total_subsets == 64
    assert result.feasible_subsets == 37
    assert result.solution.selected_task_ids == ("T1", "T2", "T5", "T6")
    assert result.solution.bit_vector == (1, 1, 0, 0, 1, 1)
    assert result.solution.priority == 27
    assert result.solution.used == Resources(9, 10, 10)
    assert result.solution.feasible is True
    assert "qiskit" not in sys.modules
    assert "qiskit_aer" not in sys.modules


def test_repeated_solves_are_identical() -> None:
    scenario = load_scenario(FIXTURE)

    assert solve_exact(scenario) == solve_exact(scenario)


def test_tie_prefers_lexicographically_smaller_task_ids() -> None:
    scenario = _scenario(
        (
            Task("A", priority=2, energy=1, storage=0, downlink=0),
            Task("B", priority=2, energy=1, storage=0, downlink=0),
            Task("C", priority=4, energy=2, storage=0, downlink=0),
        ),
        (2, 0, 0),
    )

    result = solve_exact(scenario)

    assert result.solution.priority == 4
    assert result.solution.selected_task_ids == ("A", "B")
    assert result.solution.bit_vector == (1, 1, 0)
    assert result.feasible_subsets == 5


def test_infeasible_high_priority_loses_to_a_feasible_task() -> None:
    scenario = _scenario(
        (
            Task("huge", priority=100, energy=9, storage=0, downlink=0),
            Task("fit", priority=3, energy=1, storage=0, downlink=0),
        ),
        (1, 0, 0),
    )

    result = solve_exact(scenario)

    assert result.examined_subsets == 4
    assert result.feasible_subsets == 2
    assert result.solution.selected_task_ids == ("fit",)
    assert result.solution.priority == 3
    assert result.solution.used == Resources(1, 0, 0)


def test_zero_cost_tasks_are_all_selected() -> None:
    scenario = _scenario(
        (
            Task("Z1", priority=2, energy=0, storage=0, downlink=0),
            Task("Z2", priority=3, energy=0, storage=0, downlink=0),
        ),
        (0, 0, 0),
    )

    result = solve_exact(scenario)

    assert result.solution.selected_task_ids == ("Z1", "Z2")
    assert result.solution.priority == 5
    assert result.solution.used == Resources(0, 0, 0)
    assert result.feasible_subsets == 4


def test_empty_task_list_examines_one_empty_subset() -> None:
    result = solve_exact(_scenario((), (0, 0, 0), scenario_id="empty"))

    assert result.examined_subsets == 1
    assert result.feasible_subsets == 1
    assert result.solution.selected_task_ids == ()
    assert result.solution.priority == 0
    assert result.solution.bit_vector == ()


def test_reference_block_does_not_supply_the_optimum() -> None:
    scenario = parse_scenario(
        {
            "schema_version": 1,
            "scenario_id": "lying-reference",
            "description": "reference must not replace enumeration",
            "budgets": {"energy": 5, "storage": 5, "downlink": 5},
            "tasks": [
                {"id": "A", "priority": 4, "energy": 1, "storage": 0, "downlink": 0},
                {"id": "B", "priority": 5, "energy": 1, "storage": 0, "downlink": 0},
            ],
            "reference": {
                "source": "deliberately-wrong",
                "selected_task_ids": ["A"],
                "optimal_priority": 1,
                "used": {"energy": 1, "storage": 0, "downlink": 0},
                "feasible_subsets": 1,
                "total_subsets": 2,
            },
        }
    )

    result = solve_exact(scenario)

    assert result.solution.selected_task_ids == ("A", "B")
    assert result.solution.priority == 9
    assert result.feasible_subsets == 4
    assert scenario.reference is not None
    assert result.solution.priority != scenario.reference.optimal_priority


def test_counts_match_an_independent_evaluator_scan() -> None:
    scenario = _scenario(
        (
            Task("A", priority=3, energy=2, storage=1, downlink=0),
            Task("B", priority=3, energy=2, storage=0, downlink=1),
            Task("C", priority=4, energy=2, storage=1, downlink=1),
        ),
        (4, 1, 1),
    )
    feasible: list[SolutionEvaluation] = []
    n_tasks = len(scenario.tasks)
    for mask in range(1 << n_tasks):
        bits = [(mask >> index) & 1 for index in range(n_tasks)]
        evaluation = evaluate_solution(scenario, bits)
        if evaluation.feasible:
            feasible.append(evaluation)
    expected = min(
        (item for item in feasible if item.priority == max(item.priority for item in feasible)),
        key=lambda item: item.selected_task_ids,
    )

    result = solve_exact(scenario)

    assert result.examined_subsets == 1 << n_tasks
    assert result.feasible_subsets == len(feasible)
    assert result.solution.selected_task_ids == expected.selected_task_ids
    assert result.solution == evaluate_solution(scenario, result.solution.bit_vector)
