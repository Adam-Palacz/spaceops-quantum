"""Controlled T19 grid: exact search, then offline ideal and noisy shots.

Importing this module does not import Qiskit. A cell that fails is archived
and the remaining cells still run. No cloud, direct-access, or QPU client
is used.
"""

from __future__ import annotations

import json
import math
import os
import time
import traceback
from pathlib import Path
from typing import Any

from spaceops_quantum.classical import solve_exact, solve_greedy
from spaceops_quantum.domain import load_scenario
from spaceops_quantum.encoding import (
    assess_sample,
    build_qubo,
    logical_bits_from_qiskit_bitstring,
    to_ising,
)
from spaceops_quantum.experiment.baseline import uniform_task_baseline
from spaceops_quantum.experiment.f2_pilot import PilotError, prepare_output
from spaceops_quantum.quantum.sampling import is_original_optimum

_PENALTY = 41
_EVALUATIONS = 25
_SHOTS = 200
_SCENARIOS = {
    "f2-six-tasks-v1": "configs/f2_six_tasks.yaml",
    "f3-six-tasks-v1": "configs/f3_six_tasks.yaml",
}
_SEEDS = (0, 1, 2)
_BLOCKED_ENV = (
    "AQT_TOKEN",
    "AQT_ACCESS_TOKEN",
    "AQT_DIRECT_URL",
    "AQT_WORKSPACE_ID",
    "AQT_RESOURCE_ID",
)


def slurm_request() -> dict[str, object]:
    """The one CPU job that runs every evidence cell."""

    return {
        "cap_node_hours": 0.5,
        "cpus_per_task": 2,
        "licenses": None,
        "mem": "8G",
        "nodes": 1,
        "ntasks": 1,
        "partition": "all",
        "time": "00:30:00",
    }


def planned_cells() -> tuple[dict[str, object], ...]:
    """Six cells. F2 seed 0 is repeated so the grid has one procedure."""

    cells: list[dict[str, object]] = []
    for scenario_id, relative in _SCENARIOS.items():
        for seed in _SEEDS:
            cells.append(
                {
                    "cell_id": f"{scenario_id}-seed{seed}",
                    "scenario_id": scenario_id,
                    "scenario_file": relative,
                    "seed": seed,
                }
            )
    return tuple(cells)


def binomial_standard_error(hits: int, shots: int) -> float:
    """Standard error of a hit frequency. ``shots`` must be positive."""

    if shots <= 0:
        raise PilotError(f"shots must be positive, got {shots}")
    probability = hits / shots
    return math.sqrt(probability * (1.0 - probability) / shots)


def execute_cells(
    out_dir: Path,
    cells: tuple[dict[str, object], ...],
    run: Any,
) -> dict[str, object]:
    """Run cells into a fresh directory. One failure does not erase the others."""

    prepare_output(out_dir)
    records: list[dict[str, object]] = []
    for cell in cells:
        cell_id = str(cell["cell_id"])
        cell_dir = out_dir / cell_id
        try:
            payload = run(cell, cell_dir)
            records.append({"cell_id": cell_id, "status": "ok", "summary": _summary(payload)})
        except Exception as exc:
            cell_dir.mkdir(parents=True, exist_ok=True)
            _write(
                cell_dir / "failure.json",
                {
                    "cell_id": cell_id,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "type": type(exc).__name__,
                },
            )
            records.append({"cell_id": cell_id, "error": str(exc), "status": "failed"})
    payload = {
        "cells": records,
        "failed": sum(1 for item in records if item["status"] != "ok"),
        "slurm_request": slurm_request(),
    }
    _write(out_dir / "grid_summary.json", payload)
    return payload


