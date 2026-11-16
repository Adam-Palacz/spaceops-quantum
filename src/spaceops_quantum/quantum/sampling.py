"""Shot records for one sampled p=1 distribution.

Counts are the source of truth. A probability is ``count / shots``. Task
feasibility comes from the original budgets. When no shot is feasible,
``best_feasible_priority`` stays empty and the infeasible priorities remain
on the samples. ``sampled_optimum_probability`` is the shot frequency of
every feasible subset whose priority equals the exact optimum. The
lexicographic subset returned by ``solve_exact`` is not the only success.
It is not the ideal-statevector probability.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from spaceops_quantum.classical import solve_exact
from spaceops_quantum.domain.models import Scenario
from spaceops_quantum.encoding.penalty_audit import SampleAssessment, assess_sample
from spaceops_quantum.encoding.qubo import QuboModel
from spaceops_quantum.quantum.protocol import BackendSample

_PROBABILITY_TOLERANCE = 1e-9


class SampledRecordError(ValueError):
    """A shot record does not match its counts or the scenario."""


@dataclass(frozen=True, slots=True)
class SampledShot:
    """One observed logical bitstring and its independent assessment."""

    bits: tuple[int, ...]
    count: int
    probability: float
    assessment: SampleAssessment


@dataclass(frozen=True, slots=True)
class SampledRunRecord:
    """Decoded shots from one seeded, finite-shot run."""

    scenario_id: str
    scenario_hash: str
    p: int
    seed: int
    shots: int
    backend: str
    parameters: tuple[float, ...]
    samples: tuple[SampledShot, ...]
    best_feasible_priority: int | None
    best_feasible_task_ids: tuple[str, ...] | None
    feasibility_rate: float
    sampled_optimum_probability: float
    approx_ratio: float | None
    relative_gap: float | None
    versions: tuple[tuple[str, str], ...]


def build_sampled_record(
    scenario: Scenario,
    qubo: QuboModel,
    samples: Sequence[BackendSample],
    *,
    p: int,
    seed: int,
    shots: int,
    backend: str,
    parameters: Sequence[float],
    versions: Sequence[tuple[str, str]],
) -> SampledRunRecord:
    """Decode every shot and leave an empty best when none are feasible."""

    if p != 1:
        raise SampledRecordError(f"sampled record in this task accepts p=1, got {p}")
    _require_seed(seed)
    shot_count = _require_shots(shots)
    checked_parameters = _require_parameters(parameters)
    if not isinstance(backend, str) or backend == "":
        raise SampledRecordError("backend name must be a non-empty string")
    decoded = _decode_samples(scenario, qubo, samples, shot_count)
    feasible = tuple(item for item in decoded if item.assessment.task_feasible)
    feasible_count = sum(item.count for item in feasible)
    best_priority = None if not feasible else max(item.assessment.priority for item in feasible)
    best_ids = _best_ids(feasible, best_priority)
    exact = solve_exact(scenario).solution
    optimum_count = sum(
        item.count
        for item in decoded
        if is_original_optimum(item.assessment, exact.priority)
    )
    approx_ratio, relative_gap = _ratios(best_priority, exact.priority)
    return SampledRunRecord(
        scenario_id=scenario.scenario_id,
        scenario_hash=qubo.scenario_hash,
        p=1,
        seed=seed,
        shots=shot_count,
        backend=backend,
        parameters=checked_parameters,
        samples=decoded,
        best_feasible_priority=best_priority,
        best_feasible_task_ids=best_ids,
        feasibility_rate=feasible_count / shot_count,
        sampled_optimum_probability=optimum_count / shot_count,
        approx_ratio=approx_ratio,
        relative_gap=relative_gap,
        versions=tuple(versions),
    )


def _decode_samples(
    scenario: Scenario,
    qubo: QuboModel,
    samples: Sequence[BackendSample],
    shots: int,
) -> tuple[SampledShot, ...]:
    if isinstance(samples, (str, bytes, bytearray)):
        raise SampledRecordError("samples must be a sequence of backend samples")
    found: list[SampledShot] = []
    seen: set[tuple[int, ...]] = set()
    total = 0
    for sample in samples:
        count = _require_count(sample.count)
        if sample.probability is None:
            raise SampledRecordError("shot sample is missing a probability")
        expected = count / shots
        if abs(sample.probability - expected) > _PROBABILITY_TOLERANCE:
            raise SampledRecordError(
                f"probability {sample.probability} does not match {count}/{shots}"
            )
        if sample.bits in seen:
            raise SampledRecordError(f"duplicate bitstring {sample.bits}")
        seen.add(sample.bits)
        assessment = assess_sample(qubo, scenario, sample.bits)
        found.append(
            SampledShot(
                bits=sample.bits,
                count=count,
                probability=expected,
                assessment=assessment,
            )
        )
        total += count
    if total != shots:
        raise SampledRecordError(f"counts sum to {total}, expected {shots} shots")
    return tuple(sorted(found, key=lambda item: item.bits))


def is_original_optimum(assessment: SampleAssessment, optimum_priority: int) -> bool:
    """True for every feasible subset that reaches the exact objective."""

    return assessment.task_feasible and assessment.priority == optimum_priority


def _best_ids(
    feasible: Sequence[SampledShot],
    best_priority: int | None,
) -> tuple[str, ...] | None:
    if best_priority is None:
        return None
    winners = {
        item.assessment.selected_task_ids
        for item in feasible
        if item.assessment.priority == best_priority
    }
    return min(winners)


def _ratios(best_priority: int | None, optimum: int) -> tuple[float | None, float | None]:
    if best_priority is None or optimum <= 0:
        return None, None
    return best_priority / optimum, (optimum - best_priority) / optimum


def _require_count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SampledRecordError(f"shot count must be an integer >= 1, got {value!r}")
    return value


def _require_shots(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SampledRecordError(f"shots must be an integer >= 1, got {value!r}")
    return value


def _require_seed(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SampledRecordError(f"seed must be an integer >= 0, got {value!r}")


def _require_parameters(values: Sequence[float]) -> tuple[float, float]:
    if isinstance(values, (str, bytes, bytearray)):
        raise SampledRecordError("parameters must be two finite numbers (gamma, beta)")
    try:
        raw = list(values)
    except TypeError as exc:
        raise SampledRecordError("parameters must be two finite numbers (gamma, beta)") from exc
    if len(raw) != 2:
        raise SampledRecordError(f"p=1 sampling expects 2 parameters, got {len(raw)}")
    checked: list[float] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SampledRecordError(f"parameter must be a finite number, got {value!r}")
        number = float(value)
        if not math.isfinite(number):
            raise SampledRecordError(f"parameter must be a finite number, got {value!r}")
        checked.append(number)
    return (checked[0], checked[1])
