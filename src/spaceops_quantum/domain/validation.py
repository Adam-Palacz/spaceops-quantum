"""Strict YAML loading for task-selection scenarios."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from spaceops_quantum.domain.models import Resources, Scenario, ScenarioReference, Task

SUPPORTED_SCHEMA_VERSIONS = frozenset({1})
_RESOURCE_FIELDS = ("energy", "storage", "downlink")
_SCENARIO_FIELDS = frozenset(
    {"schema_version", "scenario_id", "description", "budgets", "tasks", "reference"}
)
_TASK_FIELDS = frozenset({"id", "priority", "energy", "storage", "downlink"})
_REFERENCE_FIELDS = frozenset(
    {
        "source",
        "selected_task_ids",
        "optimal_priority",
        "used",
        "feasible_subsets",
        "total_subsets",
    }
)


class ScenarioValidationError(ValueError):
    """Actionable schema or value error for a scenario document."""

    def __init__(self, message: str, *, path: str) -> None:
        self.path = path
        super().__init__(f"{path}: {message}")


def load_scenario(path: str | Path) -> Scenario:
    """Load and validate a UTF-8 YAML scenario.

    Raises:
        FileNotFoundError: the path does not exist.
        ScenarioValidationError: the document is not valid UTF-8, YAML, or schema.
    """
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ScenarioValidationError(
            f"file is not valid UTF-8 ({exc.reason})",
            path=str(source),
        ) from exc
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ScenarioValidationError(f"invalid YAML: {exc}", path=str(source)) from exc
    return parse_scenario(document, path=str(source))


def parse_scenario(document: object, *, path: str = "<scenario>") -> Scenario:
    """Validate an already-parsed YAML document."""
    data = _require_mapping(document, path)
    _require_fields(
        data,
        required=("schema_version", "scenario_id", "description", "budgets", "tasks"),
        allowed=_SCENARIO_FIELDS,
        path=path,
    )
    schema_version = _require_int(data["schema_version"], f"{path}.schema_version", minimum=1)
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        supported = ", ".join(str(item) for item in sorted(SUPPORTED_SCHEMA_VERSIONS))
        raise ScenarioValidationError(
            f"unsupported schema_version {schema_version}; supported versions: {supported}",
            path=f"{path}.schema_version",
        )
    scenario_id = _require_text(data["scenario_id"], f"{path}.scenario_id")
    description = _require_text(data["description"], f"{path}.description")
    budgets = _parse_resources(data["budgets"], f"{path}.budgets")
    tasks = _parse_tasks(data["tasks"], f"{path}.tasks")
    reference = None
    if "reference" in data:
        reference = _parse_reference(
            data["reference"],
            f"{path}.reference",
            task_ids=tuple(task.id for task in tasks),
        )
    return Scenario(
        schema_version=schema_version,
        scenario_id=scenario_id,
        description=description,
        budgets=budgets,
        tasks=tasks,
        reference=reference,
    )


def _parse_resources(value: object, path: str) -> Resources:
    data = _require_mapping(value, path)
    _require_fields(data, required=_RESOURCE_FIELDS, allowed=frozenset(_RESOURCE_FIELDS), path=path)
    return Resources(
        energy=_require_int(data["energy"], f"{path}.energy", minimum=0),
        storage=_require_int(data["storage"], f"{path}.storage", minimum=0),
        downlink=_require_int(data["downlink"], f"{path}.downlink", minimum=0),
    )


def _parse_tasks(value: object, path: str) -> tuple[Task, ...]:
    items = _require_list(value, path)
    if not items:
        raise ScenarioValidationError("expected a non-empty list", path=path)
    tasks: list[Task] = []
    seen: dict[str, int] = {}
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        data = _require_mapping(item, item_path)
        _require_fields(
            data,
            required=("id", "priority", "energy", "storage", "downlink"),
            allowed=_TASK_FIELDS,
            path=item_path,
        )
        task_id = _require_text(data["id"], f"{item_path}.id")
        if task_id in seen:
            raise ScenarioValidationError(
                f"duplicate task id {task_id!r} (also at {path}[{seen[task_id]}])",
                path=f"{item_path}.id",
            )
        seen[task_id] = index
        tasks.append(
            Task(
                id=task_id,
                priority=_require_int(data["priority"], f"{item_path}.priority", minimum=1),
                energy=_require_int(data["energy"], f"{item_path}.energy", minimum=0),
                storage=_require_int(data["storage"], f"{item_path}.storage", minimum=0),
                downlink=_require_int(data["downlink"], f"{item_path}.downlink", minimum=0),
            )
        )
    return tuple(tasks)


def _parse_reference(value: object, path: str, *, task_ids: tuple[str, ...]) -> ScenarioReference:
    data = _require_mapping(value, path)
    _require_fields(
        data,
        required=(
            "source",
            "selected_task_ids",
            "optimal_priority",
            "used",
            "feasible_subsets",
            "total_subsets",
        ),
        allowed=_REFERENCE_FIELDS,
        path=path,
    )
    selected = _parse_selected_ids(data["selected_task_ids"], f"{path}.selected_task_ids", task_ids)
    feasible = _require_int(data["feasible_subsets"], f"{path}.feasible_subsets", minimum=0)
    total = _require_int(data["total_subsets"], f"{path}.total_subsets", minimum=0)
    if feasible > total:
        raise ScenarioValidationError(
            f"feasible_subsets ({feasible}) exceeds total_subsets ({total})",
            path=f"{path}.feasible_subsets",
        )
    return ScenarioReference(
        source=_require_text(data["source"], f"{path}.source"),
        selected_task_ids=selected,
        optimal_priority=_require_int(
            data["optimal_priority"],
            f"{path}.optimal_priority",
            minimum=0,
        ),
        used=_parse_resources(data["used"], f"{path}.used"),
        feasible_subsets=feasible,
        total_subsets=total,
    )


def _parse_selected_ids(value: object, path: str, task_ids: tuple[str, ...]) -> tuple[str, ...]:
    items = _require_list(value, path)
    known = set(task_ids)
    selected: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(items):
        item_path = f"{path}[{index}]"
        task_id = _require_text(item, item_path)
        if task_id not in known:
            raise ScenarioValidationError(f"unknown task id {task_id!r}", path=item_path)
        if task_id in seen:
            raise ScenarioValidationError(f"duplicate task id {task_id!r}", path=item_path)
        seen.add(task_id)
        selected.append(task_id)
    return tuple(selected)


def _require_mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ScenarioValidationError(
            f"expected a mapping, got {_type_name(value)}",
            path=path,
        )
    return value


def _require_list(value: object, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ScenarioValidationError(
            f"expected a list, got {_type_name(value)}",
            path=path,
        )
    return value


def _require_fields(
    data: dict[str, Any],
    *,
    required: tuple[str, ...],
    allowed: frozenset[str],
    path: str,
) -> None:
    missing = [key for key in required if key not in data]
    if missing:
        raise ScenarioValidationError(
            f"missing required fields: {', '.join(missing)}",
            path=path,
        )
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ScenarioValidationError(
            f"unknown fields: {', '.join(unknown)}",
            path=path,
        )


def _require_int(value: object, path: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ScenarioValidationError(
            f"expected an integer >= {minimum}, got {_type_name(value)}",
            path=path,
        )
    if value < minimum:
        raise ScenarioValidationError(
            f"expected an integer >= {minimum}, got {value}",
            path=path,
        )
    return value


def _require_text(value: object, path: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise ScenarioValidationError("expected a non-empty string", path=path)
    if value != value.strip():
        raise ScenarioValidationError("must not have surrounding whitespace", path=path)
    return value


def _type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    return type(value).__name__
