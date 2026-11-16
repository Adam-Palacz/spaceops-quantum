"""The T15 manifest is locked and is not executed here."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from spaceops_quantum.classical import solve_exact
from spaceops_quantum.domain import evaluate_solution, load_scenario
from spaceops_quantum.encoding import build_qubo
from spaceops_quantum.experiment.grid import load_planned_runs

_ROOT = Path(__file__).resolve().parents[2]


def test_grid_refuses_a_populated_directory(tmp_path: Path) -> None:
    from spaceops_quantum.experiment.execute import GridOutputError, execute_grid

    (tmp_path / "previous.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(GridOutputError, match="not empty"):
        execute_grid(tmp_path)
    assert (tmp_path / "previous.txt").read_text(encoding="utf-8") == "keep"
    assert not (tmp_path / "grid_summary.json").exists()
    assert "qiskit" not in sys.modules


def test_exact_grid_cell_archives_without_qiskit(tmp_path: Path) -> None:
    from spaceops_quantum.experiment.execute import execute_planned_run

    run = next(item for item in load_planned_runs() if item.experiment_id == "f1-exact")
    outcome = execute_planned_run(run, tmp_path)
    assert outcome["status"] == "ok"
    metrics = json.loads((tmp_path / "f1-exact" / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["best_feasible_priority"] == 5
    assert metrics["performance_metric"] == "objective"
    assert "qiskit" not in sys.modules


def test_locked_grid_counts_runs_and_does_not_execute_qaoa() -> None:
    runs = load_planned_runs()
    assert len(runs) == 66
    assert len({run.experiment_id for run in runs}) == 66
    assert sum(run.statevector_evaluations for run in runs) == 951
    methods = {run.method for run in runs}
    assert methods == {"exact", "greedy", "optimized", "sampled"}
    penalties = {run.penalty for run in runs if run.method == "optimized"}
    assert penalties == {5, 10, 20, 41}
    shots = {run.shots for run in runs if run.method == "sampled"}
    assert shots == {256, 1024}
    fixed = [run for run in runs if run.method == "sampled"]
    assert {(run.gamma, run.beta) for run in fixed} == {(0.1, 0.2)}
    assert {run.parameter_source for run in fixed} == {"fixed"}
    assert {run.max_evaluations for run in fixed} == {None}
    assert {run.penalty for run in fixed} == {41}
    search = [
        run
        for run in runs
        if run.method == "optimized" and run.experiment_id.find("-penalty-") >= 0
    ]
    assert {run.max_evaluations for run in search} == {25}
    assert {run.seed for run in search} == {0, 1, 2}
    budgets = [run for run in runs if "-budget-" in run.experiment_id]
    assert {run.max_evaluations for run in budgets} == {1, 10}
    assert {run.seed for run in budgets} == {0}
    assert {run.penalty for run in budgets} == {41}
    assert "qiskit" not in sys.modules


def test_f1_counts_both_optima_and_f2_f3_are_unique() -> None:
    expected = {
        "configs/f1_three_tasks.yaml": (6, 5, 2, 4, 8),
        "configs/f2_six_tasks.yaml": (9, 18, 1, 16, 64),
        "configs/f3_six_tasks.yaml": (12, 17, 1, 13, 64),
    }
    for relative, (qubits, priority, n_optima, feasible, total) in expected.items():
        scenario = load_scenario(_ROOT / relative)
        result = solve_exact(scenario)
        assert result.solution.priority == priority
        assert result.feasible_subsets == feasible
        assert result.total_subsets == total
        assert scenario.reference is not None
        assert scenario.reference.optimal_priority == priority
        assert scenario.reference.selected_task_ids == result.solution.selected_task_ids
        optima = []
        for mask in range(1 << len(scenario.tasks)):
            bits = tuple((mask >> index) & 1 for index in range(len(scenario.tasks)))
            evaluation = evaluate_solution(scenario, bits)
            if evaluation.feasible and evaluation.priority == priority:
                optima.append(evaluation.selected_task_ids)
        assert len(optima) == n_optima
        assert build_qubo(
            scenario, {"energy": 41, "storage": 41, "downlink": 41}
        ).n_logical_qubits == qubits
    assert "qiskit" not in sys.modules
