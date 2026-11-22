"""Sample a 2-qubit Bell circuit on the AQT offline simulators.

This process must stay on the local machine. It does not read an API token
and it does not open a cloud or direct-access backend.
"""

from __future__ import annotations

import importlib.metadata
import os
import traceback

_SHOTS = 100
_BLOCKED_ENV = (
    "AQT_TOKEN",
    "AQT_ACCESS_TOKEN",
    "AQT_DIRECT_URL",
    "AQT_WORKSPACE_ID",
    "AQT_RESOURCE_ID",
)


def bell_circuit():
    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure_all()
    return circuit


def main() -> int:
    for name in _BLOCKED_ENV:
        os.environ.pop(name, None)
    os.environ["AQT_PROVIDER"] = "offline"

    import qiskit
    from qiskit_aqt_provider import AQTProvider

    print(f"qiskit {qiskit.__version__}")
    provider_version = importlib.metadata.version("qiskit-aqt-provider")
    print(f"qiskit_aqt_provider {provider_version}")
    circuit = bell_circuit()
    provider = AQTProvider()
    backends = (
        ("ideal", provider.offline.ideal()),
        ("noisy", provider.offline.noisy()),
    )
    try:
        for label, backend in backends:
            print(f"backend {label} id {backend.id}")
            result = backend.run(circuit, shots=_SHOTS, seed_simulator=0).result()
            print(f"counts {label} {dict(result.get_counts())}")
            print(f"success {label}")
    except Exception:
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
