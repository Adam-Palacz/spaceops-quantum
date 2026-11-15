"""QUBO expansion of the penalized task-selection objective.

The published polynomial is

    E = constant + sum_i linear_i v_i + sum_{i<j} quadratic_ij v_i v_j.

``quadratic_ij`` is the full coefficient of the product ``v_i v_j``. It is not
the off-diagonal entry of a symmetric matrix, whose two contributions would
halve that coefficient. ``v_i^2 = v_i`` is folded into ``linear_i``. The
constant offset is stored separately and ``evaluate`` includes it.

This module does not import Qiskit.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from spaceops_quantum.domain.models import Scenario
from spaceops_quantum.encoding.bit_mapping import (
    BitLayout,
    EncodingError,
    allocate_layout,
    decode_sample,
)

QUBO_CONVENTION = (
    "E = constant + sum_i linear_i v_i + sum_{i<j} quadratic_ij v_i v_j. "
    "quadratic_ij is the full monomial coefficient, not half of a symmetric "
    "matrix entry. v_i^2 = v_i is folded into linear_i. The constant offset "
    "is stored separately and included by evaluate."
)
_RESOURCES = ("energy", "storage", "downlink")


@dataclass(frozen=True, slots=True)
class QuboModel:
    """Expanded QUBO for one scenario and one penalty vector."""

    variable_names: tuple[str, ...]
    linear: tuple[tuple[str, int], ...]
    quadratic: tuple[tuple[str, str, int], ...]
    constant: int
    lambda_by_constraint: tuple[tuple[str, int], ...]
    bit_layout: BitLayout
    n_task_bits: int
    n_slack_bits: int
    n_logical_qubits: int
    scenario_hash: str
    convention: str = QUBO_CONVENTION

    def evaluate(self, bits: Sequence[int]) -> int:
        """Return the penalized energy, including the constant offset."""
        decode_sample(bits, self.bit_layout)
        values = list(bits)
        index = {name: position for position, name in enumerate(self.variable_names)}
        total = self.constant
        for name, coefficient in self.linear:
            total += coefficient * values[index[name]]
        for left, right, coefficient in self.quadratic:
            total += coefficient * values[index[left]] * values[index[right]]
        return total


def build_qubo(scenario: Scenario, lambda_by_constraint: Mapping[str, int]) -> QuboModel:
    """Expand ``-priority + sum_r λ_r (cost_r + slack_r - budget_r)^2``."""
    penalties = _penalties(lambda_by_constraint)
    layout = allocate_layout(scenario)
    linear = {name: 0 for name in layout.variable_names}
    quadratic: dict[tuple[str, str], int] = {}
    constant = 0
    for task in scenario.tasks:
        linear[f"x_{task.id}"] -= task.priority
    for resource, penalty in zip(_RESOURCES, penalties, strict=True):
        register = next(item for item in layout.registers if item.resource == resource)
        constant += _expand_square(
            layout,
            linear,
            quadratic,
            terms=_constraint_terms(scenario, layout, register.resource),
            budget=register.budget,
            penalty=penalty,
        )
    index = {variable.name: variable.index for variable in layout.variables}
    ordered_quadratic = tuple(
        (left, right, coefficient)
        for (left, right), coefficient in sorted(
            quadratic.items(),
            key=lambda item: (index[item[0][0]], index[item[0][1]]),
        )
    )
    return QuboModel(
        variable_names=layout.variable_names,
        linear=tuple(linear.items()),
        quadratic=ordered_quadratic,
        constant=constant,
        lambda_by_constraint=tuple(zip(_RESOURCES, penalties, strict=True)),
        bit_layout=layout,
        n_task_bits=layout.n_task_bits,
        n_slack_bits=layout.n_slack_bits,
        n_logical_qubits=layout.n_logical_qubits,
        scenario_hash=scenario_hash(scenario),
    )


def scenario_hash(scenario: Scenario) -> str:
    """Hash the mathematical instance, ignoring description and reference."""
    payload = {
        "budgets": {
            "downlink": scenario.budgets.downlink,
            "energy": scenario.budgets.energy,
            "storage": scenario.budgets.storage,
        },
        "scenario_id": scenario.scenario_id,
        "schema_version": scenario.schema_version,
        "tasks": [
            {
                "downlink": task.downlink,
                "energy": task.energy,
                "id": task.id,
                "priority": task.priority,
                "storage": task.storage,
            }
            for task in scenario.tasks
        ],
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _penalties(values: Mapping[str, int]) -> tuple[int, int, int]:
    if not isinstance(values, Mapping):
        raise EncodingError(
            f"lambda_by_constraint must be a mapping, got {type(values).__name__}"
        )
    missing = [name for name in _RESOURCES if name not in values]
    if missing:
        raise EncodingError(f"missing penalty fields: {', '.join(missing)}")
    unknown = sorted(set(values) - set(_RESOURCES))
    if unknown:
        raise EncodingError(f"unknown penalty fields: {', '.join(unknown)}")
    penalties: list[int] = []
    for name in _RESOURCES:
        penalty = values[name]
        if isinstance(penalty, bool) or not isinstance(penalty, int) or penalty < 0:
            raise EncodingError(f"lambda {name} must be an integer >= 0, got {penalty!r}")
        penalties.append(penalty)
    return (penalties[0], penalties[1], penalties[2])


def _constraint_terms(
    scenario: Scenario,
    layout: BitLayout,
    resource: str,
) -> tuple[tuple[str, int], ...]:
    terms: list[tuple[str, int]] = []
    for task in scenario.tasks:
        coefficient = getattr(task, resource)
        if coefficient != 0:
            terms.append((f"x_{task.id}", coefficient))
    register = next(item for item in layout.registers if item.resource == resource)
    terms.extend(zip(register.names, register.weights, strict=True))
    return tuple(terms)


def _expand_square(
    layout: BitLayout,
    linear: dict[str, int],
    quadratic: dict[tuple[str, str], int],
    *,
    terms: tuple[tuple[str, int], ...],
    budget: int,
    penalty: int,
) -> int:
    """Add ``penalty * (sum_j c_j v_j - budget)^2`` and return its constant."""
    if penalty == 0:
        return 0
    index = {variable.name: variable.index for variable in layout.variables}
    for position, (name, coefficient) in enumerate(terms):
        linear[name] += penalty * (coefficient * coefficient - 2 * budget * coefficient)
        for other_name, other_coefficient in terms[position + 1 :]:
            product = penalty * 2 * coefficient * other_coefficient
            if product == 0:
                continue
            if index[name] < index[other_name]:
                key = (name, other_name)
            else:
                key = (other_name, name)
            quadratic[key] = quadratic.get(key, 0) + product
    return penalty * budget * budget