def run_cell(cell: dict[str, object], out_dir: Path, *, root: Path) -> dict[str, Any]:
    """Exact Aer search, then 200 offline ideal shots and 200 offline noisy shots."""

    for name in _BLOCKED_ENV:
        os.environ.pop(name, None)
    os.environ["AQT_PROVIDER"] = "offline"
    prepare_output(out_dir)
    started = time.perf_counter()
    scenario = load_scenario(root / str(cell["scenario_file"]))
    if scenario.scenario_id != cell["scenario_id"]:
        raise PilotError(f"scenario id {scenario.scenario_id} does not match the cell")
    seed = int(cell["seed"])
    penalties = {"downlink": _PENALTY, "energy": _PENALTY, "storage": _PENALTY}
    exact = solve_exact(scenario)
    greedy = solve_greedy(scenario, seed=seed)
    uniform = uniform_task_baseline(scenario)

    from spaceops_quantum.quantum.aer import AerIdealBackend
    from spaceops_quantum.quantum.aqt_audit import audit_qaoa_circuit
    from spaceops_quantum.quantum.qaoa import OptimizerConfig, qaoa_circuit, run_qaoa

    search_started = time.perf_counter()
    result = run_qaoa(
        scenario,
        AerIdealBackend(),
        p=1,
        shots=None,
        seed=seed,
        optimizer=OptimizerConfig(max_evaluations=_EVALUATIONS, initial_parameters=None),
        lambda_by_constraint=penalties,
    )
    search_seconds = time.perf_counter() - search_started
    gamma, beta = float(result.parameters[0]), float(result.parameters[1])
    if len(result.evaluations) > _EVALUATIONS:
        raise PilotError("the exact search exceeded 25 evaluations")
    audit = audit_qaoa_circuit(scenario, penalty=_PENALTY, parameters=(gamma, beta))
    if not audit.native_gates_only or not audit.targets_match:
        raise PilotError("the offline ideal and noisy targets do not share a native circuit")
    qubo = build_qubo(scenario, penalties)
    circuit = qaoa_circuit(to_ising(qubo), (gamma, beta))
    circuit.measure_all()

    from qiskit import transpile
    from qiskit_aqt_provider import AQTProvider

    provider = AQTProvider()
    ideal = provider.offline.ideal()
    noisy = provider.offline.noisy()
    _require_offline(str(ideal.id), "ideal")
    _require_offline(str(noisy.id), "noisy")
    compiled = transpile(circuit, target=noisy.target, optimization_level=1, seed_transpiler=0)
    if compiled.count_ops().get("rxx", 0) != audit.rxx_count or compiled.depth() != audit.depth:
        raise PilotError("the sampled circuit does not match the compilation audit")
    arms = {}
    for label, backend in (("ideal", ideal), ("noisy", noisy)):
        counts = backend.run(compiled, shots=_SHOTS, seed_simulator=seed).result().get_counts()
        arms[label] = _decode_counts(counts, qubo, scenario, exact.solution.priority)
    optimum = exact.solution.priority
    payload: dict[str, Any] = {
        "approx_ratio_best_observed": _ratio(arms["noisy"]["best_feasible_priority"], optimum),
        "approx_ratio_definition": (
            "best_observed is the best feasible shot divided by the exact priority. "
            "mean_feasible is the mean priority of feasible shots divided by the exact "
            "priority. Neither number is the statevector optimum probability."
        ),
        "arms": arms,
        "beta": beta,
        "classical": {
            "exact_priority": optimum,
            "feasible_uniform_exact": _fraction(uniform.feasible_probability),
            "greedy_priority": greedy.solution.priority,
            "uniform_exact": _fraction(uniform.probability),
        },
        "compilation": {
            "depth": audit.depth,
            "native_gates_only": audit.native_gates_only,
            "rxx_count": audit.rxx_count,
        },
        "evaluations": len(result.evaluations),
        "gamma": gamma,
        "ideal_optimum_probability": result.ideal_optimum_probability,
        "mean_feasible_approx_ratio": _ratio(arms["noisy"]["mean_feasible_priority"], optimum),
        "p": 1,
        "penalty": _PENALTY,
        "scenario_id": scenario.scenario_id,
        "search_seconds": search_seconds,
        "seed": seed,
        "shots": _SHOTS,
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "wall_time_sec": time.perf_counter() - started,
    }
    _write(out_dir / "cell.json", payload)
    _write(
        out_dir / "optimizer_trace.json",
        {
            "evaluations": [
                {
                    "beta": item.parameters[1],
                    "energy": item.energy,
                    "gamma": item.parameters[0],
                    "index": item.index,
                }
                for item in result.evaluations
            ]
        },
    )
    return payload


def _require_offline(backend_id: str, kind: str) -> None:
    """Accept the local AQT ids. The ideal id contains the letters in ``noise``."""

    if not backend_id.startswith("offline_simulator"):
        raise PilotError(f"refusing backend {backend_id}")
    ideal = "no_noise" in backend_id
    if kind == "ideal" and not ideal:
        raise PilotError(f"refusing backend {backend_id}")
    if kind == "noisy" and ideal:
        raise PilotError(f"refusing backend {backend_id}")


def _decode_counts(counts: Any, qubo: Any, scenario: Any, optimum_priority: int) -> dict[str, Any]:
    total = 0
    feasible = 0
    optimum = 0
    priority_sum = 0
    feasible_priority_sum = 0
    best: int | None = None
    width = qubo.n_logical_qubits
    for key, count in counts.items():
        shots = int(count)
        total += shots
        bits = _bits_from_key(str(key), width)
        assessment = assess_sample(qubo, scenario, bits)
        priority_sum += assessment.priority * shots
        if assessment.task_feasible:
            feasible += shots
            feasible_priority_sum += assessment.priority * shots
            if best is None or assessment.priority > best:
                best = assessment.priority
        if is_original_optimum(assessment, optimum_priority):
            optimum += shots
    if total != _SHOTS:
        raise PilotError(f"counts sum to {total}, expected {_SHOTS}")
    mean_feasible = None if feasible == 0 else feasible_priority_sum / feasible
    return {
        "best_feasible_priority": best,
        "feasibility_rate": feasible / total,
        "mean_feasible_priority": mean_feasible,
        "mean_selected_priority": priority_sum / total,
        "optimum_hit_count": optimum,
        "optimum_hit_frequency": optimum / total,
        "optimum_hit_standard_error": binomial_standard_error(optimum, total),
    }


def _bits_from_key(key: str, width: int) -> tuple[int, ...]:
    text = key.replace(" ", "")
    if len(text) < width:
        text = text.zfill(width)
    return logical_bits_from_qiskit_bitstring(text)


def _fraction(value: Any) -> str:
    return f"{value.numerator}/{value.denominator}"


def _ratio(value: int | float | None, optimum: int) -> float | None:
    if value is None or optimum == 0:
        return None
    return float(value) / optimum


def _summary(payload: dict[str, Any]) -> dict[str, object]:
    noisy = payload["arms"]["noisy"]
    return {
        "ideal_optimum_probability": payload["ideal_optimum_probability"],
        "optimum_hit_frequency": noisy["optimum_hit_frequency"],
        "rxx_count": payload["compilation"]["rxx_count"],
    }


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    """Run the grid only when the approval flag is set."""

    import argparse
    import os as _os

    if _os.environ.get("SPACEOPS_T19_APPROVED") != "1":
        print("T19 grid is not approved")
        print(f"cells {len(planned_cells())}")
        print(json.dumps(slurm_request(), sort_keys=True))
        return 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    def _run(cell: dict[str, object], cell_dir: Path) -> dict[str, Any]:
        return run_cell(cell, cell_dir, root=args.root)

    summary = execute_cells(args.out, planned_cells(), _run)
    print(f"failed {summary['failed']}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
