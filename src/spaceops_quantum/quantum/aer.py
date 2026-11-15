"""Noiseless Aer adapters.

Ideal runs read a statevector. Sampled runs use shots and ``seed_simulator``.
Neither adapter applies a noise model, and neither builds a QAOA circuit.
Qiskit display strings are reversed into logical order before they leave
this module.
"""

from __future__ import annotations

import numbers
from collections.abc import Mapping

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from spaceops_quantum.encoding.bit_mapping import (
    EncodingError,
    logical_bits_from_qiskit_bitstring,
)
from spaceops_quantum.quantum.protocol import (
    BackendError,
    BackendRun,
    BackendSample,
    installed_quantum_versions,
)

_PROBABILITY_FLOOR = 1e-12


class AerIdealBackend:
    """Noiseless Aer statevector. Shots and seeds are rejected."""

    name = "aer-statevector"

    def run(
        self,
        circuit: object,
        *,
        shots: int | None = None,
        seed: int | None = None,
    ) -> BackendRun:
        if shots is not None:
            raise BackendError("ideal statevector backend rejects shots")
        if seed is not None:
            raise BackendError("ideal statevector backend rejects a seed")
        prepared = _copy_circuit(circuit)
        if not _has_instruction(prepared, "save_statevector"):
            prepared.save_statevector()
        result = AerSimulator(method="statevector").run(prepared, shots=1).result()
        try:
            statevector = result.data(0)["statevector"]
        except (KeyError, IndexError) as exc:
            raise BackendError("Aer result has no statevector") from exc
        samples = _samples_from_probabilities(statevector.probabilities_dict())
        return BackendRun(
            backend=self.name,
            method="statevector",
            shots=None,
            seed=None,
            samples=samples,
            versions=installed_quantum_versions(),
        )


class AerSampledBackend:
    """Shot-based noiseless Aer. Shots and a seed are required."""

    name = "aer-sampled"

    def run(
        self,
        circuit: object,
        *,
        shots: int | None = None,
        seed: int | None = None,
    ) -> BackendRun:
        shot_count = _require_positive_int(shots, "shots")
        seed_value = _require_nonnegative_int(seed, "seed")
        prepared = _copy_circuit(circuit)
        result = (
            AerSimulator(method="statevector")
            .run(prepared, shots=shot_count, seed_simulator=seed_value)
            .result()
        )
        counts = result.get_counts()
        samples = _samples_from_counts(counts, shot_count)
        return BackendRun(
            backend=self.name,
            method="sampled",
            shots=shot_count,
            seed=seed_value,
            samples=samples,
            versions=installed_quantum_versions(),
        )


def _copy_circuit(circuit: object) -> QuantumCircuit:
    if not isinstance(circuit, QuantumCircuit):
        raise BackendError(
            f"circuit must be a Qiskit QuantumCircuit, got {type(circuit).__name__}"
        )
    return circuit.copy()


def _has_instruction(circuit: QuantumCircuit, name: str) -> bool:
    return any(instruction.operation.name == name for instruction in circuit.data)


def _samples_from_probabilities(
    probabilities: Mapping[object, object],
) -> tuple[BackendSample, ...]:
    samples: list[BackendSample] = []
    for key, raw_probability in probabilities.items():
        probability = _require_probability(raw_probability)
        if probability <= _PROBABILITY_FLOOR:
            continue
        samples.append(
            BackendSample(
                bits=_logical_bits(key),
                probability=probability,
                count=None,
            )
        )
    if not samples:
        raise BackendError("statevector has no outcome above the reporting threshold")
    return tuple(sorted(samples, key=lambda sample: sample.bits))


def _samples_from_counts(
    counts: Mapping[object, object],
    shots: int,
) -> tuple[BackendSample, ...]:
    samples: list[BackendSample] = []
    total = 0
    for key, raw_count in counts.items():
        count = _require_count(raw_count)
        total += count
        samples.append(
            BackendSample(
                bits=_logical_bits(key),
                probability=count / shots,
                count=count,
            )
        )
    if total != shots:
        raise BackendError(f"counts sum to {total}, expected {shots} shots")
    if not samples:
        raise BackendError("Aer result has no counts; the circuit needs measurements")
    return tuple(sorted(samples, key=lambda sample: sample.bits))


def _logical_bits(key: object) -> tuple[int, ...]:
    if not isinstance(key, str):
        raise BackendError(f"simulator bitstring must be str, got {type(key).__name__}")
    try:
        return logical_bits_from_qiskit_bitstring(key)
    except EncodingError as exc:
        raise BackendError(str(exc)) from exc


def _require_probability(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise BackendError(f"probability must be a real number, got {value!r}")
    return float(value)


def _require_count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise BackendError(f"shot count must be an integer, got {value!r}")
    count = int(value)
    if count < 0:
        raise BackendError(f"shot count must be >= 0, got {count}")
    return count


def _require_positive_int(value: object, label: str) -> int:
    number = _require_nonnegative_int(value, label)
    if number < 1:
        raise BackendError(f"{label} must be an integer >= 1, got {number}")
    return number


def _require_nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BackendError(f"{label} must be an integer, got {value!r}")
    if value < 0:
        raise BackendError(f"{label} must be an integer >= 0, got {value}")
    return value
