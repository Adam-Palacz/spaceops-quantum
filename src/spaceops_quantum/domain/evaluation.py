"""Independent feasibility and objective evaluation.

This module uses only the original task costs and budgets. It does not read
the scenario reference block and it does not import Qiskit or QUBO code.
"""

from __future__ import annotations

from collections.abc import Iterable

from spaceops_quantum.domain.models import (
    Resources,
    ResourceViolations,
    Scenario,
    SolutionEvaluation,
)


class SolutionEvaluationError(ValueError):
    """The selection bits are not a valid task-sized 0/1 vector."""


def evaluate_solution(
    scenario: Scenario,
    selected_bits: Iterable[int],
) -> SolutionEvaluation:
    """Score one task subset against the original budgets.

    ``selected_bits`` follows ``scenario.tasks`` order. A 1 selects that task.
    Infeasible subsets are returned as-is; bits are never repaired.
    """
    bits = _validate_bits(scenario, selected_bits)
    selected_ids: list[str] = []
    priority = 0
    energy = 0
    storage = 0
    downlink = 0
    for index, task in enumerate(scenario.tasks):
        if bits[index] == 0:
            continue
        selected_ids.append(task.id)
        priority += task.priority
        energy += task.energy
        storage += task.storage
        downlink += task.downlink
    violations = ResourceViolations(
        energy=max(0, energy - scenario.budgets.energy),
        storage=max(0, storage - scenario.budgets.storage),
        downlink=max(0, downlink - scenario.budgets.downlink),
    )
    return SolutionEvaluation(
        scenario_id=scenario.scenario_id,
        selected_task_ids=tuple(selected_ids),
        bit_vector=bits,
        priority=priority,
        used=Resources(energy=energy, storage=storage, downlink=downlink),
        feasible=violations == ResourceViolations(0, 0, 0),
        violations=violations,
    )


def _validate_bits(scenario: Scenario, selected_bits: Iterable[int]) -> tuple[int, ...]:
    if isinstance(selected_bits, (str, bytes, bytearray)):
        raise SolutionEvaluationError(
            "expected a sequence of 0/1 task bits, got "
            f"{type(selected_bits).__name__}"
        )
    try:
        raw = list(selected_bits)
    except TypeError as exc:
        raise SolutionEvaluationError(
            "expected a sequence of 0/1 task bits, got "
            f"{type(selected_bits).__name__}"
        ) from exc
    expected = len(scenario.tasks)
    if len(raw) != expected:
        names = ", ".join(task.id for task in scenario.tasks)
        raise SolutionEvaluationError(
            f"expected {expected} bits in task order [{names}], got {len(raw)}"
        )
    validated: list[int] = []
    for index, value in enumerate(raw):
        if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
            task_id = scenario.tasks[index].id
            raise SolutionEvaluationError(
                f"bit {index} (task {task_id}) must be 0 or 1, got {_bit_got(value)}"
            )
        validated.append(value)
    return tuple(validated)


def _bit_got(value: object) -> str:
    if isinstance(value, bool):
        return "bool"
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    return type(value).__name__
