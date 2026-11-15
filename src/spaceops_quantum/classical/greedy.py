"""Deterministic greedy baseline for task selection.

Strategy ``resource_density`` ranks each task by

    priority / sum(cost_r / budget_r)

over energy, storage and downlink. A budget of zero contributes nothing when
the task cost is also zero, and makes the task unfit when the cost is positive.
Zero-cost tasks are ranked first. Equal density yields to higher priority,
then to the lexicographically smaller task id, then to the earlier scenario
index. A task is added only when the remaining budgets still hold it, so the
subset stays feasible. The seed is stored for provenance and does not change
this ranking.
"""

from __future__ import annotations

from fractions import Fraction

from spaceops_quantum.classical.exact import ClassicalResult
from spaceops_quantum.domain.evaluation import evaluate_solution
from spaceops_quantum.domain.models import Resources, Scenario, Task

RESOURCE_DENSITY = "resource_density"
SUPPORTED_STRATEGIES = frozenset({RESOURCE_DENSITY})


class GreedySolverError(ValueError):
    """The greedy request is not a supported deterministic strategy."""


def solve_greedy(
    scenario: Scenario,
    strategy: str = RESOURCE_DENSITY,
    seed: int = 0,
) -> ClassicalResult:
    """Build one feasible subset by resource-adjusted priority ranking."""
    _validate_request(strategy, seed)
    remaining = [
        scenario.budgets.energy,
        scenario.budgets.storage,
        scenario.budgets.downlink,
    ]
    selected: set[str] = set()
    ranked = sorted(
        enumerate(scenario.tasks),
        key=lambda item: _sort_key(item[1], item[0], scenario.budgets),
    )
    for _index, task in ranked:
        costs = (task.energy, task.storage, task.downlink)
        if any(cost > left for cost, left in zip(costs, remaining, strict=True)):
            continue
        selected.add(task.id)
        for position, cost in enumerate(costs):
            remaining[position] -= cost
    bits = [1 if task.id in selected else 0 for task in scenario.tasks]
    solution = evaluate_solution(scenario, bits)
    if not solution.feasible:
        raise RuntimeError(
            f"greedy subset for {scenario.scenario_id!r} failed the independent evaluator"
        )
    return ClassicalResult(
        method="greedy",
        scenario_id=scenario.scenario_id,
        examined_subsets=len(scenario.tasks),
        feasible_subsets=None,
        total_subsets=None,
        solution=solution,
        strategy=strategy,
        seed=seed,
    )


def _validate_request(strategy: str, seed: int) -> None:
    if strategy not in SUPPORTED_STRATEGIES:
        supported = ", ".join(sorted(SUPPORTED_STRATEGIES))
        raise GreedySolverError(f"unknown strategy {strategy!r}; supported: {supported}")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise GreedySolverError(f"seed must be an integer >= 0, got {seed!r}")


def _sort_key(
    task: Task,
    index: int,
    budgets: Resources,
) -> tuple[int, Fraction, int, str, int]:
    unfit = False
    weight = Fraction(0)
    for cost, budget in (
        (task.energy, budgets.energy),
        (task.storage, budgets.storage),
        (task.downlink, budgets.downlink),
    ):
        if budget == 0:
            if cost > 0:
                unfit = True
            continue
        weight += Fraction(cost, budget)
    if unfit:
        return (2, Fraction(0), -task.priority, task.id, index)
    if weight == 0:
        return (0, Fraction(0), -task.priority, task.id, index)
    density = Fraction(task.priority) / weight
    return (1, -density, -task.priority, task.id, index)
