"""Schema tests for the T02 scenario loader."""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from spaceops_quantum.domain import ScenarioValidationError, load_scenario

FIXTURE = Path(__file__).resolve().parents[2] / "configs" / "six_tasks.yaml"


def _valid_document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "scenario_id": "mini",
        "description": "minimal valid scenario",
        "budgets": {"energy": 1, "storage": 0, "downlink": 2},
        "tasks": [
            {"id": "A", "priority": 3, "energy": 0, "storage": 0, "downlink": 1},
        ],
    }


def _dump(tmp_path: Path, document: dict[str, object]) -> Path:
    path = tmp_path / "scenario.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def _load_error(path: Path) -> str:
    with pytest.raises(ScenarioValidationError) as exc_info:
        load_scenario(path)
    return str(exc_info.value)


def test_frozen_fixture_loads_without_qiskit() -> None:
    scenario = load_scenario(FIXTURE)

    assert scenario.schema_version == 1
    assert scenario.scenario_id == "eo-six-tasks-v1"
    assert "normalized unitless" in scenario.description
    assert (scenario.budgets.energy, scenario.budgets.storage, scenario.budgets.downlink) == (
        10,
        10,
        10,
    )
    assert [task.id for task in scenario.tasks] == ["T1", "T2", "T3", "T4", "T5", "T6"]
    loaded_rows = [
        (task.priority, task.energy, task.storage, task.downlink) for task in scenario.tasks
    ]
    assert loaded_rows == [
        (10, 4, 3, 5),
        (8, 2, 4, 2),
        (7, 5, 2, 3),
        (6, 3, 5, 4),
        (5, 1, 2, 2),
        (4, 2, 1, 1),
    ]
    assert scenario.reference is not None
    assert scenario.reference.selected_task_ids == ("T1", "T2", "T5", "T6")
    assert scenario.reference.optimal_priority == 27
    used = scenario.reference.used
    assert (used.energy, used.storage, used.downlink) == (9, 10, 10)
    assert scenario.reference.feasible_subsets == 37
    assert scenario.reference.total_subsets == 64
    assert "qiskit" not in sys.modules
    assert "qiskit_aer" not in sys.modules


def test_minimal_scenario_allows_zero_costs_and_omits_reference(tmp_path: Path) -> None:
    scenario = load_scenario(_dump(tmp_path, _valid_document()))

    assert scenario.reference is None
    assert scenario.tasks[0].energy == 0
    assert scenario.budgets.storage == 0


def test_models_are_immutable() -> None:
    scenario = load_scenario(FIXTURE)

    with pytest.raises(FrozenInstanceError):
        scenario.scenario_id = "other"  # type: ignore[misc]


def test_negative_cost_names_the_field(tmp_path: Path) -> None:
    document = _valid_document()
    tasks = document["tasks"]
    assert isinstance(tasks, list)
    tasks[0]["energy"] = -1

    message = _load_error(_dump(tmp_path, document))

    assert "tasks[0].energy" in message
    assert "expected an integer >= 0, got -1" in message


def test_negative_budget_names_the_field(tmp_path: Path) -> None:
    document = _valid_document()
    budgets = document["budgets"]
    assert isinstance(budgets, dict)
    budgets["downlink"] = -2

    message = _load_error(_dump(tmp_path, document))

    assert "budgets.downlink" in message
    assert "got -2" in message


def test_nonintegral_priority_is_rejected(tmp_path: Path) -> None:
    document = _valid_document()
    tasks = document["tasks"]
    assert isinstance(tasks, list)
    tasks[0]["priority"] = 1.5

    message = _load_error(_dump(tmp_path, document))

    assert "tasks[0].priority" in message
    assert "got float" in message


def test_zero_priority_is_rejected(tmp_path: Path) -> None:
    document = _valid_document()
    tasks = document["tasks"]
    assert isinstance(tasks, list)
    tasks[0]["priority"] = 0

    message = _load_error(_dump(tmp_path, document))

    assert "tasks[0].priority" in message
    assert "got 0" in message


