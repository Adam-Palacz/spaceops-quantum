"""Backend contract for ideal and shot-based simulation.

This module records simulator versions and the shape of a run. It does not
import Qiskit. Aer adapters live in ``spaceops_quantum.quantum.aer``.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from typing import Protocol, runtime_checkable

_PACKAGES = ("qiskit", "qiskit-aer")


class BackendError(ValueError):
    """A backend request or simulator result violates the protocol."""


@dataclass(frozen=True, slots=True)
class BackendSample:
    """One measured outcome in logical bit order.

    Index 0 is qubit 0. ``probability`` is the statevector probability for an
    ideal run, or ``count / shots`` for a sampled run. ``count`` is set only
    for a sampled run.
    """

    bits: tuple[int, ...]
    probability: float | None = None
    count: int | None = None


@dataclass(frozen=True, slots=True)
class BackendRun:
    """One noiseless simulator execution."""

    backend: str
    method: str
    shots: int | None
    seed: int | None
    samples: tuple[BackendSample, ...]
    versions: tuple[tuple[str, str], ...]


@runtime_checkable
class QuantumBackend(Protocol):
    """Run a circuit and return logical samples.

    ``circuit`` stays untyped here so this protocol can be checked without
    importing Qiskit. An Aer adapter rejects anything other than a Qiskit
    ``QuantumCircuit``.
    """

    name: str

    def run(
        self,
        circuit: object,
        *,
        shots: int | None = None,
        seed: int | None = None,
    ) -> BackendRun:
        """Execute ``circuit``. Ideal runs omit shots and seed."""


def installed_quantum_versions() -> tuple[tuple[str, str], ...]:
    """Return installed Qiskit and Aer versions without importing them."""

    return tuple((name, version(name)) for name in _PACKAGES)
