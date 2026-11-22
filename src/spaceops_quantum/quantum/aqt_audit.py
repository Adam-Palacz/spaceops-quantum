"""Compile one p=1 QAOA circuit to the AQT offline target.

Importing this module does not import Qiskit or the AQT provider. The
offline target is a local simulator gate set. This module does not submit a
job and does not read an API token.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from spaceops_quantum.domain.models import Scenario
from spaceops_quantum.encoding import allocate_layout, build_qubo, to_ising

_NATIVE = frozenset({"measure", "r", "rxx", "rz"})
_IGNORED = frozenset({"barrier"})
_PARAMETERS = (0.1, 0.2)
_PENALTY = 41
_TWO_QUBIT_BUDGET = 400


@dataclass(frozen=True, slots=True)
class AqtCircuitAudit:
    """Resource counts for one compiled QAOA circuit."""

    scenario_id: str
    decision_variables: int
    slack_qubits: int
    logical_qubits: int
    compiled_qubits: int
    backend_register_qubits: int
    penalty: int
    gamma: float
    beta: float
    optimization_level: int
    seed_transpiler: int
    depth: int
    r_count: int
    rz_count: int
    rxx_count: int
    measure_count: int
    barrier_count: int
    other_operations: tuple[str, ...]
    terminal_full_register_measurement: bool
    native_gates_only: bool
    two_qubit_budget: int
    within_two_qubit_budget: bool
    ideal_target: tuple[str, ...]
    noisy_target: tuple[str, ...]
    targets_match: bool
    ideal_and_noisy_counts_match: bool


def audit_qaoa_circuit(
    scenario: Scenario,
    *,
    penalty: int = _PENALTY,
    parameters: tuple[float, float] = _PARAMETERS,
    optimization_level: int = 1,
    seed_transpiler: int = 0,
) -> AqtCircuitAudit:
    """Transpile p=1 QAOA with a terminal full-register measurement."""

    from qiskit import transpile
    from qiskit_aqt_provider import AQTProvider

    from spaceops_quantum.quantum.qaoa import qaoa_circuit

    layout = allocate_layout(scenario)
    penalties = {"downlink": penalty, "energy": penalty, "storage": penalty}
    circuit = qaoa_circuit(to_ising(build_qubo(scenario, penalties)), parameters)
    circuit.measure_all()
    provider = AQTProvider()
    ideal = provider.offline.ideal()
    noisy = provider.offline.noisy()
    ideal_names = tuple(sorted(ideal.target.operation_names))
    noisy_names = tuple(sorted(noisy.target.operation_names))
    compiled_ideal = transpile(
        circuit,
        target=ideal.target,
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
    )
    compiled_noisy = transpile(
        circuit,
        target=noisy.target,
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
    )
    ideal_counts = _counts(compiled_ideal)
    noisy_counts = _counts(compiled_noisy)
    others = tuple(sorted(name for name in ideal_counts if name not in _NATIVE | _IGNORED))
    rxx_count = ideal_counts.get("rxx", 0)
    return AqtCircuitAudit(
        scenario_id=scenario.scenario_id,
        decision_variables=layout.n_task_bits,
        slack_qubits=layout.n_slack_bits,
        logical_qubits=layout.n_logical_qubits,
        compiled_qubits=compiled_ideal.num_qubits,
        backend_register_qubits=ideal.target.num_qubits,
        penalty=penalty,
        gamma=parameters[0],
        beta=parameters[1],
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
        depth=compiled_ideal.depth(),
        r_count=ideal_counts.get("r", 0),
        rz_count=ideal_counts.get("rz", 0),
        rxx_count=rxx_count,
        measure_count=ideal_counts.get("measure", 0),
        barrier_count=ideal_counts.get("barrier", 0),
        other_operations=others,
        terminal_full_register_measurement=_terminal_full_register(compiled_ideal),
        native_gates_only=not others,
        two_qubit_budget=_TWO_QUBIT_BUDGET,
        within_two_qubit_budget=rxx_count < _TWO_QUBIT_BUDGET,
        ideal_target=ideal_names,
        noisy_target=noisy_names,
        targets_match=ideal_names == noisy_names,
        ideal_and_noisy_counts_match=ideal_counts == noisy_counts,
    )


def write_audit(path: Path, audits: list[AqtCircuitAudit]) -> None:
    """Write one JSON document. The path's parent must already exist."""

    payload = {
        "audits": [asdict(item) for item in audits],
        "parameters": {"beta": _PARAMETERS[1], "gamma": _PARAMETERS[0]},
        "penalty": _PENALTY,
        "schema_version": 1,
        "source": "AQT offline ideal and noisy targets, qiskit-aqt-provider 2.0.1",
        "two_qubit_budget": _TWO_QUBIT_BUDGET,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _counts(circuit: Any) -> dict[str, int]:
    return {name: int(count) for name, count in circuit.count_ops().items()}


def _terminal_full_register(circuit: Any) -> bool:
    measured: set[int] = set()
    finished: set[int] = set()
    for instruction in circuit.data:
        name = instruction.operation.name
        qubits = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        if name == "measure":
            if len(qubits) != 1 or qubits[0] in measured:
                return False
            measured.add(qubits[0])
            finished.add(qubits[0])
            continue
        if any(qubit in finished for qubit in qubits):
            return False
    return measured == set(range(circuit.num_qubits))
