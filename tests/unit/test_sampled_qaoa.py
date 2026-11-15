"""Shot-based QAOA samples, bit order, and a run with no feasible shot.

Qiskit stays in the subprocess.
"""

from __future__ import annotations

import subprocess
import sys

_SCRIPT = r"""
from qiskit import QuantumCircuit

from spaceops_quantum.domain import Resources, Scenario, Task, evaluate_solution
from spaceops_quantum.encoding import build_qubo
from spaceops_quantum.quantum.aer import AerSampledBackend
from spaceops_quantum.quantum.qaoa import sample_qaoa
from spaceops_quantum.quantum.sampling import build_sampled_record

penalties = {"energy": 6, "storage": 0, "downlink": 0}
hand = Scenario(
    schema_version=1,
    scenario_id="bit-order-hand",
    description="one task on qubit 0",
    budgets=Resources(1, 0, 0),
    tasks=(Task("A", priority=3, energy=1, storage=0, downlink=0),),
)
prepared = QuantumCircuit(2)
prepared.x(0)
prepared.measure_all()
shots = AerSampledBackend().run(prepared, shots=32, seed=5)
assert len(shots.samples) == 1
assert shots.samples[0].bits == (1, 0)
assert shots.samples[0].count == 32
assert shots.samples[0].probability == 1.0
hand_qubo = build_qubo(hand, penalties)
hand_record = build_sampled_record(
    hand,
    hand_qubo,
    shots.samples,
    p=1,
    seed=5,
    shots=32,
    backend=shots.backend,
    parameters=(0.0, 0.0),
    versions=shots.versions,
)
assert hand_record.samples[0].assessment.selected_task_ids == ("A",)
scored = evaluate_solution(hand, hand_record.samples[0].assessment.task_bits)
assert scored.feasible is True
assert scored.priority == 3

pair = Scenario(
    schema_version=1,
    scenario_id="qaoa-two-tasks",
    description="two tasks, one energy unit",
    budgets=Resources(1, 0, 0),
    tasks=(
        Task("A", priority=3, energy=1, storage=0, downlink=0),
        Task("B", priority=2, energy=1, storage=0, downlink=0),
    ),
)
forced = QuantumCircuit(3)
forced.x(0)
forced.x(1)
forced.measure_all()
forced_run = AerSampledBackend().run(forced, shots=16, seed=1)
assert forced_run.samples[0].bits == (1, 1, 0)
assert forced_run.samples[0].count == 16
empty_best = build_sampled_record(
    pair,
    build_qubo(pair, penalties),
    forced_run.samples,
    p=1,
    seed=1,
    shots=16,
    backend=forced_run.backend,
    parameters=(0.0, 0.0),
    versions=forced_run.versions,
)
assert empty_best.best_feasible_priority is None
assert empty_best.feasibility_rate == 0
assert empty_best.approx_ratio is None
assert empty_best.relative_gap is None
assert empty_best.sampled_optimum_probability == 0
assert empty_best.samples[0].assessment.priority == 5
assert empty_best.samples[0].assessment.task_feasible is False

first = sample_qaoa(
    pair,
    parameters=(0.2, 0.3),
    shots=64,
    seed=4,
    lambda_by_constraint=penalties,
)
second = sample_qaoa(
    pair,
    parameters=(0.2, 0.3),
    shots=64,
    seed=4,
    lambda_by_constraint=penalties,
)
assert first == second
assert sum(item.count for item in first.samples) == 64
for item in first.samples:
    assert item.count >= 1
    assert item.probability == item.count / 64
    assert len(item.bits) == 3
assert first.backend == "aer-sampled"
assert first.shots == 64
assert first.seed == 4
versions = dict(first.versions)
assert versions["qiskit"] == "2.4.1"
assert versions["qiskit-aer"] == "0.18.2"
print("ok")
"""


def test_sampled_qaoa_counts_bit_order_and_empty_feasible_set() -> None:
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
