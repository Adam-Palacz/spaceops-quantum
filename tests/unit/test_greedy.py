"""Deterministic feasible greedy baseline."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from spaceops_quantum.classical import GreedySolverError, solve_exact, solve_greedy
from spaceops_quantum.domain import Resources, Scenario, Task, load_scenario

FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"


def _scenario(
    tasks: tuple[Task, ...],
    budgets: tuple[int, int, int] = (10, 10, 10),
    scenario_id: str = "greedy",
) -> Scenario:
    return Scenario(
        schema_version=1,
        scenario_id=scenario_id,
        description="greedy fixture",
        budgets=Resources(*budgets),
        tasks=tasks,
    )


def test_fixture_greedy_is_feasible_and_happens_to_match_the_optimum() -> None:
    scenario = load_scenario(FIXTURE)

    result = solve_greedy(scenario, "resource_density", 0)

    assert result.method == "greedy"
    assert result.strategy == "resource_density"
    assert result.seed == 0
    assert result.examined_subsets == 6
    assert result.feasible_subsets is None
    assert result.total_subsets is None
    assert result.solution.selected_task_ids == ("T1", "T2", "T5", "T6")
    assert result.solution.priority == 27
    assert result.solution.used == Resources(9, 10, 10)
    assert result.solution.feasible is True
    assert "qiskit" not in sys.modules


def test_seed_is_recorded_without_changing_the_subset() -> None:
    scenario = load_scenario(FIXTURE)

    first = solve_greedy(scenario, seed=0)
    second = solve_greedy(scenario, seed=7)

    assert first.solution.selected_task_ids == second.solution.selected_task_ids
    assert first.seed == 0
    assert second.seed == 7


def test_greedy_can_miss_the_exact_optimum() -> None:
    scenario = _scenario(
        (
            Task("A", priority=6, energy=4, storage=0, downlink=0),
            Task("B", priority=5, energy=3, storage=0, downlink=0),
            Task("C", priority=5, energy=3, storage=0, downlink=0),
        ),
        (5, 0, 0),
    )

    greedy = solve_greedy(scenario)
    exact = solve_exact(scenario)

    assert greedy.solution.selected_task_ids == ("B",)
    assert greedy.solution.priority == 5
    assert greedy.solution.feasible is True
    assert exact.solution.selected_task_ids == ("A",)
    assert exact.solution.priority == 6
    assert greedy.solution.priority < exact.solution.priority


def test_equal_density_prefers_higher_priority() -> None:
    scenario = _scenario(
        (
            Task("A", priority=4, energy=2, storage=0, downlink=0),
            Task("B", priority=6, energy=3, storage=0, downlink=0),
        ),
        (3, 0, 0),
    )

    result = solve_greedy(scenario)

    assert result.solution.selected_task_ids == ("B",)
    assert result.solution.priority == 6


def test_equal_density_and_priority_prefers_smaller_task_id() -> None:
    scenario = _scenario(
        (
            Task("B", priority=4, energy=2, storage=0, downlink=0),
            Task("A", priority=4, energy=2, storage=0, downlink=0),
        ),
        (2, 0, 0),
    )

    result = solve_greedy(scenario)

    assert result.solution.selected_task_ids == ("A",)
    assert result.solution.bit_vector == (0, 1)


def test_zero_cost_task_is_kept_with_a_fitting_costly_task() -> None:
    scenario = _scenario(
        (
            Task("P", priority=4, energy=1, storage=0, downlink=0),
            Task("Z", priority=3, energy=0, storage=0, downlink=0),
        ),
        (1, 0, 0),
    )

    result = solve_greedy(scenario)

    assert result.solution.selected_task_ids == ("P", "Z")
    assert result.solution.priority == 7
    assert result.solution.feasible is True


def test_task_that_cannot_fit_is_skipped() -> None:
    scenario = _scenario(
        (
            Task("huge", priority=100, energy=9, storage=0, downlink=0),
            Task("fit", priority=2, energy=1, storage=0, downlink=0),
        ),
        (5, 0, 0),
    )

    result = solve_greedy(scenario)

    assert result.solution.selected_task_ids == ("fit",)
    assert result.solution.feasible is True


def test_unknown_strategy_and_bad_seed_are_rejected() -> None:
    scenario = _scenario((Task("A", priority=1, energy=0, storage=0, downlink=0),))

    with pytest.raises(GreedySolverError, match="unknown strategy 'random'"):
        solve_greedy(scenario, strategy="random")
    with pytest.raises(GreedySolverError, match="seed must be an integer >= 0"):
        solve_greedy(scenario, seed=-1)
    with pytest.raises(GreedySolverError, match="got True"):
        solve_greedy(scenario, seed=True)  # type: ignore[arg-type]
