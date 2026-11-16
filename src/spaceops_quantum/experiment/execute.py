"""Execute the locked T15 runs and keep every failure.

Qiskit is imported only while a sampled or optimized cell runs. A failed cell
writes ``failure.json`` and the grid continues, so the summary still lists
every planned id.
"""

from __future__ import annotations

import json
import time
import traceback
from pathlib import Path

from spaceops_quantum.classical import solve_exact, solve_greedy
from spaceops_quantum.domain import load_scenario
from spaceops_quantum.experiment.archive import (
    capture_classical,
    capture_sampled,
    write_experiment,
)
from spaceops_quantum.experiment.grid import PlannedRun, load_planned_runs

_ROOT = Path(__file__).resolve().parents[3]


class GridOutputError(FileExistsError):
    """The output directory already holds a previous run."""


def execute_grid(out_dir: Path) -> tuple[dict[str, object], ...]:
    """Run every locked cell once and write ``grid_summary.json``."""

    if out_dir.exists() and any(out_dir.iterdir()):
        raise GridOutputError(
            f"output directory is not empty: {out_dir}. Use a new directory."
        )
    runs = load_planned_runs()
    out_dir.mkdir(parents=True, exist_ok=True)
    outcomes: list[dict[str, object]] = []
    for index, run in enumerate(runs, start=1):
        print(f"[{index}/{len(runs)}] {run.experiment_id}", flush=True)
        outcome = execute_planned_run(run, out_dir)
        outcomes.append(outcome)
        print(f"  {outcome['status']}", flush=True)
        _write_summary(out_dir / "grid_summary.json", len(runs), outcomes)
    return tuple(outcomes)


def execute_planned_run(run: PlannedRun, out_dir: Path) -> dict[str, object]:
    """Archive one planned cell. Any exception stays in the returned record."""

    started = time.perf_counter()
    try:
        destination = _execute(run, out_dir)
    except Exception as exc:
        elapsed = time.perf_counter() - started
        destination = out_dir / run.experiment_id
        destination.mkdir(parents=True, exist_ok=True)
        payload = {
            "experiment_id": run.experiment_id,
            "status": "failed",
            "wall_time_sec": elapsed,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
        (destination / "failure.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        payload["directory"] = str(destination)
        return payload
    elapsed = time.perf_counter() - started
    metrics = json.loads((destination / "metrics.json").read_text(encoding="utf-8"))
    return {
        "experiment_id": run.experiment_id,
        "status": "ok",
        "directory": str(destination),
        "wall_time_sec": elapsed,
        "performance_metric": metrics["performance_metric"],
        "p_optimum": metrics["p_optimum"],
        "best_feasible_priority": metrics["best_feasible_priority"],
        "best_feasible_basis": metrics["best_feasible_basis"],
        "feasibility_rate": metrics["feasibility_rate"],
        "approx_ratio": metrics["approx_ratio"],
        "error": None,
    }


def _execute(run: PlannedRun, out_dir: Path) -> Path:
    scenario_path = _scenario_path(run)
    scenario = load_scenario(scenario_path)
    recorded_path = str(scenario_path)
    if run.method == "exact":
        started = time.perf_counter()
        result = solve_exact(scenario)
        elapsed = time.perf_counter() - started
        return write_experiment(
            out_dir,
            capture_classical(
                run.experiment_id,
                recorded_path,
                scenario,
                result,
                wall_time_sec=elapsed,
            ),
            scenario,
        )
    if run.method == "greedy":
        if run.seed is None:
            raise ValueError(f"{run.experiment_id} is missing a greedy seed")
        started = time.perf_counter()
        result = solve_greedy(scenario, "resource_density", run.seed)
        elapsed = time.perf_counter() - started
        return write_experiment(
            out_dir,
            capture_classical(
                run.experiment_id,
                recorded_path,
                scenario,
                result,
                wall_time_sec=elapsed,
            ),
            scenario,
        )
    if run.penalty is None or run.seed is None:
        raise ValueError(f"{run.experiment_id} is missing a penalty or seed")
    penalties = {"energy": run.penalty, "storage": run.penalty, "downlink": run.penalty}
    if run.method == "sampled":
        if run.shots is None or run.gamma is None or run.beta is None:
            raise ValueError(f"{run.experiment_id} is missing shots or fixed parameters")
        from spaceops_quantum.quantum.qaoa import sample_qaoa

        started = time.perf_counter()
        record = sample_qaoa(
            scenario,
            parameters=(run.gamma, run.beta),
            shots=run.shots,
            seed=run.seed,
            lambda_by_constraint=penalties,
        )
        elapsed = time.perf_counter() - started
        return write_experiment(
            out_dir,
            capture_sampled(
                run.experiment_id,
                recorded_path,
                scenario,
                record,
                penalties,
                wall_time_sec=elapsed,
            ),
            scenario,
        )
    if run.method == "optimized":
        if run.max_evaluations is None:
            raise ValueError(f"{run.experiment_id} is missing max_evaluations")
        from spaceops_quantum.experiment.optimized import capture_optimized_run

        capture = capture_optimized_run(
            run.experiment_id,
            recorded_path,
            scenario,
            seed=run.seed,
            max_evaluations=run.max_evaluations,
            penalties=penalties,
            initial_parameters=None,
        )
        return write_experiment(out_dir, capture, scenario)
    raise ValueError(f"unsupported planned method {run.method}")


def _scenario_path(run: PlannedRun) -> Path:
    path = Path(run.scenario_path)
    if path.is_absolute():
        return path
    return _ROOT / path


def _write_summary(path: Path, planned: int, outcomes: list[dict[str, object]]) -> None:
    failed = [item["experiment_id"] for item in outcomes if item["status"] != "ok"]
    payload = {
        "planned_runs": planned,
        "completed_runs": len(outcomes),
        "failed_runs": failed,
        "outcomes": outcomes,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
