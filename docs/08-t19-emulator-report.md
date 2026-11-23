# T19 emulator benchmark — draft for review

This draft is for review before anything is sent to PCSS. It does not request a physical QPU run. The completed measurement is one F2 pilot. The remaining five evidence cells are specified and have not been submitted.

## What was measured

Slurm job 2081 on partition `all` completed with exit code 0 in 4 seconds. The archive is `specs/001-task-selection/f2-pilot-seed0/pilot.json`. The backend was `offline_simulator_noise` from `qiskit-aqt-provider` 2.0.1, with `qiskit-aer` 0.18.2. No API token was set and no remote backend was called.

| Item | Value |
|---|---|
| Scenario | F2, 9 logical qubits, exact priority 18 |
| Depth and penalty | p=1, λ=41 on every resource |
| Seed | 0 |
| Exact search | 25 COBYLA evaluations, 1.08 s |
| Statevector optimum probability | 0.002687 |
| Noisy shots | 200, seed 0, 0.075 s |
| Noisy optimum hits | 1/200 = 0.005 |
| Binomial standard error | 0.0050 |
| Feasible-shot rate | 0.445 |
| Best observed feasible priority | 18, so the best-shot ratio is 1 |
| Greedy priority | 18 |
| Uniform task draw | 1/64 = 0.015625 |
| Feasible-uniform draw | 1/16 = 0.0625 |
| Compiled circuit | depth 29, 17 RXX, native gates only |
| Process wall time | 2.08 s |
| Peak resident memory | 144 MB |

The performance number for the search is the statevector optimum probability, 0.002687. The best-shot ratio of 1 only says that one of the 200 shots was an optimal feasible subset. It is not evidence that the optimizer concentrated on that subset.

The noisy hit rate 0.005 ± 0.005 overlaps both zero and the uniform draw 0.0156. Two hundred shots cannot separate this seed from uniform task selection. Greedy already returns the exact priority 18.

## Semantics

The Aer search and the AQT sample use the same QUBO, the same Ising image `s = 2v - 1`, and the same `(gamma, beta)` order. Both decode measurements with `logical_bits_from_qiskit_bitstring`, so qubit 0 is the first task bit. The sampled circuit is transpiled to the offline target and rejected if its RXX count or depth differs from the audit. `offline.ideal()` shot counts, when the grid runs, are a second labeled estimator. They are not the objective that COBYLA minimized.

## Remaining grid

The controlled grid is six cells: F2 and F3, seeds 0, 1 and 2. Each cell repeats the same procedure: at most 25 exact Aer evaluations, freeze `(gamma, beta)`, compile once, then 200 shots on `offline.ideal()` and 200 shots on `offline.noisy()`. A failed cell writes `failure.json` and the other cells continue. F1 is not in this grid.

One Slurm job, not yet submitted:

| Field | Request |
|---|---|
| Partition | `all` |
| Nodes / tasks / CPUs | 1 / 1 / 2 |
| Memory | 8G cap. The measured F2 peak was 144 MB |
| Time | 30 minutes. The cap is 0.5 node-hour |
| Licenses | none |
| Script | `scripts/t19_grid.sbatch` |

F2 seed 0 is included again so every cell uses this procedure, including the ideal-shot arm that job 2081 did not run. The original pilot archive is left in place.

Jobs 2077 and 2078 failed in 2 seconds because the environment had Aer 0.18.4. Job 2079 failed because the package was not installed. Job 2080 was submitted after that import error and is not a result. Those failures are recorded here and are not hidden.

## Why the optimum mass is small

The confirmatory Aer grid already showed that λ=41, which keeps the QUBO optimum aligned with the classical optimum, is not the penalty that gives shallow QAOA the most optimum mass. On F2 the ideal median optimum probability at λ=41 was about 0.010, below the uniform draw 0.0156. Job 2081 is one more seed in that range: the optimized statevector mass is 0.0027. The likely contributors are the penalty, depth p=1, and the slack bits, which make the ground state a stricter set than a correct task decision. This grid does not change λ, p, or the encoding, and it does not drop a seed. A λ sweep and a p=2 run are separate experiments after these six cells.

## Hardware estimate

This uses the compiled F2 circuit and does not submit it. Two hundred shots at 25 ms each would be 5 seconds. At 100 ms each they would be 20 seconds. Six noisy circuits, if F3 compiles to a similar duration, would be 30–120 seconds of QPU time. F3 depth and RXX count are not measured yet, so that product is only a scale. Statevector search time is CPU time and is not part of the QPU estimate. The 10 QPU-hour hardware budget is untouched.

## CPU accounting

Job 2081 used 4 seconds of one node on partition `all`. The failed attempts 2077–2080 used about 2 seconds each. Together this is well under 0.01 node-hour of the 10 node-hour emulator allocation. The unsubmitted grid caps another 0.5 node-hour and is expected to finish in a few minutes.

## Limitations

The problem is one satellite choosing tasks under three budgets. It is not contact-window scheduling and it is not a constellation. The quantum stage ran on a CPU node through an offline simulator. Native hardware gates, an emulator shot quota, and a device noise model are still unread. ORCA licenses are not configured in Slurm. No physical QPU job has been submitted.
