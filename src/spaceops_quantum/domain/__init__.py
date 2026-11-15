"""Domain models and scenario loading.

Importing this package must not import Qiskit.
"""

from spaceops_quantum.domain.evaluation import SolutionEvaluationError, evaluate_solution
from spaceops_quantum.domain.models import (
    Resources,
    ResourceViolations,
    Scenario,
    ScenarioReference,
    SolutionEvaluation,
    Task,
)
from spaceops_quantum.domain.validation import (
    ScenarioValidationError,
    load_scenario,
    parse_scenario,
)

__all__ = [
    "ResourceViolations",
    "Resources",
    "Scenario",
    "ScenarioReference",
    "ScenarioValidationError",
    "SolutionEvaluation",
    "SolutionEvaluationError",
    "Task",
    "evaluate_solution",
    "load_scenario",
    "parse_scenario",
]
