"""AQT offline compilation stays out of the parent interpreter."""

from __future__ import annotations

import subprocess
import sys

_SCRIPT = r"""
import sys
from spaceops_quantum.domain import Resources, Scenario, Task
from spaceops_quantum.quantum.aqt_audit import audit_qaoa_circuit

scenario = Scenario(
    schema_version=1,
    scenario_id="aqt-tiny",
    description="two tasks",
    budgets=Resources(1, 0, 0),
    tasks=(
        Task("A", priority=3, energy=1, storage=0, downlink=0),
        Task("B", priority=4, energy=1, storage=0, downlink=0),
    ),
)
audit = audit_qaoa_circuit(scenario)
assert audit.decision_variables == 2
assert audit.slack_qubits == 1
assert audit.logical_qubits == 3
assert audit.compiled_qubits == 3
assert audit.measure_count == 3
assert audit.terminal_full_register_measurement
assert audit.native_gates_only
assert audit.other_operations == ()
assert audit.targets_match
assert audit.ideal_target == ("measure", "r", "rxx", "rz")
assert audit.rxx_count >= 1
assert audit.within_two_qubit_budget
assert "qiskit_aqt_provider" in sys.modules
print("ok")
"""


def test_aqt_audit_import_does_not_load_qiskit() -> None:
    import spaceops_quantum.quantum.aqt_audit as audit

    assert "qiskit" not in sys.modules
    assert audit.AqtCircuitAudit.__name__ == "AqtCircuitAudit"


def test_tiny_circuit_compiles_to_native_aqt_gates() -> None:
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
