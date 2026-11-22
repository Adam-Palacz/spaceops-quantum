"""One F2 pilot: exact statevector search, then 200 AQT offline noisy shots.

The noisy stage copies the archived parameters. It does not call COBYLA.
The AQT call is ``offline.noisy()`` only. There is no cloud, direct-access,
OpenQAPI, or QPU client in this module.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
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
from spaceops_quantum.quantum.sampling import is_original_optimum

_PENALTY = 41
_SEED = 0
_EVALUATIONS = 25
_NOISY_SHOTS = 200
_NOISY_SEED = 0
_REQUIRED_AER = "0.18.2"
_BLOCKED_ENV = (
    "AQT_TOKEN",
    "AQT_ACCESS_TOKEN",
    "AQT_DIRECT_URL",
    "AQT_WORKSPACE_ID",
    "AQT_RESOURCE_ID",
)


class PilotError(RuntimeError):
    """The pilot refused to run or could not archive its result."""


def require_local_backends() -> str:
    """Return the Aer version. Any other version is a failed precondition."""

    import qiskit_aer

    version = qiskit_aer.__version__
    if version != _REQUIRED_AER:
        raise PilotError(f"qiskit-aer {_REQUIRED_AER} is required, found {version}")
    return version


def assert_noisy_offline(backend_id: str) -> None:
    """Accept only the local noisy simulator id."""

    if "offline" not in backend_id or "noise" not in backend_id:
        raise PilotError(f"refusing backend {backend_id}")


def prepare_output(path: Path) -> None:
    """Create an empty directory. A populated directory is left untouched."""

    if path.exists() and any(path.iterdir()):
        raise PilotError(f"output directory is not empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def run_f2_pilot(scenario_path: Path, out_dir: Path) -> dict[str, Any]:
    """Run the one approved F2 pilot and write its archive."""

    for name in _BLOCKED_ENV:
        os.environ.pop(name, None)
    os.environ["AQT_PROVIDER"] = "offline"
    aer_version = require_local_backends()
    prepare_output(out_dir)
    started = time.perf_counter()
    scenario = load_scenario(scenario_path)
    if scenario.scenario_id != "f2-six-tasks-v1":
        raise PilotError(f"pilot accepts only F2, got {scenario.scenario_id}")

    from spaceops_quantum.quantum.aer import AerIdealBackend
    from spaceops_quantum.quantum.aqt_audit import audit_qaoa_circuit
    from spaceops_quantum.quantum.qaoa import OptimizerConfig, qaoa_circuit, run_qaoa

    penalties = {"downlink": _PENALTY, "energy": _PENALTY, "storage": _PENALTY}
    exact = solve_exact(scenario)
    greedy = solve_greedy(scenario, seed=_SEED)
    uniform = uniform_task_baseline(scenario)
    search_started = time.perf_counter()
    result = run_qaoa(
        scenario,
        AerIdealBackend(),
        p=1,
        shots=None,
        seed=_SEED,
        optimizer=OptimizerConfig(max_evaluations=_EVALUATIONS, initial_parameters=None),
        lambda_by_constraint=penalties,
    )
    search_seconds = time.perf_counter() - search_started
    gamma, beta = float(result.parameters[0]), float(result.parameters[1])
    if len(result.evaluations) > _EVALUATIONS:
        raise PilotError("the exact search exceeded 25 evaluations")
    audit = audit_qaoa_circuit(
        scenario,
        penalty=_PENALTY,
        parameters=(gamma, beta),
    )
    qubo = build_qubo(scenario, penalties)
    circuit = qaoa_circuit(to_ising(qubo), (gamma, beta))
    circuit.measure_all()
    from qiskit import transpile
    from qiskit_aqt_provider import AQTProvider

    backend = AQTProvider().offline.noisy()
    assert_noisy_offline(str(backend.id))
    if not audit.native_gates_only:
        raise PilotError("compiled circuit is not native to the offline target")
    compiled = transpile(
        circuit,
        target=backend.target,
        optimization_level=1,
        seed_transpiler=0,
    )
    sampled_rxx = compiled.count_ops().get("rxx", 0)
    if sampled_rxx != audit.rxx_count or compiled.depth() != audit.depth:
        raise PilotError("the sampled circuit does not match the compilation audit")
    sample_started = time.perf_counter()
    counts = backend.run(compiled, shots=_NOISY_SHOTS, seed_simulator=_NOISY_SEED).result()
    sample_seconds = time.perf_counter() - sample_started
    decoded = _decode_counts(counts.get_counts(), qubo, scenario, exact.solution.priority)
    payload: dict[str, Any] = {
        "aer_version": aer_version,
        "approx_ratio": _ratio(decoded["best_feasible_priority"], exact.solution.priority),
        "backend_id": str(backend.id),
        "beta": beta,
        "classical": {
            "exact_priority": exact.solution.priority,
            "greedy_priority": greedy.solution.priority,
            "uniform_exact": (
                f"{uniform.probability.numerator}/{uniform.probability.denominator}"
            ),
        },
        "compilation": {
            "depth": audit.depth,
            "native_gates_only": audit.native_gates_only,
            "rxx_count": audit.rxx_count,
            "terminal_full_register_measurement": audit.terminal_full_register_measurement,
        },
        "evaluations": len(result.evaluations),
        "feasibility_rate": decoded["feasibility_rate"],
        "gamma": gamma,
        "ideal_optimum_probability": result.ideal_optimum_probability,
        "noisy_seed": _NOISY_SEED,
        "optimum_hit_frequency": decoded["optimum_hit_frequency"],
        "optimum_hit_count": decoded["optimum_hit_count"],
        "p": 1,
        "parameter_source_noisy": "fixed-from-ideal-trace",
        "peak_rss_kb": _peak_rss_kb(),
        "penalty": _PENALTY,
        "scenario_hash": result.scenario_hash,
        "scenario_id": scenario.scenario_id,
        "seed": _SEED,
        "shots": _NOISY_SHOTS,
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "search_seconds": search_seconds,
        "sample_seconds": sample_seconds,
        "wall_time_sec": time.perf_counter() - started,
    }
    _write(out_dir / "pilot.json", payload)
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
            ],
            "selected_beta": beta,
            "selected_gamma": gamma,
        },
    )
    _write(out_dir / "noisy_counts.json", decoded["counts"])
    _write(out_dir / "compilation_audit.json", asdict(audit))
    return payload


def _decode_counts(
    counts: Any,
    qubo: Any,
    scenario: Any,
    optimum_priority: int,
) -> dict[str, Any]:
    total = 0
    feasible = 0
    optimum = 0
    best: int | None = None
    stored: dict[str, int] = {}
    width = qubo.n_logical_qubits
    for key, count in counts.items():
        shots = int(count)
        total += shots
        bits = _bits_from_key(str(key), width)
        assessment = assess_sample(qubo, scenario, bits)
        label = "".join(str(bit) for bit in bits)
        stored[label] = shots
        if assessment.task_feasible:
            feasible += shots
            if best is None or assessment.priority > best:
                best = assessment.priority
        if is_original_optimum(assessment, optimum_priority):
            optimum += shots
    if total != _NOISY_SHOTS:
        raise PilotError(f"noisy counts sum to {total}, expected {_NOISY_SHOTS}")
    return {
        "best_feasible_priority": best,
        "counts": stored,
        "feasibility_rate": feasible / total,
        "optimum_hit_count": optimum,
        "optimum_hit_frequency": optimum / total,
    }


def _bits_from_key(key: str, width: int) -> tuple[int, ...]:
    text = key.replace(" ", "")
    if text.startswith("0x"):
        text = format(int(text, 16), f"0{width}b")
    if len(text) < width:
        text = text.zfill(width)
    return logical_bits_from_qiskit_bitstring(text)


def _ratio(best: int | None, optimum: int) -> float | None:
    if best is None or optimum == 0:
        return None
    return best / optimum


def _peak_rss_kb() -> int | None:
    status = Path("/proc/self/status")
    if not status.is_file():
        return None
    for line in status.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1])
    return None


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = run_f2_pilot(args.scenario, args.out)
    except PilotError as exc:
        print(str(exc))
        return 2
    print(f"gamma {payload['gamma']}")
    print(f"beta {payload['beta']}")
    print(f"optimum_hit_frequency {payload['optimum_hit_frequency']}")
    print(f"rxx_count {payload['compilation']['rxx_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
