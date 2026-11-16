"""T11 ideal p=1 QAOA on a two-task instance.

Qiskit is imported only inside the subprocess. The parent interpreter must
stay free of it so the rest of the suite can assert that.
"""

from __future__ import annotations

import subprocess
import sys

_SCRIPT = r"""
import math
import random


def _all_bits(width):
    return tuple(
        tuple((mask >> index) & 1 for index in range(width)) for mask in range(1 << width)
    )


from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from spaceops_quantum.classical import solve_exact
from spaceops_quantum.domain import Resources, Scenario, Task, evaluate_solution
from spaceops_quantum.encoding import bits_to_spins, build_qubo, to_ising
from spaceops_quantum.quantum.aer import AerIdealBackend
from spaceops_quantum.quantum.qaoa import (
    OptimizerConfig,
    QaoaError,
    ising_cost_operator,
    qaoa_circuit,
    run_qaoa,
)

scenario = Scenario(
    schema_version=1,
    scenario_id="qaoa-two-tasks",
    description="two tasks, one energy unit",
    budgets=Resources(1, 0, 0),
    tasks=(
        Task("A", priority=3, energy=1, storage=0, downlink=0),
        Task("B", priority=2, energy=1, storage=0, downlink=0),
    ),
)
penalties = {"energy": 6, "storage": 0, "downlink": 0}
qubo = build_qubo(scenario, penalties)
ising = to_ising(qubo)
assert qubo.n_task_bits == 2
assert qubo.n_logical_qubits == 3
backend = AerIdealBackend()

uniform = run_qaoa(
    scenario,
    backend,
    p=1,
    shots=None,
    seed=0,
    optimizer=OptimizerConfig(max_evaluations=1, initial_parameters=(0.0, 0.0)),
    lambda_by_constraint=penalties,
)
assert uniform.evaluations[0].parameters == (0.0, 0.0)
assert len(uniform.evaluations) == 1
assert uniform.shots is None
assert uniform.p == 1
assert uniform.backend == "aer-statevector"
mean = sum(float(ising.evaluate(bits_to_spins(bits))) for bits in _all_bits(3)) / 8
assert abs(uniform.energy - mean) < 1e-8
assert len(uniform.candidates) == 8
both = next(item for item in uniform.candidates if item.bits[:2] == (1, 1))
assert both.assessment.task_feasible is False
assert both.assessment.priority == 5
assert both.assessment.selected_task_ids == ("A", "B")
scored = evaluate_solution(scenario, both.assessment.task_bits)
assert scored.feasible is False
assert scored.priority == 5
feasible_mass = sum(
    item.probability for item in uniform.candidates if item.assessment.task_feasible
)
assert math.isclose(uniform.feasibility_rate, feasible_mass, rel_tol=0, abs_tol=1e-9)
assert math.isclose(uniform.feasibility_rate, 0.75, rel_tol=0, abs_tol=1e-8)
assert uniform.best_feasible_priority == 3
optimum = solve_exact(scenario).solution
assert optimum.selected_task_ids == ("A",)
optimum_mass = sum(
    item.probability
    for item in uniform.candidates
    if item.assessment.task_feasible and item.assessment.priority == optimum.priority
)
assert math.isclose(uniform.ideal_optimum_probability, optimum_mass, abs_tol=1e-9)
assert math.isclose(uniform.ideal_optimum_probability, 0.25, abs_tol=1e-8)

operator = ising_cost_operator(ising)
labels = {label: complex(coeff).real for label, coeff in operator.to_list()}
assert abs(labels["IIZ"] - (-float(ising.linear[0][1]))) < 1e-12
prepared = QuantumCircuit(3)
prepared.x(0)
expected = float(ising.evaluate(bits_to_spins((1, 0, 0))))
observed = Statevector.from_instruction(prepared).expectation_value(operator).real
assert abs(observed + float(ising.constant) - expected) < 1e-8

probe = (0.35, 0.55)
probed = run_qaoa(
    scenario,
    backend,
    p=1,
    shots=None,
    seed=1,
    optimizer=OptimizerConfig(max_evaluations=1, initial_parameters=probe),
    lambda_by_constraint=penalties,
)
quantum_energy = Statevector.from_instruction(qaoa_circuit(ising, probe)).expectation_value(
    operator
).real + float(ising.constant)
assert abs(probed.energy - quantum_energy) < 1e-7

seed = 2
budget = 5
first = run_qaoa(
    scenario,
    backend,
    p=1,
    shots=None,
    seed=seed,
    optimizer=OptimizerConfig(max_evaluations=budget),
    lambda_by_constraint=penalties,
)
second = run_qaoa(
    scenario,
    backend,
    p=1,
    shots=None,
    seed=seed,
    optimizer=OptimizerConfig(max_evaluations=budget),
    lambda_by_constraint=penalties,
)
assert first == second
assert 1 <= len(first.evaluations) <= budget
generator = random.Random(seed)
start = (generator.random() * math.pi, generator.random() * math.pi)
assert first.evaluations[0].parameters == start
assert {name: value for name, value in first.versions}["qiskit"] == "2.4.1"

for bad in (
    {"p": 2, "shots": None, "seed": 0, "optimizer": OptimizerConfig(1)},
    {"p": 1, "shots": 16, "seed": 0, "optimizer": OptimizerConfig(1)},
    {"p": 1, "shots": None, "seed": 0, "optimizer": OptimizerConfig(0)},
):
    try:
        run_qaoa(scenario, backend, lambda_by_constraint=penalties, **bad)
    except QaoaError:
        pass
    else:
        raise SystemExit(f"accepted invalid request {bad}")

tie = Scenario(
    schema_version=1,
    scenario_id="two-optima",
    description="two feasible optima and one infeasible priority match",
    budgets=Resources(1, 0, 0),
    tasks=(
        Task("A", priority=4, energy=1, storage=0, downlink=0),
        Task("B", priority=4, energy=1, storage=0, downlink=0),
        Task("C", priority=4, energy=2, storage=0, downlink=0),
    ),
)
tie_exact = solve_exact(tie).solution
assert tie_exact.selected_task_ids == ("A",)
assert tie_exact.priority == 4
tie_result = run_qaoa(
    tie,
    backend,
    p=1,
    shots=None,
    seed=0,
    optimizer=OptimizerConfig(max_evaluations=1, initial_parameters=(0.0, 0.0)),
    lambda_by_constraint=penalties,
)
tie_mass = sum(
    item.probability
    for item in tie_result.candidates
    if item.assessment.task_feasible and item.assessment.priority == tie_exact.priority
)
canonical_mass = sum(
    item.probability
    for item in tie_result.candidates
    if item.assessment.selected_task_ids == tie_exact.selected_task_ids
)
assert tie_mass > canonical_mass
assert math.isclose(tie_result.ideal_optimum_probability, tie_mass, abs_tol=1e-9)
assert math.isclose(tie_result.ideal_optimum_probability, 0.25, abs_tol=1e-8)
print("ok")
"""


def test_ideal_qaoa_trace_and_decoded_samples_stay_out_of_process() -> None:
    assert "qiskit" not in sys.modules
    completed = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "ok" in completed.stdout
    assert "qiskit" not in sys.modules
