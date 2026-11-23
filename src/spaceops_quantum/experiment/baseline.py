"""Analytical comparisons that do not rerun QAOA.

``p_uniform`` is the share of task subsets that are feasible and optimal.
Slack bits are not part of that draw. ``p_ground_state`` is the probability
of bitstrings that achieve the enumerated QUBO minimum, so the slack
assignment has to be one of those minima.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from spaceops_quantum.classical import solve_exact
from spaceops_quantum.domain.evaluation import evaluate_solution
from spaceops_quantum.domain.models import Scenario


@dataclass(frozen=True, slots=True)
class UniformTaskBaseline:
    """Uniform draw over the 2^n task subsets."""

    task_subsets: int
    optimal_task_subsets: int
    feasible_task_subsets: int
    probability: Fraction
    feasible_probability: Fraction


def uniform_task_baseline(scenario: Scenario) -> UniformTaskBaseline:
    """Count feasible optimal task subsets and divide by 2^n."""

    optimum = solve_exact(scenario).solution.priority
    width = len(scenario.tasks)
    total = 1 << width
    winners = 0
    feasible = 0
    for mask in range(total):
        bits = tuple((mask >> index) & 1 for index in range(width))
        evaluation = evaluate_solution(scenario, bits)
        if not evaluation.feasible:
            continue
        feasible += 1
        if evaluation.priority == optimum:
            winners += 1
    return UniformTaskBaseline(
        total,
        winners,
        feasible,
        Fraction(winners, total),
        Fraction(winners, feasible),
    )


def probability_on_bitstrings(
    rows: Sequence[tuple[tuple[int, ...], float]],
    targets: set[tuple[int, ...]],
) -> float:
    """Sum the probability of rows whose logical bits are in ``targets``."""

    return sum(probability for bits, probability in rows if bits in targets)
