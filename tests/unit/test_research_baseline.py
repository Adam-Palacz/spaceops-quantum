"""Uniform task baseline and QUBO ground-state probability."""

from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

from spaceops_quantum.domain import Resources, Scenario, Task, load_scenario, parse_scenario
from spaceops_quantum.encoding import assess_sample, build_qubo, find_qubo_minima
from spaceops_quantum.experiment.aggregate import build_aggregate
from spaceops_quantum.experiment.baseline import (
    probability_on_bitstrings,
    uniform_task_baseline,
)
from spaceops_quantum.experiment.charts import write_charts
from spaceops_quantum.quantum import is_original_optimum

_ROOT = Path(__file__).resolve().parents[2]
_PENALTIES = {"downlink": 6, "energy": 6, "storage": 6}


def test_f1_f2_and_f3_uniform_baselines_match_the_task_draw() -> None:
    expected = {
        "configs/f1_three_tasks.yaml": (2, 8),
        "configs/f2_six_tasks.yaml": (1, 64),
        "configs/f3_six_tasks.yaml": (1, 64),
    }
    for relative, (winners, total) in expected.items():
        baseline = uniform_task_baseline(load_scenario(_ROOT / relative))
        assert baseline.optimal_task_subsets == winners
        assert baseline.task_subsets == total
        assert baseline.probability == Fraction(winners, total)
    assert "qiskit" not in sys.modules


def test_wrong_slack_counts_for_the_task_optimum_only() -> None:
    scenario = Scenario(
        schema_version=1,
        scenario_id="two-optima",
        description="two feasible optima",
        budgets=Resources(1, 0, 0),
        tasks=(
            Task("A", priority=4, energy=1, storage=0, downlink=0),
            Task("B", priority=4, energy=1, storage=0, downlink=0),
            Task("C", priority=4, energy=2, storage=0, downlink=0),
        ),
    )
    model = build_qubo(scenario, _PENALTIES)
    minima = find_qubo_minima(model, scenario)
    correct_b = (0, 1, 0, 0)
    wrong_a = (1, 0, 0, 1)
    assert correct_b in minima.bitstrings
    assert wrong_a not in minima.bitstrings
    wrong = assess_sample(model, scenario, wrong_a)
    correct = assess_sample(model, scenario, correct_b)
    assert is_original_optimum(wrong, 4)
    assert is_original_optimum(correct, 4)
    assert wrong.equality_satisfied is False
    mass = probability_on_bitstrings(((wrong_a, 0.5), (correct_b, 0.5)), set(minima.bitstrings))
    assert mass == 0.5
    assert "qiskit" not in sys.modules


def test_archived_cell_separates_ground_state_from_task_optimum(tmp_path: Path) -> None:
    scenario = Scenario(
        schema_version=1,
        scenario_id="two-optima",
        description="two feasible optima",
        budgets=Resources(1, 0, 0),
        tasks=(
            Task("A", priority=4, energy=1, storage=0, downlink=0),
            Task("B", priority=4, energy=1, storage=0, downlink=0),
            Task("C", priority=4, energy=2, storage=0, downlink=0),
        ),
    )
    cell = tmp_path / "tie-penalty-l6-seed0"
    cell.mkdir()
    (cell / "scenario.json").write_text(
        json.dumps(
            {
                "budgets": {"downlink": 0, "energy": 1, "storage": 0},
                "description": scenario.description,
                "scenario_id": scenario.scenario_id,
                "schema_version": 1,
                "tasks": [
                    {"downlink": 0, "energy": 1, "id": "A", "priority": 4, "storage": 0},
                    {"downlink": 0, "energy": 1, "id": "B", "priority": 4, "storage": 0},
                    {"downlink": 0, "energy": 2, "id": "C", "priority": 4, "storage": 0},
                ],
            }
        ),
        encoding="utf-8",
    )
    (cell / "manifest.json").write_text(
        json.dumps({"penalties": {"downlink": 6, "energy": 6, "storage": 6}}),
        encoding="utf-8",
    )
    (cell / "metrics.json").write_text(
        json.dumps(
            {
                "best_feasible_basis": "statevector-support",
                "experiment_id": "tie-penalty-l6-seed0",
                "feasibility_rate": 1,
                "p_optimum": 1,
                "performance_metric": "statevector-probability",
                "seed": 0,
                "shots": None,
            }
        ),
        encoding="utf-8",
    )
    samples = [
        {"bits": [1, 0, 0, 1], "probability": 0.5},
        {"bits": [0, 1, 0, 0], "probability": 0.5},
    ]
    (cell / "samples.jsonl").write_text(
        "\n".join(json.dumps(sample) for sample in samples) + "\n",
        encoding="utf-8",
    )
    aggregate = build_aggregate(tmp_path)
    restored = parse_scenario(
        json.loads((cell / "scenario.json").read_text(encoding="utf-8"))
    )
    assert restored.scenario_id == "two-optima"
    cell_row = aggregate["cells"][0]
    assert cell_row["p_uniform_exact"] == "1/4"
    assert cell_row["p_optimum"] == 1
    assert cell_row["p_ground_state"] == 0.5
    assert cell_row["p_optimum_over_uniform"] == 4
    assert "qiskit" not in sys.modules


def test_published_aggregate_keeps_the_uniform_baseline() -> None:
    path = _ROOT / "docs" / "aggregates" / "t15-v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    uniform = payload["uniform_task_baseline"]
    assert uniform["f1-three-tasks-v1"]["optimal_task_subsets"] == 2
    assert uniform["f1-three-tasks-v1"]["p_uniform_exact"] == "1/4"
    assert uniform["f2-six-tasks-v1"]["p_uniform_exact"] == "1/64"
    assert uniform["f3-six-tasks-v1"]["p_uniform_exact"] == "1/64"
    assert payload["provenance"]["git_shas"] == ["0cb532899223c67798fded033fe797a2b78b8f65"]
    assert payload["provenance"]["cell_count"] == 66
    row = next(
        item
        for item in payload["summary"]["ideal_penalty"]
        if item["scenario_id"] == "f1-three-tasks-v1" and item["key"] == 41
    )
    assert row["p_optimum_over_uniform_median"] < 1
    assert row["p_ground_state_median"] < row["p_optimum_median"]
    assert "qiskit" not in sys.modules


def test_charts_render_the_three_scenarios(tmp_path: Path) -> None:
    groups = []
    for scenario in ("f1-three-tasks-v1", "f2-six-tasks-v1", "f3-six-tasks-v1"):
        for penalty in (5, 10, 20, 41):
            groups.append(
                {
                    "key": penalty,
                    "p_ground_state_median": 0.01,
                    "p_optimum_median": 0.02,
                    "p_optimum_over_uniform_median": 1.5,
                    "scenario_id": scenario,
                }
            )
    write_charts({"summary": {"ideal_penalty": groups}}, tmp_path)
    ratio = (tmp_path / "t15-ratio.svg").read_text(encoding="utf-8")
    ground = (tmp_path / "t15-ground-vs-optimum.svg").read_text(encoding="utf-8")
    assert "p_optimum / p_uniform" in ratio
    assert "p_ground_state" in ground
    assert "qiskit" not in sys.modules
