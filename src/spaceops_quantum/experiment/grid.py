"""Expand the locked T15 manifest into planned runs.

This module does not execute QAOA and does not import Qiskit. The confirmatory
grid stays unrun until that manifest is accepted.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[3]


class GridManifestError(ValueError):
    """The locked manifest is missing a field or has the wrong shape."""


@dataclass(frozen=True, slots=True)
class PlannedRun:
    """One archive that the confirmatory grid will write later."""

    experiment_id: str
    scenario_label: str
    scenario_path: str
    logical_qubits: int
    method: str
    penalty: int | None
    seed: int | None
    shots: int | None
    parameter_source: str
    max_evaluations: int | None
    gamma: float | None
    beta: float | None

    @property
    def statevector_evaluations(self) -> int:
        if self.method == "sampled":
            return 1
        if self.method == "optimized":
            if self.max_evaluations is None:
                raise GridManifestError(f"{self.experiment_id} is missing max_evaluations")
            return self.max_evaluations
        return 0


def load_planned_runs(path: Path | None = None) -> tuple[PlannedRun, ...]:
    """Read the manifest and return every planned run in stable order."""

    manifest_path = _ROOT / "configs" / "t15_grid.yaml" if path is None else path
    document = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    data = _mapping(document, "grid")
    _require(data, "p")
    if data["p"] != 1:
        raise GridManifestError(f"confirmatory grid is locked at p=1, got {data['p']!r}")
    penalties = _ints(data, "penalties")
    seeds = _ints(data, "seeds")
    shot_counts = _ints(data, "shot_counts")
    fixed = _mapping(data.get("fixed_parameters"), "fixed_parameters")
    gamma = _number(fixed, "gamma")
    beta = _number(fixed, "beta")
    optimizer = _mapping(data.get("optimizer"), "optimizer")
    search_budget = _int(optimizer, "confirmatory_max_evaluations")
    budget_values = _ints(optimizer, "budget_arm_max_evaluations")
    budget_penalty = _int(optimizer, "budget_arm_penalty")
    budget_seed = _int(optimizer, "budget_arm_seed")
    shot_penalty = _int(data, "shot_arm_penalty")
    classical = _mapping(data.get("classical"), "classical")
    greedy_seed = _int(classical, "greedy_seed")
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise GridManifestError("scenarios must be a non-empty list")
    runs: list[PlannedRun] = []
    for item in scenarios:
        scenario = _mapping(item, "scenario")
        label = _text(scenario, "label")
        scenario_path = _text(scenario, "path")
        qubits = _int(scenario, "logical_qubits")
        runs.append(
            PlannedRun(
                experiment_id=f"{label}-exact",
                scenario_label=label,
                scenario_path=scenario_path,
                logical_qubits=qubits,
                method="exact",
                penalty=None,
                seed=None,
                shots=None,
                parameter_source="none",
                max_evaluations=None,
                gamma=None,
                beta=None,
            )
        )
        runs.append(
            PlannedRun(
                experiment_id=f"{label}-greedy",
                scenario_label=label,
                scenario_path=scenario_path,
                logical_qubits=qubits,
                method="greedy",
                penalty=None,
                seed=greedy_seed,
                shots=None,
                parameter_source="none",
                max_evaluations=None,
                gamma=None,
                beta=None,
            )
        )
        for penalty in penalties:
            for seed in seeds:
                runs.append(
                    PlannedRun(
                        experiment_id=f"{label}-penalty-l{penalty}-seed{seed}",
                        scenario_label=label,
                        scenario_path=scenario_path,
                        logical_qubits=qubits,
                        method="optimized",
                        penalty=penalty,
                        seed=seed,
                        shots=None,
                        parameter_source="optimizer",
                        max_evaluations=search_budget,
                        gamma=None,
                        beta=None,
                    )
                )
        for shots in shot_counts:
            for seed in seeds:
                runs.append(
                    PlannedRun(
                        experiment_id=f"{label}-shots-{shots}-seed{seed}",
                        scenario_label=label,
                        scenario_path=scenario_path,
                        logical_qubits=qubits,
                        method="sampled",
                        penalty=shot_penalty,
                        seed=seed,
                        shots=shots,
                        parameter_source="fixed",
                        max_evaluations=None,
                        gamma=gamma,
                        beta=beta,
                    )
                )
        for evaluations in budget_values:
            runs.append(
                PlannedRun(
                    experiment_id=f"{label}-budget-e{evaluations}",
                    scenario_label=label,
                    scenario_path=scenario_path,
                    logical_qubits=qubits,
                    method="optimized",
                    penalty=budget_penalty,
                    seed=budget_seed,
                    shots=None,
                    parameter_source="optimizer",
                    max_evaluations=evaluations,
                    gamma=None,
                    beta=None,
                )
            )
    identities = [run.experiment_id for run in runs]
    if len(identities) != len(set(identities)):
        raise GridManifestError("planned experiment ids are not unique")
    return tuple(runs)


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GridManifestError(f"{label} must be a mapping")
    return value


def _require(data: dict[str, Any], key: str) -> None:
    if key not in data:
        raise GridManifestError(f"missing {key}")


def _ints(data: dict[str, Any], key: str) -> tuple[int, ...]:
    _require(data, key)
    value = data[key]
    if not isinstance(value, list) or not value:
        raise GridManifestError(f"{key} must be a non-empty list")
    return tuple(_plain_int(item, key) for item in value)


def _int(data: dict[str, Any], key: str) -> int:
    _require(data, key)
    return _plain_int(data[key], key)


def _plain_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise GridManifestError(f"{label} must be an integer, got {value!r}")
    return value


def _number(data: dict[str, Any], key: str) -> float:
    _require(data, key)
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GridManifestError(f"{key} must be a number, got {value!r}")
    return float(value)


def _text(data: dict[str, Any], key: str) -> str:
    _require(data, key)
    value = data[key]
    if not isinstance(value, str) or value == "":
        raise GridManifestError(f"{key} must be a non-empty string")
    return value
