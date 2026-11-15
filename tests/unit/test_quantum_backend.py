"""T10 backend protocol and Aer smoke checks.

The in-process tests never import Qiskit. The Aer smoke runs in a subprocess
so the rest of the suite still sees an interpreter without ``qiskit`` loaded.
"""

from __future__ import annotations

import subprocess
import sys

from spaceops_quantum.quantum import (
    BackendRun,
    BackendSample,
    QuantumBackend,
    installed_quantum_versions,
)

_ISOLATION_SCRIPT = """
import sys
import spaceops_quantum.domain
import spaceops_quantum.classical
import spaceops_quantum.encoding
import spaceops_quantum.cli
import spaceops_quantum.quantum
assert "qiskit" not in sys.modules, sorted(sys.modules)
assert "qiskit_aer" not in sys.modules, sorted(sys.modules)
print("ok")
"""

_AER_SCRIPT = """
from qiskit import QuantumCircuit

from spaceops_quantum.quantum.aer import AerIdealBackend, AerSampledBackend
from spaceops_quantum.quantum.protocol import BackendError, installed_quantum_versions

ideal_circuit = QuantumCircuit(2)
ideal_circuit.x(0)
instruction_count = len(ideal_circuit.data)
ideal = AerIdealBackend().run(ideal_circuit)
assert len(ideal_circuit.data) == instruction_count
assert ideal.method == "statevector"
assert ideal.shots is None
assert ideal.seed is None
assert len(ideal.samples) == 1
assert ideal.samples[0].bits == (1, 0)
assert ideal.samples[0].probability == 1.0
assert ideal.samples[0].count is None

sampled_circuit = QuantumCircuit(2)
sampled_circuit.x(0)
sampled_circuit.measure_all()
sampled = AerSampledBackend()
first = sampled.run(sampled_circuit, shots=32, seed=7)
second = sampled.run(sampled_circuit, shots=32, seed=7)
assert first == second
assert first.shots == 32
assert first.seed == 7
assert first.samples[0].bits == (1, 0)
assert first.samples[0].count == 32
assert first.samples[0].probability == 1.0

try:
    AerIdealBackend().run(ideal_circuit, shots=1)
except BackendError:
    pass
else:
    raise SystemExit("ideal backend accepted shots")

versions = dict(ideal.versions)
assert versions == dict(installed_quantum_versions())
parsed = tuple(int(part) for part in versions["qiskit"].split("."))
assert (2, 3, 0) <= parsed <= (2, 4, 1)
assert versions["qiskit"] == "2.4.1"
assert versions["qiskit-aer"] == "0.18.2"
print("ok")
"""


def test_protocol_accepts_a_backend_without_qiskit() -> None:
    class RecordingBackend:
        name = "recording"

        def run(
            self,
            circuit: object,
            *,
            shots: int | None = None,
            seed: int | None = None,
        ) -> BackendRun:
            return BackendRun(
                backend=self.name,
                method="fake",
                shots=shots,
                seed=seed,
                samples=(BackendSample(bits=(1, 0), probability=1.0),),
                versions=(),
            )

    backend = RecordingBackend()
    assert isinstance(backend, QuantumBackend)
    result = backend.run(object())
    assert result.samples[0].bits == (1, 0)
    assert "qiskit" not in sys.modules
    assert "qiskit_aer" not in sys.modules


def test_version_record_does_not_import_qiskit() -> None:
    versions = dict(installed_quantum_versions())
    assert versions == {"qiskit": "2.4.1", "qiskit-aer": "0.18.2"}
    parsed = tuple(int(part) for part in versions["qiskit"].split("."))
    assert (2, 3, 0) <= parsed <= (2, 4, 1)
    assert "qiskit" not in sys.modules
    assert "qiskit_aer" not in sys.modules


def test_domain_layers_do_not_import_qiskit() -> None:
    _run_script(_ISOLATION_SCRIPT)


def test_aer_smoke_maps_qubit_zero_and_repeats_a_seed() -> None:
    _run_script(_AER_SCRIPT)


def _run_script(code: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "ok" in completed.stdout
