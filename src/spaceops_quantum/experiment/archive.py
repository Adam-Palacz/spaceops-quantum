"""Write one experiment archive.

The directory holds a manifest, one JSON object per evaluated sample, metrics,
and a one-row CSV summary. A classical solve is not a shot frequency:
``p_optimum`` stays null and ``p_optimum_definition`` is ``not-a-sample``.
A fixed-parameter shot run stores ``shot-frequency`` and leaves
``optimizer_max_evaluations`` null, so sampling is not confused with a search.
This module does not import Qiskit.
"""

from __future__ import annotations

import csv
import json
import platform
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from spaceops_quantum.classical import ClassicalResult, solve_exact
from spaceops_quantum.domain.models import Scenario
from spaceops_quantum.encoding.qubo import scenario_hash
from spaceops_quantum.quantum.sampling import SampledRunRecord

_PACKAGES = ("spaceops-quantum", "qiskit", "qiskit-aer")
_SCHEMA_VERSION = 1


class ExperimentArchiveError(ValueError):
    """An experiment archive request is incomplete or would hide a result."""


@dataclass(frozen=True, slots=True)
class ArchivedSample:
    """One decoded row. Infeasible rows stay in the file."""

    bits: tuple[int, ...] | None
    count: int | None
    probability: float | None
    selected_task_ids: tuple[str, ...]
    task_bits: tuple[int, ...]
    priority: int
    feasible: bool
    energy: int
    storage: int
    downlink: int
    violation_energy: int
    violation_storage: int
    violation_downlink: int


@dataclass(frozen=True, slots=True)
class ExperimentCapture:
    """Everything the archive writes, before provenance is added."""

    experiment_id: str
    scenario_path: str
    scenario_id: str
    scenario_hash: str
    solver: str
    backend: str
    seed: int | None
    shots: int | None
    p: int | None
    parameter_source: str
    optimizer_max_evaluations: int | None
    parameters: tuple[float, ...] | None
    penalties: tuple[tuple[str, int], ...] | None
    samples: tuple[ArchivedSample, ...]
    best_feasible_priority: int | None
    best_feasible_task_ids: tuple[str, ...] | None
    feasibility_rate: float | None
    approx_ratio: float | None
    relative_gap: float | None
    p_optimum: float | None
    p_optimum_definition: str
    feasible_subsets: int | None
    total_subsets: int | None
    examined_subsets: int | None


def capture_classical(
    experiment_id: str,
    scenario_path: str,
    scenario: Scenario,
    result: ClassicalResult,
) -> ExperimentCapture:
    """Record one exact or greedy solve against the exhaustive optimum."""

    if result.method not in ("exact", "greedy"):
        raise ExperimentArchiveError(f"unsupported classical method {result.method}")
    if result.scenario_id != scenario.scenario_id:
        raise ExperimentArchiveError("classical result does not match the scenario")
    optimum = solve_exact(scenario).solution
    solution = result.solution
    ratio, gap = _ratios(solution.priority if solution.feasible else None, optimum.priority)
    sample = ArchivedSample(
        bits=None,
        count=None,
        probability=None,
        selected_task_ids=solution.selected_task_ids,
        task_bits=solution.bit_vector,
        priority=solution.priority,
        feasible=solution.feasible,
        energy=solution.used.energy,
        storage=solution.used.storage,
        downlink=solution.used.downlink,
        violation_energy=solution.violations.energy,
        violation_storage=solution.violations.storage,
        violation_downlink=solution.violations.downlink,
    )
    best_ids = solution.selected_task_ids if solution.feasible else None
    best_priority = solution.priority if solution.feasible else None
    return ExperimentCapture(
        experiment_id=experiment_id,
        scenario_path=scenario_path,
        scenario_id=scenario.scenario_id,
        scenario_hash=scenario_hash(scenario),
        solver=result.method,
        backend="classical",
        seed=result.seed,
        shots=None,
        p=None,
        parameter_source="none",
        optimizer_max_evaluations=None,
        parameters=None,
        penalties=None,
        samples=(sample,),
        best_feasible_priority=best_priority,
        best_feasible_task_ids=best_ids,
        feasibility_rate=None,
        approx_ratio=ratio,
        relative_gap=gap,
        p_optimum=None,
        p_optimum_definition="not-a-sample",
        feasible_subsets=result.feasible_subsets,
        total_subsets=result.total_subsets,
        examined_subsets=result.examined_subsets,
    )


def capture_sampled(
    experiment_id: str,
    scenario_path: str,
    scenario: Scenario,
    record: SampledRunRecord,
    penalties: Mapping[str, int],
) -> ExperimentCapture:
    """Record fixed-parameter shots. The optimizer budget stays null."""

    digest = scenario_hash(scenario)
    if record.scenario_hash != digest or record.scenario_id != scenario.scenario_id:
        raise ExperimentArchiveError("sampled record does not match the scenario")
    rows = tuple(
        ArchivedSample(
            bits=shot.bits,
            count=shot.count,
            probability=shot.probability,
            selected_task_ids=shot.assessment.selected_task_ids,
            task_bits=shot.assessment.task_bits,
            priority=shot.assessment.priority,
            feasible=shot.assessment.task_feasible,
            energy=shot.assessment.used.energy,
            storage=shot.assessment.used.storage,
            downlink=shot.assessment.used.downlink,
            violation_energy=shot.assessment.violations.energy,
            violation_storage=shot.assessment.violations.storage,
            violation_downlink=shot.assessment.violations.downlink,
        )
        for shot in record.samples
    )
    return ExperimentCapture(
        experiment_id=experiment_id,
        scenario_path=scenario_path,
        scenario_id=scenario.scenario_id,
        scenario_hash=digest,
        solver="qaoa-sampled",
        backend=record.backend,
        seed=record.seed,
        shots=record.shots,
        p=record.p,
        parameter_source="fixed",
        optimizer_max_evaluations=None,
        parameters=record.parameters,
        penalties=tuple(sorted(penalties.items())),
        samples=rows,
        best_feasible_priority=record.best_feasible_priority,
        best_feasible_task_ids=record.best_feasible_task_ids,
        feasibility_rate=record.feasibility_rate,
        approx_ratio=record.approx_ratio,
        relative_gap=record.relative_gap,
        p_optimum=record.sampled_optimum_probability,
        p_optimum_definition="shot-frequency",
        feasible_subsets=None,
        total_subsets=None,
        examined_subsets=None,
    )


