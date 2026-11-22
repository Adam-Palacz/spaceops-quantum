"""T19 emulator matrix. Building the plan does not run QAOA or submit a job.

The ideal objective is the exact statevector expectation. AQT ``offline.ideal()``
with a shot count is a separate estimator. Noisy shots reuse the archived
parameters and do not start another optimizer.
"""

from __future__ import annotations

import os

_EVIDENCE_SCENARIOS = ("f2-six-tasks-v1", "f3-six-tasks-v1")
_SEEDS = (0, 1, 2)
_MAX_EVALUATIONS = 25
_SHOTS = 200


def planned_jobs() -> tuple[dict[str, object], ...]:
    """Return the evidence matrix. F1 is not an evidence scenario."""

    jobs: list[dict[str, object]] = []
    for scenario_id in _EVIDENCE_SCENARIOS:
        for seed in _SEEDS:
            jobs.append(
                {
                    "backend": "aer-statevector",
                    "circuits": 0,
                    "evaluations": _MAX_EVALUATIONS,
                    "objective": "exact-statevector-expectation",
                    "penalty": 41,
                    "scenario_id": scenario_id,
                    "seed": seed,
                    "shots": None,
                    "stage": "ideal-optimize",
                }
            )
            jobs.append(
                {
                    "backend": "offline.noisy",
                    "circuits": 1,
                    "evaluations": 0,
                    "objective": "shot-frequency",
                    "parameter_source": "fixed-from-ideal-trace",
                    "penalty": 41,
                    "scenario_id": scenario_id,
                    "seed": seed,
                    "shots": _SHOTS,
                    "stage": "noisy-fixed",
                }
            )
    return tuple(jobs)


def maximum_shots() -> int:
    """Shots on the noisy readout. The statevector search contributes none."""

    return sum(int(job["circuits"]) * int(job["shots"] or 0) for job in planned_jobs())


def pilot_job() -> dict[str, object]:
    """One F2 seed, exact search, then one noisy readout at the same parameters."""

    return {
        "evaluations": _MAX_EVALUATIONS,
        "noisy_shots": _SHOTS,
        "penalty": 41,
        "scenario_id": "f2-six-tasks-v1",
        "seed": 0,
        "statevector_shots": None,
    }


def main() -> int:
    """Print the matrix. The benchmark stays disabled without approval."""

    if os.environ.get("SPACEOPS_T19_APPROVED") != "1":
        print("T19 benchmark is not approved")
        print(f"jobs {len(planned_jobs())}")
        print(f"maximum_shots {maximum_shots()}")
        return 2
    print("approval flag is set; the benchmark runner is not implemented in this review")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
