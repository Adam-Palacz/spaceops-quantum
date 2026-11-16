"""Build a sanitized aggregate from an existing T15 archive.

This reads archived samples and enumerates QUBO minima classically. It does
not call Qiskit and does not rerun the grid.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import median

from spaceops_quantum.domain import parse_scenario
from spaceops_quantum.encoding import build_qubo, find_qubo_minima
from spaceops_quantum.experiment.baseline import (
    probability_on_bitstrings,
    uniform_task_baseline,
)
from spaceops_quantum.experiment.charts import write_charts

_SCHEMA_VERSION = 1


def publish(results_dir: Path, destination: Path) -> Path:
    """Write ``t15-v1.json`` and the SVG charts under ``destination``."""

    payload = build_aggregate(results_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "t15-v1.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_charts(payload, destination)
    return path


def build_aggregate(results_dir: Path) -> dict[str, object]:
    """Summarize one finished grid directory."""

    cells: list[dict[str, object]] = []
    minima_cache: dict[tuple[str, int], tuple[int, tuple[tuple[int, ...], ...]]] = {}
    uniform_cache: dict[str, dict[str, object]] = {}
    git_shas: set[str] = set()
    packages: dict[str, str] | None = None
    for child in sorted(path for path in results_dir.iterdir() if path.is_dir()):
        metrics_path = child / "metrics.json"
        if not metrics_path.is_file():
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        manifest = json.loads((child / "manifest.json").read_text(encoding="utf-8"))
        if isinstance(manifest.get("git_sha"), str):
            git_shas.add(manifest["git_sha"])
        if packages is None and isinstance(manifest.get("packages"), dict):
            packages = {str(key): str(value) for key, value in manifest["packages"].items()}
        scenario = parse_scenario(
            json.loads((child / "scenario.json").read_text(encoding="utf-8"))
        )
        baseline = uniform_cache.get(scenario.scenario_id)
        if baseline is None:
            uniform = uniform_task_baseline(scenario)
            exact = f"{uniform.probability.numerator}/{uniform.probability.denominator}"
            baseline = {
                "optimal_task_subsets": uniform.optimal_task_subsets,
                "p_uniform": float(uniform.probability),
                "p_uniform_exact": exact,
                "task_subsets": uniform.task_subsets,
            }
            uniform_cache[scenario.scenario_id] = baseline
        cell: dict[str, object] = {
            "best_feasible_basis": metrics["best_feasible_basis"],
            "experiment_id": metrics["experiment_id"],
            "feasibility_rate": metrics["feasibility_rate"],
            "p_optimum": metrics["p_optimum"],
            "p_uniform": baseline["p_uniform"],
            "p_uniform_exact": baseline["p_uniform_exact"],
            "performance_metric": metrics["performance_metric"],
            "scenario_id": scenario.scenario_id,
            "seed": metrics["seed"],
            "shots": metrics["shots"],
        }
        penalties = manifest.get("penalties")
        if penalties is None or metrics["p_optimum"] is None:
            cell["p_ground_state"] = None
            cell["p_optimum_over_uniform"] = None
            cell["ground_state_energy"] = None
            cell["archived_probability_mass"] = None
        else:
            penalty = int(penalties["energy"])
            cache_key = (scenario.scenario_id, penalty)
            if cache_key not in minima_cache:
                model = build_qubo(
                    scenario,
                    {"downlink": penalty, "energy": penalty, "storage": penalty},
                )
                minima = find_qubo_minima(model, scenario)
                minima_cache[cache_key] = (minima.energy, minima.bitstrings)
            energy, bitstrings = minima_cache[cache_key]
            rows, mass = _sample_rows(child / "samples.jsonl")
            ground = probability_on_bitstrings(rows, set(bitstrings))
            cell["archived_probability_mass"] = mass
            cell["ground_state_energy"] = energy
            cell["p_ground_state"] = ground
            cell["p_optimum_over_uniform"] = float(metrics["p_optimum"]) / float(
                baseline["p_uniform"]
            )
            cell["penalty"] = penalty
        cells.append(cell)
    masses = [
        float(cell["archived_probability_mass"])
        for cell in cells
        if cell["archived_probability_mass"] is not None
    ]
    return {
        "cells": cells,
        "grid_id": "t15-confirmatory-v1",
        "provenance": {
            "archive_schema_version": 2,
            "cell_count": len(cells),
            "git_shas": sorted(git_shas),
            "min_archived_probability_mass": min(masses) if masses else None,
            "omitted": "absolute paths, credentials, and raw sample bitstrings",
            "packages": packages,
        },
        "schema_version": _SCHEMA_VERSION,
        "source": "archived T15 grid, not a new QAOA execution",
        "summary": _summary(cells),
        "uniform_task_baseline": uniform_cache,
    }


def _sample_rows(path: Path) -> tuple[tuple[tuple[tuple[int, ...], float], ...], float]:
    rows: list[tuple[tuple[int, ...], float]] = []
    mass = 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == "":
            continue
        sample = json.loads(line)
        probability = float(sample["probability"])
        rows.append((tuple(sample["bits"]), probability))
        mass += probability
    return tuple(rows), mass


def _summary(cells: list[dict[str, object]]) -> dict[str, object]:
    penalty_groups: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    shot_groups: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for cell in cells:
        if cell["p_ground_state"] is None:
            continue
        scenario = str(cell["scenario_id"])
        penalty = int(cell["penalty"])
        if cell["performance_metric"] == "statevector-probability" and cell["shots"] is None:
            if "penalty" in str(cell["experiment_id"]):
                penalty_groups[(scenario, penalty)].append(cell)
        if cell["performance_metric"] == "shot-frequency":
            shot_groups[(scenario, int(cell["shots"]))].append(cell)
    return {
        "ideal_penalty": [
            _group(scenario, penalty, group)
            for (scenario, penalty), group in sorted(penalty_groups.items())
        ],
        "shots": [
            _group(scenario, shots, group)
            for (scenario, shots), group in sorted(shot_groups.items())
        ],
    }


def _group(scenario: str, key: int, group: list[dict[str, object]]) -> dict[str, object]:
    return {
        "key": key,
        "n": len(group),
        "p_ground_state_median": median(float(item["p_ground_state"]) for item in group),
        "p_optimum_median": median(float(item["p_optimum"]) for item in group),
        "p_optimum_over_uniform_median": median(
            float(item["p_optimum_over_uniform"]) for item in group
        ),
        "scenario_id": scenario,
    }
