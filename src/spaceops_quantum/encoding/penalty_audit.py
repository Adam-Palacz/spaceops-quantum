"""Penalty audit for a built QUBO.

A sample is a feasible task subset only when the original task budgets hold.
Slack bits are reported separately as an equality residual. Low QUBO energy
does not repair an infeasible task subset, and a broken slack equality does
not make a feasible subset infeasible. This module does not import Qiskit.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from spaceops_quantum.domain.evaluation import evaluate_solution
from spaceops_quantum.domain.models import Resources, ResourceViolations, Scenario
from spaceops_quantum.encoding.bit_mapping import EncodingError, SlackValues, decode_sample
from spaceops_quantum.encoding.qubo import QuboModel, scenario_hash

_MAX_EXHAUSTIVE_QUBITS = 18


@dataclass(frozen=True, slots=True)
class ConstraintResidual:
    """``used + slack - budget`` for each resource. Zero satisfies that equality."""

    energy: int
    storage: int
    downlink: int

    @property
    def squared_total(self) -> int:
        return self.energy**2 + self.storage**2 + self.downlink**2


@dataclass(frozen=True, slots=True)
class SampleAssessment:
    """Original-task evaluation plus the separate QUBO equality residual."""

    selected_task_ids: tuple[str, ...]
    task_bits: tuple[int, ...]
    priority: int
    used: Resources
    task_feasible: bool
    violations: ResourceViolations
    slack: SlackValues
    residual: ConstraintResidual
    weighted_penalty: int
    qubo_energy: int
    equality_satisfied: bool


@dataclass(frozen=True, slots=True)
class QuboMinimum:
    """Global minima of one QUBO found by enumerating every logical assignment."""

    energy: int
    examined_assignments: int
    bitstrings: tuple[tuple[int, ...], ...]
    nonpositive_infeasible_samples: int


def assess_sample(model: QuboModel, scenario: Scenario, bits: Sequence[int]) -> SampleAssessment:
    """Decode one logical assignment and keep task feasibility independent."""
    _require_same_instance(model, scenario)
    decoded = decode_sample(bits, model.bit_layout)
    evaluation = evaluate_solution(scenario, decoded.task_bits)
    residual = ConstraintResidual(
        energy=evaluation.used.energy + decoded.slack_values.energy - scenario.budgets.energy,
        storage=evaluation.used.storage + decoded.slack_values.storage - scenario.budgets.storage,
        downlink=(
            evaluation.used.downlink + decoded.slack_values.downlink - scenario.budgets.downlink
        ),
    )
    penalties = dict(model.lambda_by_constraint)
    weighted_penalty = (
        penalties["energy"] * residual.energy**2
        + penalties["storage"] * residual.storage**2
        + penalties["downlink"] * residual.downlink**2
    )
    return SampleAssessment(
        selected_task_ids=evaluation.selected_task_ids,
        task_bits=decoded.task_bits,
        priority=evaluation.priority,
        used=evaluation.used,
        task_feasible=evaluation.feasible,
        violations=evaluation.violations,
        slack=decoded.slack_values,
        residual=residual,
        weighted_penalty=weighted_penalty,
        qubo_energy=model.evaluate(bits),
        equality_satisfied=residual.squared_total == 0,
    )


def find_qubo_minima(model: QuboModel, scenario: Scenario) -> QuboMinimum:
    """Enumerate every logical assignment and return the minimum-energy set.

    Bit ``i`` of the internal mask is logical variable ``i``. Strings displayed
    by Qiskit are not accepted here. The search stops above 18 logical qubits.
    """
    _require_same_instance(model, scenario)
    n_qubits = model.n_logical_qubits
    if n_qubits > _MAX_EXHAUSTIVE_QUBITS:
        raise EncodingError(
            f"exhaustive QUBO search supports at most {_MAX_EXHAUSTIVE_QUBITS} "
            f"logical qubits, got {n_qubits}"
        )
    index = {name: position for position, name in enumerate(model.variable_names)}
    linear_terms = tuple(
        (index[name], coefficient) for name, coefficient in model.linear if coefficient != 0
    )
    pair_terms = tuple(
        (index[left], index[right], coefficient)
        for left, right, coefficient in model.quadratic
        if coefficient != 0
    )
    constant = model.constant
    n_tasks = model.n_task_bits
    task_energy = tuple(task.energy for task in scenario.tasks)
    task_storage = tuple(task.storage for task in scenario.tasks)
    task_downlink = tuple(task.downlink for task in scenario.tasks)
    budget_energy = scenario.budgets.energy
    budget_storage = scenario.budgets.storage
    budget_downlink = scenario.budgets.downlink
    best: int | None = None
    winners: list[int] = []
    nonpositive_infeasible = 0
    examined = 1 << n_qubits
    for mask in range(examined):
        energy = constant
        for variable, coefficient in linear_terms:
            if (mask >> variable) & 1:
                energy += coefficient
        for left, right, coefficient in pair_terms:
            if (mask >> left) & 1 and (mask >> right) & 1:
                energy += coefficient
        if best is None or energy < best:
            best = energy
            winners = [mask]
        elif energy == best:
            winners.append(mask)
        if energy <= 0 and _task_bits_infeasible(
            mask,
            n_tasks,
            task_energy,
            task_storage,
            task_downlink,
            budget_energy,
            budget_storage,
            budget_downlink,
        ):
            nonpositive_infeasible += 1
    if best is None:
        raise EncodingError("QUBO search examined no assignments")
    return QuboMinimum(
        energy=best,
        examined_assignments=examined,
        bitstrings=tuple(_bits_from_mask(n_qubits, mask) for mask in winners),
        nonpositive_infeasible_samples=nonpositive_infeasible,
    )


def _require_same_instance(model: QuboModel, scenario: Scenario) -> None:
    if scenario_hash(scenario) != model.scenario_hash:
        raise EncodingError("scenario does not match the QUBO instance")


def _task_bits_infeasible(
    mask: int,
    n_tasks: int,
    task_energy: tuple[int, ...],
    task_storage: tuple[int, ...],
    task_downlink: tuple[int, ...],
    budget_energy: int,
    budget_storage: int,
    budget_downlink: int,
) -> bool:
    used_energy = 0
    used_storage = 0
    used_downlink = 0
    for index in range(n_tasks):
        if (mask >> index) & 1:
            used_energy += task_energy[index]
            used_storage += task_storage[index]
            used_downlink += task_downlink[index]
    return (
        used_energy > budget_energy
        or used_storage > budget_storage
        or used_downlink > budget_downlink
    )


def _bits_from_mask(n_qubits: int, mask: int) -> tuple[int, ...]:
    return tuple((mask >> index) & 1 for index in range(n_qubits))
