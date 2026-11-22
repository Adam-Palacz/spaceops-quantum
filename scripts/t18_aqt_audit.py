"""Compile F1–F3 once and write the AQT resource audit.

This does not sample shots and does not submit a Slurm job.
"""

from __future__ import annotations

import sys
from pathlib import Path

from spaceops_quantum.domain import load_scenario
from spaceops_quantum.quantum.aqt_audit import audit_qaoa_circuit, write_audit

_ROOT = Path(__file__).resolve().parents[1]
_SCENARIOS = (
    "configs/f1_three_tasks.yaml",
    "configs/f2_six_tasks.yaml",
    "configs/f3_six_tasks.yaml",
)


def main() -> int:
    destination = _ROOT / "specs" / "001-task-selection" / "t18-aqt-audit.json"
    audits = [
        audit_qaoa_circuit(load_scenario(_ROOT / relative))
        for relative in _SCENARIOS
    ]
    write_audit(destination, audits)
    for audit in audits:
        print(
            f"{audit.scenario_id} qubits {audit.logical_qubits} "
            f"depth {audit.depth} rxx {audit.rxx_count} "
            f"native {audit.native_gates_only} "
            f"terminal {audit.terminal_full_register_measurement}"
        )
    print(destination)
    return 0


if __name__ == "__main__":
    sys.exit(main())
