"""T14 archive schema for classical solves and an empty feasible shot set."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import pytest

from spaceops_quantum.classical import solve_exact, solve_greedy
from spaceops_quantum.cli import main
from spaceops_quantum.domain import Resources, Scenario, Task, parse_scenario
from spaceops_quantum.encoding import build_qubo, scenario_hash
from spaceops_quantum.experiment import (
    ExperimentArchiveError,
    capture_classical,
    capture_optimized,
    capture_sampled,
    write_experiment,
)
from spaceops_quantum.quantum import BackendSample, build_sampled_record

FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_PENALTIES = {"energy": 6, "storage": 0, "downlink": 0}


def test_exact_archive_links_the_fixture_hash_and_version(tmp_path: Path) -> None:
    from spaceops_quantum.domain import load_scenario

    scenario = load_scenario(FIXTURE)
    result = solve_exact(scenario)
    destination = write_experiment(
        tmp_path,
        capture_classical("exact-f0", str(FIXTURE), scenario, result, wall_time_sec=0.25),
        scenario,
    )
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((destination / "metrics.json").read_text(encoding="utf-8"))
    samples = [
        json.loads(line)
        for line in (destination / "samples.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    with (destination / "summary.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    snapshot = json.loads((destination / "scenario.json").read_text(encoding="utf-8"))
    restored = parse_scenario(snapshot)
    assert manifest["schema_version"] == 2
    assert manifest["scenario_file"] == "scenario.json"
    assert scenario_hash(restored) == manifest["scenario_hash"]
    assert snapshot["budgets"] == {"downlink": 10, "energy": 10, "storage": 10}
    assert [task["id"] for task in snapshot["tasks"]] == ["T1", "T2", "T3", "T4", "T5", "T6"]
    assert snapshot["reference"]["optimal_priority"] == 27
    assert manifest["experiment_id"] == "exact-f0"
    assert manifest["scenario_path"] == str(FIXTURE)
    assert manifest["scenario_id"] == "eo-six-tasks-v1"
    assert manifest["scenario_hash"] == scenario_hash(scenario)
    assert manifest["packages"]["spaceops-quantum"] == "0.1.0"
    assert manifest["seed"] is None
    assert manifest["parameter_source"] == "none"
    assert manifest["optimizer_max_evaluations"] is None
    assert _TIMESTAMP.match(manifest["timestamp_utc"])
    assert metrics["best_feasible_priority"] == 27
    assert metrics["best_feasible_task_ids"] == ["T1", "T2", "T5", "T6"]
    assert metrics["feasible_subsets"] == 37
    assert metrics["total_subsets"] == 64
    assert metrics["approx_ratio"] == 1
    assert metrics["relative_gap"] == 0
    assert metrics["p_optimum"] is None
    assert metrics["p_optimum_definition"] == "not-a-sample"
    assert metrics["feasibility_rate"] is None
    assert metrics["circuit_depth_sensitivity"] == "not-yet-evaluated"
    assert len(samples) == 1
    assert samples[0]["feasible"] is True
    assert samples[0]["priority"] == 27
    assert samples[0]["used"] == {"downlink": 10, "energy": 9, "storage": 10}
    assert samples[0]["violations"] == {"downlink": 0, "energy": 0, "storage": 0}
    assert samples[0]["equality_residual"] is None
    assert samples[0]["qubo_energy"] is None
    assert metrics["wall_time_sec"] == 0.25
    assert metrics["optimizer_time_sec"] is None
    assert metrics["transpile_time_sec"] is None
    assert rows[0]["experiment_id"] == "exact-f0"
    assert rows[0]["p_optimum_definition"] == "not-a-sample"
    assert "qiskit" not in sys.modules


def test_greedy_gap_is_measured_against_the_oracle(tmp_path: Path) -> None:
    scenario = Scenario(
        schema_version=1,
        scenario_id="greedy-gap",
        description="greedy misses the optimum",
        budgets=Resources(5, 0, 0),
        tasks=(
            Task("A", priority=6, energy=4, storage=0, downlink=0),
            Task("B", priority=5, energy=3, storage=0, downlink=0),
            Task("C", priority=5, energy=3, storage=0, downlink=0),
        ),
    )
    result = solve_greedy(scenario, "resource_density", 4)
    destination = write_experiment(
        tmp_path,
        capture_classical(
            "greedy-gap",
            "memory://greedy-gap",
            scenario,
            result,
            wall_time_sec=0.1,
        ),
        scenario,
    )
    metrics = json.loads((destination / "metrics.json").read_text(encoding="utf-8"))
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["seed"] == 4
    assert metrics["best_feasible_task_ids"] == ["B"]
    assert metrics["best_feasible_priority"] == 5
    assert metrics["approx_ratio"] == pytest.approx(5 / 6)
    assert metrics["relative_gap"] == pytest.approx(1 / 6)
    assert metrics["feasible_subsets"] is None
    assert metrics["p_optimum"] is None


def test_infeasible_shots_stay_in_the_archive(tmp_path: Path) -> None:
    scenario = Scenario(
        schema_version=1,
        scenario_id="sampled-two-tasks",
        description="two tasks sharing one energy unit",
        budgets=Resources(1, 0, 0),
        tasks=(
            Task("A", priority=3, energy=1, storage=0, downlink=0),
            Task("B", priority=2, energy=1, storage=0, downlink=0),
        ),
    )
    shots = 4
    record = build_sampled_record(
        scenario,
        build_qubo(scenario, _PENALTIES),
        (BackendSample(bits=(1, 1, 0), probability=1.0, count=shots),),
        p=1,
        seed=0,
        shots=shots,
        backend="aer-sampled",
        parameters=(0.2, 0.3),
        versions=(),
    )
    destination = write_experiment(
        tmp_path,
        capture_sampled(
            "no-feasible",
            "memory://pair",
            scenario,
            record,
            _PENALTIES,
            wall_time_sec=0.2,
        ),
        scenario,
    )
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((destination / "metrics.json").read_text(encoding="utf-8"))
    sample = json.loads((destination / "samples.jsonl").read_text(encoding="utf-8"))

    assert manifest["parameter_source"] == "fixed"
    assert manifest["optimizer_max_evaluations"] is None
    assert manifest["shots"] == 4
    assert manifest["seed"] == 0
    assert manifest["p"] == 1
    assert manifest["penalties"] == {"downlink": 0, "energy": 6, "storage": 0}
    assert metrics["best_feasible_priority"] is None
    assert metrics["best_feasible_task_ids"] is None
    assert metrics["feasibility_rate"] == 0
    assert metrics["approx_ratio"] is None
    assert metrics["relative_gap"] is None
    assert metrics["p_optimum"] == 0
    assert metrics["p_optimum_definition"] == "shot-frequency"
    assert sample["feasible"] is False
    assert sample["priority"] == 5
    assert sample["count"] == 4
    assert sample["violations"]["energy"] == 1
    assert sample["equality_residual"]["energy"] == 1
    assert sample["equality_satisfied"] is False
    assert isinstance(sample["qubo_energy"], int)
    assert metrics["wall_time_sec"] == 0.2
    assert metrics["optimizer_time_sec"] is None
    assert manifest["optimizer_trace_file"] is None


def test_broken_slack_equality_is_not_a_budget_violation(tmp_path: Path) -> None:
    scenario = Scenario(
        schema_version=1,
        scenario_id="slack-gap",
        description="feasible task with the wrong slack",
        budgets=Resources(1, 0, 0),
        tasks=(Task("A", priority=3, energy=1, storage=0, downlink=0),),
    )
    record = build_sampled_record(
        scenario,
        build_qubo(scenario, _PENALTIES),
        (BackendSample(bits=(1, 1), probability=1.0, count=1),),
        p=1,
        seed=0,
        shots=1,
        backend="aer-sampled",
        parameters=(0.0, 0.0),
        versions=(),
    )
    destination = write_experiment(
        tmp_path,
        capture_sampled(
            "slack-gap",
            "memory://slack",
            scenario,
            record,
            _PENALTIES,
            wall_time_sec=0,
        ),
        scenario,
    )
    sample = json.loads((destination / "samples.jsonl").read_text(encoding="utf-8"))
    assert sample["feasible"] is True
    assert sample["violations"]["energy"] == 0
    assert sample["equality_residual"]["energy"] == 1
    assert sample["equality_satisfied"] is False
    assert sample["weighted_penalty"] == 6


def test_optimizer_provenance_is_separate_from_fixed_sampling(tmp_path: Path) -> None:
    scenario = Scenario(
        schema_version=1,
        scenario_id="optimizer-schema",
        description="schema only",
        budgets=Resources(1, 0, 0),
        tasks=(
            Task("A", priority=3, energy=1, storage=0, downlink=0),
            Task("B", priority=2, energy=1, storage=0, downlink=0),
        ),
    )
    sampled = capture_sampled(
        "ignored",
        "memory://schema",
        scenario,
        build_sampled_record(
            scenario,
            build_qubo(scenario, _PENALTIES),
            (BackendSample(bits=(1, 1, 0), probability=1.0, count=2),),
            p=1,
            seed=0,
            shots=2,
            backend="aer-sampled",
            parameters=(0.0, 0.0),
            versions=(),
        ),
        _PENALTIES,
        wall_time_sec=0,
    )
    destination = write_experiment(
        tmp_path,
        capture_optimized(
            "optimized-schema",
            "memory://schema",
            scenario,
            sampled.samples,
            backend="aer-statevector",
            seed=3,
            p=1,
            parameters=(0.1, 0.2),
            penalties=_PENALTIES,
            max_evaluations=2,
            trace=((0, (0.0, 0.0), 4.0), (1, (0.1, 0.2), 3.5)),
            feasibility_rate=0.0,
            p_optimum=0.0,
            wall_time_sec=0.4,
        ),
        scenario,
    )
    metrics = json.loads((destination / "metrics.json").read_text(encoding="utf-8"))
    trace = json.loads((destination / "optimizer_trace.json").read_text(encoding="utf-8"))
    assert metrics["parameter_source"] == "optimizer"
    assert metrics["optimizer_max_evaluations"] == 2
    assert metrics["p_optimum_definition"] == "statevector-probability"
    assert metrics["optimizer_time_sec"] == 0.4
    assert metrics["wall_time_sec"] == 0.4
    assert trace[1]["parameters"] == [0.1, 0.2]
    assert trace[1]["energy"] == 3.5


def test_experiment_id_cannot_escape_the_output_directory(tmp_path: Path) -> None:
    scenario = Scenario(
        schema_version=1,
        scenario_id="id-check",
        description="id check",
        budgets=Resources(1, 0, 0),
        tasks=(Task("A", priority=1, energy=1, storage=0, downlink=0),),
    )
    result = solve_exact(scenario)
    with pytest.raises(ExperimentArchiveError, match="path segment"):
        write_experiment(
            tmp_path,
            capture_classical("nested/id", "memory://id", scenario, result, wall_time_sec=0),
            scenario,
        )


def test_exact_cli_writes_an_archive_without_qiskit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out = tmp_path / "results"
    code = main(
        [
            "experiment",
            "run",
            "--method",
            "exact",
            "--scenario",
            str(FIXTURE),
            "--out",
            str(out),
            "--id",
            "cli-exact",
        ]
    )
    assert code == 0
    assert "cli-exact" in capsys.readouterr().out
    manifest = json.loads((out / "cli-exact" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scenario_hash"]
    assert manifest["solver"] == "exact"
    metrics = json.loads((out / "cli-exact" / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["wall_time_sec"] >= 0
    assert (out / "cli-exact" / "scenario.json").is_file()
    assert "qiskit" not in sys.modules
