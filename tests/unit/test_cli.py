"""CLI coverage for validate, exact and greedy."""

from __future__ import annotations

from pathlib import Path

import pytest

from spaceops_quantum.cli import main
from spaceops_quantum.domain import load_scenario
from spaceops_quantum.encoding import build_qubo, to_ising

FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"


def test_validate_prints_the_fixture(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate", str(FIXTURE)]) == 0
    text = capsys.readouterr().out
    assert "scenario_id: eo-six-tasks-v1" in text
    assert "tasks: 6" in text
    assert "energy_budget: 10" in text
    assert "valid: true" in text


def test_validate_reports_a_schema_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "scenario_id: bad",
                "description: duplicate ids",
                "budgets: {energy: 1, storage: 1, downlink: 1}",
                "tasks:",
                "  - {id: A, priority: 1, energy: 0, storage: 0, downlink: 0}",
                "  - {id: A, priority: 1, energy: 0, storage: 0, downlink: 0}",
            ]
        ),
        encoding="utf-8",
    )

    assert main(["validate", str(path)]) == 1
    assert "duplicate task id 'A'" in capsys.readouterr().err


def test_validate_missing_file_exits_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "absent.yaml"

    assert main(["validate", str(missing)]) == 1
    assert "absent.yaml" in capsys.readouterr().err


def test_exact_solve_prints_the_oracle(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["solve", "--method", "exact", "--scenario", str(FIXTURE)]) == 0
    text = capsys.readouterr().out
    assert "method: exact" in text
    assert "examined_subsets: 64" in text
    assert "feasible_subsets: 37" in text
    assert "total_subsets: 64" in text
    assert "selected_task_ids: T1,T2,T5,T6" in text
    assert "priority: 27" in text
    assert "energy: 9" in text
    assert "storage: 10" in text
    assert "downlink: 10" in text
    assert "feasible: true" in text
    assert "strategy:" not in text


def test_greedy_solve_prints_a_feasible_subset(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        ["solve", "--method", "greedy", "--scenario", str(FIXTURE), "--seed", "3"]
    )
    text = capsys.readouterr().out

    assert code == 0
    assert "method: greedy" in text
    assert "strategy: resource_density" in text
    assert "seed: 3" in text
    assert "examined_subsets: 6" in text
    assert "feasible_subsets: null" in text
    assert "total_subsets: null" in text
    assert "selected_task_ids: T1,T2,T5,T6" in text
    assert "priority: 27" in text
    assert "feasible: true" in text


def test_exact_rejects_a_greedy_seed(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        ["solve", "--method", "exact", "--scenario", str(FIXTURE), "--seed", "3"]
    )

    assert code == 2
    assert "exact does not use --strategy or --seed" in capsys.readouterr().err


def test_unknown_method_is_rejected() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["solve", "--method", "qaoa", "--scenario", str(FIXTURE)])
    assert exc_info.value.code == 2


def test_qubo_inspect_prints_the_18_qubit_summary(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["qubo", "inspect", "--scenario", str(FIXTURE), "--penalty", "41"])
    text = capsys.readouterr().out
    scenario = load_scenario(FIXTURE)
    ising = to_ising(build_qubo(scenario, {"energy": 41, "storage": 41, "downlink": 41}))
    if ising.constant.denominator == 1:
        rendered_constant = str(ising.constant.numerator)
    else:
        rendered_constant = f"{ising.constant.numerator}/{ising.constant.denominator}"

    assert code == 0
    assert "n_task_bits: 6" in text
    assert "n_slack_bits: 12" in text
    assert "n_logical_qubits: 18" in text
    assert "qubo_constant: 12300" in text
    assert "penalty_energy: 41" in text
    assert "penalty_storage: 41" in text
    assert "penalty_downlink: 41" in text
    assert f"ising_constant: {rendered_constant}" in text
    assert "spin_map: s = 2v - 1" in text
    assert text.split("variable_names: ", 1)[1].startswith("x_T1,x_T2,x_T3,x_T4,x_T5,x_T6,e_s0,")


def test_negative_penalty_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["qubo", "inspect", "--scenario", str(FIXTURE), "--penalty", "-1"])

    assert code == 2
    assert "penalty must be an integer >= 0" in capsys.readouterr().err


def test_help_lists_validate_and_solve(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    text = capsys.readouterr().out
    assert "validate" in text
    assert "solve" in text
    assert "qubo" in text
