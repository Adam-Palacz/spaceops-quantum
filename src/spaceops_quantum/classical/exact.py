"""Exhaustive classical oracle for task selection.

Every subset of ``scenario.tasks`` is scored with ``evaluate_solution``.
The chosen solution is the feasible subset with the greatest priority.
Equal priorities use the lexicographically smallest ``selected_task_ids``
tuple, in scenario task order. Task i is bit i, and the first task is the
least significant bit. Infeasible subsets are counted and never repaired.
"""

from __future__ import annotations

from dataclasses import dataclass

from spaceops_quantum.domain.evaluation import evaluate_solution
from spaceops_quantum.domain.models import Scenario, SolutionEvaluation


@dataclass(frozen=True, slots=True)
class ClassicalResult:
    """One deterministic classical solve.

    ``feasible_subsets`` and ``total_subsets`` are populated by exhaustive
    enumeration. A heuristic that does not enumerate leaves them as ``None``.
    """

    method: str
    scenario_id: str
    examined_subsets: int
    feasible_subsets: int | None
    total_subsets: int | None
    solution: SolutionEvaluation
    strategy: str | None = None
    seed: int | None = None


def solve_exact(scenario: Scenario) -> ClassicalResult:
    """Return the feasible optimum and the subset counts."""
    n_tasks = len(scenario.tasks)
    total = 1 << n_tasks
    feasible_count = 0
    best: SolutionEvaluation | None = None
    for mask in range(total):
        evaluation = evaluate_solution(scenario, _bits_from_mask(n_tasks, mask))
        if not evaluation.feasible:
            continue
        feasible_count += 1
        if best is None or _prefer(evaluation, best):
            best = evaluation
    if best is None:
        raise RuntimeError(
            f"scenario {scenario.scenario_id!r} has no feasible subset; "
            "non-negative budgets always admit the empty selection"
        )
    return ClassicalResult(
        method="exact",
        scenario_id=scenario.scenario_id,
        examined_subsets=total,
        feasible_subsets=feasible_count,
        total_subsets=total,
        solution=best,
    )


def _bits_from_mask(n_tasks: int, mask: int) -> list[int]:
    return [(mask >> index) & 1 for index in range(n_tasks)]


def _prefer(candidate: SolutionEvaluation, incumbent: SolutionEvaluation) -> bool:
    if candidate.priority != incumbent.priority:
        return candidate.priority > incumbent.priority
    return candidate.selected_task_ids < incumbent.selected_task_ids