def write_experiment(out_dir: Path, capture: ExperimentCapture) -> Path:
    """Create ``out_dir/experiment_id`` and write the four archive files."""

    experiment_id = _require_id(capture.experiment_id)
    destination = out_dir / experiment_id
    if destination.exists():
        raise ExperimentArchiveError(f"experiment directory already exists: {destination}")
    destination.mkdir(parents=True)
    manifest = _manifest(capture)
    metrics = _metrics(capture)
    _write_json(destination / "manifest.json", manifest)
    _write_json(destination / "metrics.json", metrics)
    _write_samples(destination / "samples.jsonl", capture.samples)
    _write_summary(destination / "summary.csv", metrics)
    return destination


def _manifest(capture: ExperimentCapture) -> dict[str, object]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "experiment_id": capture.experiment_id,
        "timestamp_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scenario_path": capture.scenario_path,
        "scenario_id": capture.scenario_id,
        "scenario_hash": capture.scenario_hash,
        "git_sha": _git_sha(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": _packages(),
        "solver": capture.solver,
        "backend": capture.backend,
        "seed": capture.seed,
        "shots": capture.shots,
        "p": capture.p,
        "parameter_source": capture.parameter_source,
        "optimizer_max_evaluations": capture.optimizer_max_evaluations,
        "parameters": None if capture.parameters is None else list(capture.parameters),
        "penalties": None if capture.penalties is None else dict(capture.penalties),
    }


def _metrics(capture: ExperimentCapture) -> dict[str, object]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "experiment_id": capture.experiment_id,
        "scenario_hash": capture.scenario_hash,
        "solver": capture.solver,
        "backend": capture.backend,
        "seed": capture.seed,
        "shots": capture.shots,
        "p": capture.p,
        "parameter_source": capture.parameter_source,
        "optimizer_max_evaluations": capture.optimizer_max_evaluations,
        "best_feasible_priority": capture.best_feasible_priority,
        "best_feasible_task_ids": (
            None
            if capture.best_feasible_task_ids is None
            else list(capture.best_feasible_task_ids)
        ),
        "feasibility_rate": capture.feasibility_rate,
        "approx_ratio": capture.approx_ratio,
        "relative_gap": capture.relative_gap,
        "p_optimum": capture.p_optimum,
        "p_optimum_definition": capture.p_optimum_definition,
        "feasible_subsets": capture.feasible_subsets,
        "total_subsets": capture.total_subsets,
        "examined_subsets": capture.examined_subsets,
        "sample_count": len(capture.samples),
        "circuit_depth_sensitivity": "not-yet-evaluated",
    }


def _sample_object(sample: ArchivedSample) -> dict[str, object]:
    return {
        "bits": None if sample.bits is None else list(sample.bits),
        "count": sample.count,
        "probability": sample.probability,
        "selected_task_ids": list(sample.selected_task_ids),
        "task_bits": list(sample.task_bits),
        "priority": sample.priority,
        "feasible": sample.feasible,
        "used": {
            "energy": sample.energy,
            "storage": sample.storage,
            "downlink": sample.downlink,
        },
        "violations": {
            "energy": sample.violation_energy,
            "storage": sample.violation_storage,
            "downlink": sample.violation_downlink,
        },
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_samples(path: Path, samples: tuple[ArchivedSample, ...]) -> None:
    lines = [json.dumps(_sample_object(sample), sort_keys=True) for sample in samples]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _write_summary(path: Path, metrics: dict[str, object]) -> None:
    fieldnames = (
        "experiment_id",
        "scenario_hash",
        "solver",
        "backend",
        "seed",
        "shots",
        "p",
        "parameter_source",
        "optimizer_max_evaluations",
        "best_feasible_priority",
        "feasibility_rate",
        "approx_ratio",
        "relative_gap",
        "p_optimum",
        "p_optimum_definition",
        "circuit_depth_sensitivity",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {name: "" if metrics[name] is None else metrics[name] for name in fieldnames}
        )


def _ratios(value: int | None, optimum: int) -> tuple[float | None, float | None]:
    if value is None or optimum <= 0:
        return None, None
    return value / optimum, (optimum - value) / optimum


def _packages() -> dict[str, str]:
    found: dict[str, str] = {}
    for name in _PACKAGES:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            continue
    return found


def _git_sha() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    sha = completed.stdout.strip()
    if len(sha) != 40:
        return None
    return sha


def _require_id(experiment_id: str) -> str:
    escaped = not experiment_id or any(character in experiment_id for character in "\\/")
    if escaped or experiment_id in (".", ".."):
        raise ExperimentArchiveError(
            f"experiment id must be a single path segment, got {experiment_id!r}"
        )
    return experiment_id