def test_yaml_boolean_is_not_an_integer(tmp_path: Path) -> None:
    path = tmp_path / "bool.yaml"
    path.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "scenario_id: mini",
                "description: boolean trap",
                "budgets: {energy: 1, storage: 1, downlink: 1}",
                "tasks:",
                "  - {id: T1, priority: yes, energy: 0, storage: 0, downlink: 0}",
            ]
        ),
        encoding="utf-8",
    )

    message = _load_error(path)

    assert "tasks[0].priority" in message
    assert "got bool" in message


def test_duplicate_task_ids_name_both_positions(tmp_path: Path) -> None:
    document = _valid_document()
    tasks = document["tasks"]
    assert isinstance(tasks, list)
    tasks.append({"id": "A", "priority": 2, "energy": 0, "storage": 0, "downlink": 0})

    message = _load_error(_dump(tmp_path, document))

    assert "tasks[1].id" in message
    assert "duplicate task id 'A'" in message
    assert "tasks[0]" in message


def test_missing_task_field_is_named(tmp_path: Path) -> None:
    document = _valid_document()
    tasks = document["tasks"]
    assert isinstance(tasks, list)
    del tasks[0]["storage"]

    message = _load_error(_dump(tmp_path, document))

    assert "tasks[0]" in message
    assert "missing required fields: storage" in message


def test_missing_top_level_field_is_named(tmp_path: Path) -> None:
    document = _valid_document()
    del document["budgets"]

    message = _load_error(_dump(tmp_path, document))

    assert "missing required fields: budgets" in message


def test_empty_task_list_is_rejected(tmp_path: Path) -> None:
    document = _valid_document()
    document["tasks"] = []

    message = _load_error(_dump(tmp_path, document))

    assert "tasks: expected a non-empty list" in message


def test_unsupported_schema_version_lists_supported_versions(tmp_path: Path) -> None:
    document = _valid_document()
    document["schema_version"] = 2

    message = _load_error(_dump(tmp_path, document))

    assert "schema_version" in message
    assert "unsupported schema_version 2" in message
    assert "supported versions: 1" in message


def test_string_schema_version_is_rejected(tmp_path: Path) -> None:
    document = _valid_document()
    document["schema_version"] = "1"

    message = _load_error(_dump(tmp_path, document))

    assert "schema_version" in message
    assert "got str" in message


def test_unknown_field_is_rejected(tmp_path: Path) -> None:
    document = _valid_document()
    tasks = document["tasks"]
    assert isinstance(tasks, list)
    tasks[0]["orbit"] = "leo"

    message = _load_error(_dump(tmp_path, document))

    assert "tasks[0]" in message
    assert "unknown fields: orbit" in message


def test_reference_unknown_task_is_rejected(tmp_path: Path) -> None:
    document = _valid_document()
    document["reference"] = {
        "source": "manual",
        "selected_task_ids": ["missing"],
        "optimal_priority": 0,
        "used": {"energy": 0, "storage": 0, "downlink": 0},
        "feasible_subsets": 1,
        "total_subsets": 2,
    }

    message = _load_error(_dump(tmp_path, document))

    assert "reference.selected_task_ids[0]" in message
    assert "unknown task id 'missing'" in message


def test_invalid_yaml_names_the_file(tmp_path: Path) -> None:
    path = tmp_path / "broken.yaml"
    path.write_text("tasks: [\n", encoding="utf-8")

    message = _load_error(path)

    assert str(path) in message
    assert "invalid YAML" in message


def test_invalid_utf8_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "binary.yaml"
    path.write_bytes(b"\xff\xfe not utf-8")

    message = _load_error(path)

    assert "not valid UTF-8" in message


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_scenario(tmp_path / "absent.yaml")
