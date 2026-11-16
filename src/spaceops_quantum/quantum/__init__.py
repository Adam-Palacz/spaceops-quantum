"""Quantum backend protocol.

Importing this package does not import Qiskit. Aer adapters are loaded from
``spaceops_quantum.quantum.aer`` only by code that runs them.
"""

from spaceops_quantum.quantum.protocol import (
    BackendError,
    BackendRun,
    BackendSample,
    QuantumBackend,
    installed_quantum_versions,
)
from spaceops_quantum.quantum.sampling import (
    SampledRecordError,
    SampledRunRecord,
    SampledShot,
    build_sampled_record,
    is_original_optimum,
)

__all__ = [
    "BackendError",
    "BackendRun",
    "BackendSample",
    "QuantumBackend",
    "SampledRecordError",
    "SampledRunRecord",
    "SampledShot",
    "build_sampled_record",
    "installed_quantum_versions",
    "is_original_optimum",
]
