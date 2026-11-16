"""Ideal QAOA at depth p=1.

The cost operator uses ``s_i = -Z_i``. That is the same spin as
``s_i = 2 v_i - 1``: Pauli Z is +1 on bit 0 and -1 on bit 1. A product
``s_i s_j`` is ``Z_i Z_j``. The Ising constant is not evolved. The reported
energy adds it through the original Ising polynomial, weighted by the
statevector probabilities.

The optimizer minimizes that energy and stops at ``max_evaluations``. A
decoded sample is feasible only when the original task budgets hold.
Infeasible samples stay in the result. ``sample_qaoa`` measures a fixed
parameter pair with finite shots. Depth p other than 1 is rejected.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from qiskit import QuantumCircuit
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.quantum_info import SparsePauliOp
from scipy.optimize import minimize

from spaceops_quantum.classical import solve_exact
from spaceops_quantum.domain.models import Scenario
from spaceops_quantum.encoding.ising import IsingModel, bits_to_spins, to_ising
from spaceops_quantum.encoding.penalty_audit import SampleAssessment, assess_sample
from spaceops_quantum.encoding.qubo import QuboModel, build_qubo
from spaceops_quantum.quantum.aer import AerSampledBackend
from spaceops_quantum.quantum.protocol import (
    BackendSample,
    QuantumBackend,
    installed_quantum_versions,
)
from spaceops_quantum.quantum.sampling import (
    SampledRunRecord,
    build_sampled_record,
    is_original_optimum,
)

_MASS_TOLERANCE = 1e-6


class QaoaError(ValueError):
    """A QAOA request is outside the ideal p=1 contract."""


class _BudgetExceeded(Exception):
    """The objective was asked for more evaluations than the budget allows."""


@dataclass(frozen=True, slots=True)
class OptimizerConfig:
    """Bound on the classical optimizer, with an optional fixed start."""

    max_evaluations: int
    initial_parameters: tuple[float, ...] | None = None


@dataclass(frozen=True, slots=True)
class OptimizerEvaluation:
    """One objective call. Index 0 is the first call, normally the start point."""

    index: int
    parameters: tuple[float, ...]
    energy: float


@dataclass(frozen=True, slots=True)
class QaoaCandidate:
    """One logical outcome, decoded and scored on the original constraints."""

    bits: tuple[int, ...]
    probability: float
    assessment: SampleAssessment


@dataclass(frozen=True, slots=True)
class QaoaResult:
    """A finished ideal p=1 run and its optimizer trace."""

    scenario_id: str
    scenario_hash: str
    p: int
    seed: int
    shots: None
    backend: str
    parameters: tuple[float, ...]
    energy: float
    evaluations: tuple[OptimizerEvaluation, ...]
    candidates: tuple[QaoaCandidate, ...]
    best_feasible_priority: int | None
    feasibility_rate: float
    ideal_optimum_probability: float
    versions: tuple[tuple[str, str], ...]


def ising_cost_operator(ising: IsingModel) -> SparsePauliOp:
    """Return the Pauli cost operator, without the Ising constant.

    Qubit 0 is the first logical variable. A Qiskit Pauli string stores that
    qubit in its rightmost character. Linear coefficients are negated so that
    ``Z`` matches ``s = 2v - 1``.
    """

    count = ising.n_logical_qubits
    index = {name: position for position, name in enumerate(ising.variable_names)}
    terms: list[tuple[str, float]] = []
    for name, coefficient in ising.linear:
        value = float(coefficient)
        if value == 0.0:
            continue
        terms.append((_pauli(count, {index[name]: "Z"}), -value))
    for left, right, coefficient in ising.quadratic:
        value = float(coefficient)
        if value == 0.0:
            continue
        terms.append((_pauli(count, {index[left]: "Z", index[right]: "Z"}), value))
    if not terms:
        return SparsePauliOp.from_list([(_pauli(count, {}), 0.0)])
    return SparsePauliOp.from_list(terms)


def qaoa_circuit(ising: IsingModel, parameters: Sequence[float]) -> QuantumCircuit:
    """Build one p=1 QAOA circuit. Parameters are ``(gamma, beta)``."""

    gamma, beta = _parameter_pair(parameters)
    count = ising.n_logical_qubits
    circuit = QuantumCircuit(count)
    for qubit in range(count):
        circuit.h(qubit)
    circuit.append(PauliEvolutionGate(ising_cost_operator(ising), time=gamma), range(count))
    circuit.append(PauliEvolutionGate(_mixer(count), time=beta), range(count))
    return _expand(circuit)


def sample_qaoa(
    scenario: Scenario,
    *,
    parameters: Sequence[float],
    shots: int,
    seed: int,
    lambda_by_constraint: Mapping[str, int],
) -> SampledRunRecord:
    """Measure one p=1 circuit and decode every observed bitstring."""

    pair = _parameter_pair(parameters)
    _require_seed(seed)
    if isinstance(shots, bool) or not isinstance(shots, int) or shots < 1:
        raise QaoaError(f"shots must be an integer >= 1, got {shots!r}")
    qubo = build_qubo(scenario, lambda_by_constraint)
    measured = qaoa_circuit(to_ising(qubo), pair)
    measured.measure_all()
    result = AerSampledBackend().run(measured, shots=shots, seed=seed)
    return build_sampled_record(
        scenario,
        qubo,
        result.samples,
        p=1,
        seed=seed,
        shots=shots,
        backend=result.backend,
        parameters=pair,
        versions=result.versions,
    )


def run_qaoa(
    scenario: Scenario,
    backend: QuantumBackend,
    *,
    p: int,
    shots: int | None,
    seed: int,
    optimizer: OptimizerConfig,
    lambda_by_constraint: Mapping[str, int],
) -> QaoaResult:
    """Minimize the ideal p=1 expectation and decode every returned outcome."""

    if p != 1:
        raise QaoaError(f"ideal QAOA in this task accepts p=1, got {p}")
    if shots is not None:
        raise QaoaError("ideal QAOA rejects shots; sampled runs are a later task")
    _require_seed(seed)
    budget = _require_budget(optimizer.max_evaluations)
    qubo = build_qubo(scenario, lambda_by_constraint)
    ising = to_ising(qubo)
    start = _start_parameters(seed, optimizer.initial_parameters)
    records: list[tuple[OptimizerEvaluation, tuple[BackendSample, ...]]] = []

    def objective(values: Sequence[float]) -> float:
        if len(records) >= budget:
            raise _BudgetExceeded
        parameters = _parameter_pair(values)
        samples = _distribution(backend, ising, parameters)
        energy = _expectation(ising, samples)
        records.append(
            (
                OptimizerEvaluation(index=len(records), parameters=parameters, energy=energy),
                samples,
            )
        )
        return energy

    try:
        minimize(
            objective,
            start,
            method="COBYLA",
            options={"maxiter": budget, "rhobeg": 0.5},
        )
    except _BudgetExceeded:
        pass
    if not records:
        raise QaoaError("the optimizer made no objective evaluations")
    best = min(records, key=lambda record: (record[0].energy, record[0].index))
    candidates = _candidates(qubo, scenario, best[1])
    feasible = tuple(item for item in candidates if item.assessment.task_feasible)
    optimum_priority = solve_exact(scenario).solution.priority
    return QaoaResult(
        scenario_id=scenario.scenario_id,
        scenario_hash=qubo.scenario_hash,
        p=1,
        seed=seed,
        shots=None,
        backend=backend.name,
        parameters=best[0].parameters,
        energy=best[0].energy,
        evaluations=tuple(record[0] for record in records),
        candidates=candidates,
        best_feasible_priority=_best_feasible_priority(feasible),
        feasibility_rate=sum(item.probability for item in feasible),
        ideal_optimum_probability=_optimum_probability(candidates, optimum_priority),
        versions=installed_quantum_versions(),
    )


def _distribution(
    backend: QuantumBackend,
    ising: IsingModel,
    parameters: tuple[float, float],
) -> tuple[BackendSample, ...]:
    result = backend.run(qaoa_circuit(ising, parameters))
    if result.shots is not None or result.seed is not None:
        raise QaoaError("ideal QAOA requires a statevector backend result")
    total = 0.0
    for sample in result.samples:
        if sample.probability is None:
            raise QaoaError("ideal sample is missing a probability")
        total += sample.probability
    if abs(total - 1.0) > _MASS_TOLERANCE:
        raise QaoaError(f"statevector probabilities sum to {total}, expected 1")
    return result.samples


def _expectation(ising: IsingModel, samples: Sequence[BackendSample]) -> float:
    total = 0.0
    for sample in samples:
        if sample.probability is None:
            raise QaoaError("ideal sample is missing a probability")
        energy = ising.evaluate(bits_to_spins(sample.bits))
        total += sample.probability * float(energy)
    return total


def _candidates(
    qubo: QuboModel,
    scenario: Scenario,
    samples: Sequence[BackendSample],
) -> tuple[QaoaCandidate, ...]:
    found: list[QaoaCandidate] = []
    for sample in samples:
        if sample.probability is None:
            raise QaoaError("ideal sample is missing a probability")
        found.append(
            QaoaCandidate(
                bits=sample.bits,
                probability=sample.probability,
                assessment=assess_sample(qubo, scenario, sample.bits),
            )
        )
    return tuple(sorted(found, key=lambda item: item.bits))


def _best_feasible_priority(feasible: Sequence[QaoaCandidate]) -> int | None:
    if not feasible:
        return None
    return max(item.assessment.priority for item in feasible)


def _optimum_probability(candidates: Sequence[QaoaCandidate], optimum_priority: int) -> float:
    return sum(
        item.probability
        for item in candidates
        if is_original_optimum(item.assessment, optimum_priority)
    )


def _start_parameters(seed: int, initial: tuple[float, ...] | None) -> tuple[float, float]:
    if initial is not None:
        return _parameter_pair(initial)
    generator = random.Random(seed)
    return (generator.random() * math.pi, generator.random() * math.pi)


def _parameter_pair(values: Sequence[float]) -> tuple[float, float]:
    if isinstance(values, (str, bytes, bytearray)):
        raise QaoaError("parameters must be two finite numbers (gamma, beta)")
    try:
        raw = list(values)
    except TypeError as exc:
        raise QaoaError("parameters must be two finite numbers (gamma, beta)") from exc
    if len(raw) != 2:
        raise QaoaError(f"p=1 QAOA expects 2 parameters (gamma, beta), got {len(raw)}")
    checked: list[float] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise QaoaError(f"parameter must be a finite number, got {value!r}")
        number = float(value)
        if not math.isfinite(number):
            raise QaoaError(f"parameter must be a finite number, got {value!r}")
        checked.append(number)
    return (checked[0], checked[1])


def _expand(circuit: QuantumCircuit) -> QuantumCircuit:
    """Replace Pauli evolution with gates the statevector simulator can run."""

    current = circuit
    for _ in range(4):
        names = {instruction.operation.name for instruction in current.data}
        if "PauliEvolution" not in names:
            return current
        current = current.decompose()
    raise QaoaError("QAOA circuit still contains an unevaluated Pauli evolution")


def _mixer(count: int) -> SparsePauliOp:
    terms = [(_pauli(count, {qubit: "X"}), 1.0) for qubit in range(count)]
    return SparsePauliOp.from_list(terms)


def _pauli(count: int, letters: dict[int, str]) -> str:
    characters = ["I"] * count
    for qubit, letter in letters.items():
        characters[count - 1 - qubit] = letter
    return "".join(characters)


def _require_seed(seed: object) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise QaoaError(f"seed must be an integer >= 0, got {seed!r}")


def _require_budget(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise QaoaError(f"max_evaluations must be an integer >= 1, got {value!r}")
    return value
