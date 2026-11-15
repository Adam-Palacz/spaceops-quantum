"""Immutable scenario models for resource-constrained task selection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Resources:
    """Non-negative integer energy, storage and downlink quantities."""

    energy: int
    storage: int
    downlink: int


@dataclass(frozen=True, slots=True)
class Task:
    """One candidate observation task."""

    id: str
    priority: int
    energy: int
    storage: int
    downlink: int


@dataclass(frozen=True, slots=True)
class ScenarioReference:
    """Documented classical reference stored beside a scenario.

    These fields are loaded and type-checked. They are not recomputed here.
    """

    source: str
    selected_task_ids: tuple[str, ...]
    optimal_priority: int
    used: Resources
    feasible_subsets: int
    total_subsets: int


@dataclass(frozen=True, slots=True)
class ResourceViolations:
    """How far a selection exceeds each budget.

    Zero means that resource constraint is satisfied. The constraint is
    ``used <= budget``.
    """

    energy: int
    storage: int
    downlink: int


@dataclass(frozen=True, slots=True)
class SolutionEvaluation:
    """Original-constraint score of one task subset.

    Priority and resource use are always computed from the selected tasks.
    An infeasible subset keeps those totals and sets ``feasible`` to false.
    """

    scenario_id: str
    selected_task_ids: tuple[str, ...]
    bit_vector: tuple[int, ...]
    priority: int
    used: Resources
    feasible: bool
    violations: ResourceViolations


@dataclass(frozen=True, slots=True)
class Scenario:
    """Validated task-selection instance."""

    schema_version: int
    scenario_id: str
    description: str
    budgets: Resources
    tasks: tuple[Task, ...]
    reference: ScenarioReference | None = None
