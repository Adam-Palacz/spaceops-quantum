"""T12 smoke: one ideal p=1 evaluation of the 18-qubit fixture.

The parent process does not import Qiskit. The budget is one objective
evaluation. A complete basis-state report contains the known optimum because
every assignment is present, which is not an optimizer success.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"

_SCRIPT = r"""
import math
import os

from spaceops_quantum.domain import evaluate_solution, load_scenario
from spaceops_quantum.encoding import build_qubo
from spaceops_quantum.quantum.aer import AerIdealBackend
from spaceops_quantum.quantum.qaoa import OptimizerConfig, run_qaoa

penalties = {"energy": 41, "storage": 41, "downlink": 41}
scenario = load_scenario(os.environ["SPACEOPS_FIXTURE"])
qubo = build_qubo(scenario, penalties)
assert qubo.n_task_bits == 6
assert qubo.n_slack_bits == 12
assert qubo.n_logical_qubits == 18

result = run_qaoa(
    scenario,
    AerIdealBackend(),
    p=1,
    shots=None,
    seed=0,
    optimizer=OptimizerConfig(max_evaluations=1, initial_parameters=(0.1, 0.2)),
    lambda_by_constraint=penalties,
)
assert result.scenario_id == "eo-six-tasks-v1"
assert result.p == 1
assert result.seed == 0
assert result.shots is None
assert result.backend == "aer-statevector"
assert len(result.evaluations) == 1
assert result.evaluations[0].parameters == (0.1, 0.2)
assert result.parameters == (0.1, 0.2)
assert result.energy > 0
assert len(result.candidates) == 262144
assert abs(sum(item.probability for item in result.candidates) - 1.0) < 1e-6

feasible_patterns = set()
infeasible_patterns = set()
feasible_mass = 0.0
for item in result.candidates:
    assert len(item.bits) == 18
    pattern = item.assessment.task_bits
    if item.assessment.task_feasible:
        feasible_patterns.add(pattern)
        feasible_mass += item.probability
    else:
        infeasible_patterns.add(pattern)
assert feasible_patterns.isdisjoint(infeasible_patterns)
assert len(feasible_patterns) == 37
assert len(infeasible_patterns) == 27
assert math.isclose(result.feasibility_rate, feasible_mass, abs_tol=1e-9)
assert result.best_feasible_priority == 27

optimum_bits = (1, 1, 0, 0, 1, 1)
optimum = next(item for item in result.candidates if item.bits[:6] == optimum_bits)
assert optimum.assessment.priority == 27
assert optimum.assessment.task_feasible is True
scored = evaluate_solution(scenario, optimum.assessment.task_bits)
assert scored.selected_task_ids == ("T1", "T2", "T5", "T6")
assert scored.priority == 27
assert scored.feasible is True
assert (scored.used.energy, scored.used.storage, scored.used.downlink) == (9, 10, 10)

overfull = next(item for item in result.candidates if item.bits[:6] == (1, 1, 1, 1, 1, 1))
assert overfull.assessment.task_feasible is False
assert overfull.assessment.priority == 40
rejected = evaluate_solution(scenario, overfull.assessment.task_bits)
assert rejected.feasible is False
assert rejected.priority == 40

empty = next(item for item in result.candidates if item.bits[:6] == (0, 0, 0, 0, 0, 0))
assert empty.assessment.task_feasible is True
assert empty.assessment.priority == 0

optimum_mass = sum(
    item.probability
    for item in result.candidates
    if item.assessment.selected_task_ids == ("T1", "T2", "T5", "T6")
)
assert math.isclose(result.ideal_optimum_probability, optimum_mass, abs_tol=1e-9)
assert result.ideal_optimum_probability > 0
versions = dict(result.versions)
assert versions["qiskit"] == "2.4.1"
assert versions["qiskit-aer"] == "0.18.2"
print("ok")
"""


def test_f0_ideal_qaoa_smoke_uses_one_evaluation() -> None:
    assert "qiskit" not in sys.modules
    env = os.environ.copy()
    env["SPACEOPS_FIXTURE"] = str(_FIXTURE)
    completed = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        check=False,
        capture_output=True,
        text=True,
        timeout=360,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "ok" in completed.stdout
    assert "qiskit" not in sys.modules
