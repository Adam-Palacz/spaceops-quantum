"""Archive one optimized ideal QAOA run.

Importing this module imports Qiskit. The package export does not load it.
The measured interval is the optimizer call. Transpile time is not split out,
so ``optimizer_time_sec`` equals ``wall_time_sec``.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence

from spaceops_quantum.domain.models import Scenario
from spaceops_quantum.experiment.archive import (
    ExperimentCapture,
    _from_assessment,
    capture_optimized,
)
from spaceops_quantum.quantum.aer import AerIdealBackend
from spaceops_quantum.quantum.qaoa import OptimizerConfig, run_qaoa


def capture_optimized_run(
    experiment_id: str,
    scenario_path: str,
    scenario: Scenario,
    *,
    seed: int,
    max_evaluations: int,
    penalties: Mapping[str, int],
    initial_parameters: Sequence[float] | None,
) -> ExperimentCapture:
    """Run bounded ideal QAOA and return a capture with its evaluation trace."""

    started = time.perf_counter()
    result = run_qaoa(
        scenario,
        AerIdealBackend(),
        p=1,
        shots=None,
        seed=seed,
        optimizer=OptimizerConfig(
            max_evaluations=max_evaluations,
            initial_parameters=(
                None if initial_parameters is None else tuple(initial_parameters)
            ),
        ),
        lambda_by_constraint=penalties,
    )
    elapsed = time.perf_counter() - started
    samples = tuple(
        _from_assessment(
            candidate.assessment,
            bits=candidate.bits,
            count=None,
            probability=candidate.probability,
        )
        for candidate in result.candidates
    )
    trace = tuple((step.index, step.parameters, step.energy) for step in result.evaluations)
    return capture_optimized(
        experiment_id,
        scenario_path,
        scenario,
        samples,
        backend=result.backend,
        seed=seed,
        p=result.p,
        parameters=result.parameters,
        penalties=penalties,
        max_evaluations=max_evaluations,
        trace=trace,
        feasibility_rate=result.feasibility_rate,
        p_optimum=result.ideal_optimum_probability,
        wall_time_sec=elapsed,
    )
