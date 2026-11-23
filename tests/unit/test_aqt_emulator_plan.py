"""The T19 matrix is data. Building it does not import Qiskit."""

from __future__ import annotations

import sys

from spaceops_quantum.experiment.aqt_emulator_plan import (
    main,
    maximum_shots,
    noisy_shots,
    pilot_job,
    planned_jobs,
)


def test_plan_optimizes_without_shots_and_reuses_parameters() -> None:
    jobs = planned_jobs()
    ideal = [job for job in jobs if job["stage"] == "ideal-optimize"]
    sampled = [job for job in jobs if job["stage"] == "ideal-fixed"]
    noisy = [job for job in jobs if job["stage"] == "noisy-fixed"]
    assert len(ideal) == 6
    assert len(sampled) == 6
    assert len(noisy) == 6
    assert {job["scenario_id"] for job in ideal} == {"f2-six-tasks-v1", "f3-six-tasks-v1"}
    assert all(job["shots"] is None for job in ideal)
    assert all(job["objective"] == "exact-statevector-expectation" for job in ideal)
    assert all(job["shots"] == 200 and job["circuits"] == 1 for job in noisy)
    assert all(job["shots"] == 200 and job["circuits"] == 1 for job in sampled)
    assert all(job["parameter_source"] == "fixed-from-ideal-trace" for job in noisy)
    assert all(job["parameter_source"] == "fixed-from-ideal-trace" for job in sampled)
    assert noisy_shots() == 6 * 200
    assert maximum_shots() == 12 * 200
    pilot = pilot_job()
    assert pilot["scenario_id"] == "f2-six-tasks-v1"
    assert pilot["seed"] == 0
    assert pilot["statevector_shots"] is None
    assert pilot["noisy_shots"] == 200
    assert "qiskit" not in sys.modules


def test_unapproved_plan_does_not_start() -> None:
    assert main() == 2
