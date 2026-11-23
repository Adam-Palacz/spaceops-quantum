"""T19 grid accounting stays classical until a cell function is injected."""

from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest

from spaceops_quantum.domain import load_scenario
from spaceops_quantum.experiment.baseline import uniform_task_baseline
from spaceops_quantum.experiment.f2_pilot import PilotError
from spaceops_quantum.experiment.t19_grid import (
    binomial_standard_error,
    execute_cells,
    main,
    planned_cells,
    slurm_request,
)

_ROOT = Path(__file__).resolve().parents[2]


def test_import_does_not_load_qiskit() -> None:
    text = (_ROOT / "src" / "spaceops_quantum" / "experiment" / "t19_grid.py").read_text(
        encoding="utf-8"
    )
    assert "direct_access" not in text
    assert ".cloud(" not in text
    assert "qiskit" not in sys.modules


def test_plan_and_request_stay_on_the_cpu_partition() -> None:
    cells = planned_cells()
    assert len(cells) == 6
    assert {cell["seed"] for cell in cells} == {0, 1, 2}
    request = slurm_request()
    assert request["partition"] == "all"
    assert request["licenses"] is None
    assert request["mem"] == "8G"
    assert request["time"] == "00:30:00"
    assert main() == 2


def test_baselines_separate_all_subsets_from_feasible_subsets() -> None:
    f2 = uniform_task_baseline(load_scenario(_ROOT / "configs" / "f2_six_tasks.yaml"))
    f3 = uniform_task_baseline(load_scenario(_ROOT / "configs" / "f3_six_tasks.yaml"))
    assert f2.probability == Fraction(f2.optimal_task_subsets, f2.task_subsets)
    assert f2.feasible_task_subsets == 16
    assert f2.feasible_probability.denominator == 16
    assert f3.feasible_task_subsets == 13
    assert f3.feasible_probability.denominator == 13
    assert "qiskit" not in sys.modules


def test_one_hit_in_200_shots_has_the_binomial_error() -> None:
    error = binomial_standard_error(1, 200)
    assert error == pytest.approx((0.005 * 0.995 / 200) ** 0.5)
    with pytest.raises(PilotError):
        binomial_standard_error(1, 0)


def test_a_failed_cell_is_kept_and_the_next_cell_still_runs(tmp_path: Path) -> None:
    cells = (
        {"cell_id": "f2-six-tasks-v1-seed0"},
        {"cell_id": "f3-six-tasks-v1-seed0"},
    )

    def run(cell: dict[str, object], cell_dir: Path) -> dict[str, object]:
        if cell["cell_id"] == "f3-six-tasks-v1-seed0":
            raise RuntimeError("kept")
        return {
            "arms": {"noisy": {"optimum_hit_frequency": 0.005}},
            "compilation": {"rxx_count": 17},
            "ideal_optimum_probability": 0.0026,
        }

    summary = execute_cells(tmp_path, cells, run)
    assert summary["failed"] == 1
    failure = json.loads((tmp_path / "f3-six-tasks-v1-seed0" / "failure.json").read_text())
    assert failure["type"] == "RuntimeError"
    assert (tmp_path / "grid_summary.json").is_file()
