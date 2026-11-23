# T19 emulator benchmark — for second assessment

This report is ready for review. The email to PCSS has not been sent. It does not request a physical QPU run.

Slurm job 2089 completed the six-cell grid on one CPU node of partition `all`: exit code 0, elapsed 51 seconds, log line `failed 0`. The printed cell summary is transcribed in `docs/aggregates/t19-2089-printed-summary.json`. The full `cell.json` files, optimizer traces, and `grid_summary.json` are still only in `~/t19-grid-v2` on the cluster. They are not in this repository. This report does not invent the fields that were not printed.

## Claim

The benchmark shows that the same p=1 QAOA circuit can be optimized on Aer and then sampled on the AQT offline ideal and noisy simulators. That is AQT-compatible execution on a CPU node. It is not a quantum advantage. On both evidence scenarios the greedy baseline already matches the exact priority, and the optimized statevector optimum probability stays near or below a uniform draw over the 64 task subsets.

Feature 001 is task selection under three aggregate budgets. It does not assign contact windows, transmission times, or a constellation.

## What was measured

Slurm job 2081, also on partition `all`, completed with exit code 0 in 4 seconds. Its archive is in the repository at `specs/001-task-selection/f2-pilot-seed0/pilot.json`. The backend was `offline_simulator_noise` from `qiskit-aqt-provider` 2.0.1, with `qiskit-aer` 0.18.2. No API token was set and no remote backend was called. That pilot sampled only the noisy arm.

| Item | Value |
|---|---|
| Scenario | F2, 9 logical qubits, exact priority 18 |
| Depth and penalty | p=1, λ=41 on every resource |
| Seed | 0 |
| Exact search | 25 COBYLA evaluations, 1.08 s |
| Statevector optimum probability | 0.002687439220942795 |
| Noisy shots | 200, seed 0, 0.075 s |
| Noisy optimum hits | 1/200 = 0.005 |
| Binomial standard error | 0.004987 |
| Feasible-shot rate | 0.445 |
| Best observed feasible priority | 18, so the best-shot ratio is 1 |
| Greedy priority | 18 |
| Uniform task draw | 1/64 = 0.015625 |
| Feasible-uniform draw | 1/16 = 0.0625 |
| Compiled circuit | depth 29, 17 RXX, native gates only |
| Scenario hash | `7b70a751ed15d93beabee8c0ee7881cfea0f3baee6b37eb52fea7b738a37943c` |
| Process wall time | 2.08 s |
| Peak resident memory | 144 MB |

The performance number for the search is the statevector optimum probability. The best-shot ratio of 1 only says that one of the 200 shots was an optimal feasible subset.

## Semantics

The Aer search and the AQT sample use the same QUBO, the same Ising image `s = 2v - 1`, and the same `(gamma, beta)` order. Both decode measurements with `logical_bits_from_qiskit_bitstring`, so qubit 0 is the first task bit. The sampled circuit is transpiled once to the offline target and the cell is rejected if its RXX count or depth differs from the audit. `offline.ideal()` shot counts are a second labeled estimator. They are not the objective that COBYLA minimized.

## Six-cell grid

Job 2089 requested 1 node, 1 task, 2 CPUs, an 8G memory cap, and a 30-minute limit. The cap is 0.5 node-hour. No ORCA license was requested. The script is `scripts/t19_grid.sbatch`. The output directory was `~/t19-grid-v2`, so the six `failure.json` files from job 2088 remain in `~/t19-grid`.

Job 2088 is a recorded failure. All six cells were refused because the ideal backend id is `offline_simulator_no_noise`, which does not contain the word `ideal`. Elapsed time was 49 seconds and the log said `failed 6`. The code that accepts that id is commit `5b03a655f55c3da8424c1c9d9326eb1be72955c8`. The job script exits unless `SPACEOPS_T19_SHA` equals the cluster `HEAD` and unless `qiskit-aer` is exactly 0.18.2. The pasted log of job 2089 does not echo that SHA. It does show exit 0 after that fix.

Each cell is p=1 and λ=41, at most 25 exact Aer evaluations, then 200 shots on `offline.ideal()` and 200 shots on `offline.noisy()`. The runner aborts a cell unless the compiled circuit uses only the offline native gates and the sampled RXX count and depth match the audit. `failed 0` means all six cells passed that check. The boolean itself is inside `cell.json`, which was not copied here.

F2 exact priority is 18 and greedy is 18. F3 exact priority is 17 and greedy is 17. A uniform draw over task subsets hits the optimum with probability 1/64 on both. A draw over only the feasible subsets hits it with probability 1/16 on F2 and 1/13 on F3. Those classical figures come from the fixtures and the unit tests. They were not re-read from the cluster archives.

The statevector probabilities and feasibility rates below are the printed values: six decimal places and three decimal places. Hit counts are integers. The standard error is `sqrt(k/200 * (1 - k/200) / 200)`.

| Cell | Statevector p | Ideal hits | Ideal SE | Noisy hits | Noisy SE | Noisy feasible | RXX | Depth |
|---|---|---|---|---|---|---|---|---|
| F2 seed 0 | 0.002687 | 1 | 0.0050 | 1 | 0.0050 | 0.445 | 17 | 29 |
| F2 seed 1 | 0.001247 | 1 | 0.0050 | 0 | 0 | 0.425 | 17 | 29 |
| F2 seed 2 | 0.022089 | 6 | 0.0121 | 7 | 0.0130 | 0.265 | 17 | 30 |
| F3 seed 0 | 0.023119 | 4 | 0.0099 | 3 | 0.0086 | 0.190 | 42 | 48 |
| F3 seed 1 | 0.011408 | 3 | 0.0086 | 1 | 0.0050 | 0.140 | 42 | 47 |
| F3 seed 2 | 0.017216 | 2 | 0.0070 | 2 | 0.0070 | 0.225 | 42 | 48 |

F2 seed 0 repeats the job 2081 statevector probability to the six printed decimals, and it repeats the 1/200 noisy count, feasibility 0.445, 17 RXX, and depth 29. The grid parameters `(gamma, beta)` were not in the print. The pilot archive has them for that one seed only: gamma 2.5245355998100076, beta 2.3698904883880076.

The median statevector probability is 0.002687 on F2 and 0.017216 on F3. Divided by the uniform draw 0.015625, the six ratios are 0.172, 0.080, 1.414, 1.480, 0.730, and 1.102. Three seeds are below the uniform draw and three are above it. Every seed is below the feasible-uniform draw (0.0625 on F2, about 0.0769 on F3). Noisy hit counts stay within one or two shots of the ideal-simulator counts. Greedy already matches the exact priority on both scenarios, so its approximation ratio is 1.

The best-shot approximation ratio is not the claim. A single optimal shot makes that ratio 1 even when the hit frequency is 0.005. F2 seed 1 had no optimal noisy shot. The Wald standard error of a zero count is 0, which does not mean the probability is known to be 0. A count of 0 in 200 shots is still compatible with a rate of about one percent.

A uniform draw expects 3.125 optimum hits in 200 shots, with standard error 0.0088 on the frequency. None of the noisy frequencies is separated from 0.015625 by that uncertainty. Two hundred shots cannot support an advantage claim.

## Why the optimum mass is small

The confirmatory Aer grid already showed that λ=41, which keeps the QUBO optimum aligned with the classical optimum, is not the penalty that gives shallow QAOA the most optimum mass. On F2 the ideal median optimum probability at λ=41 was about 0.010, below the uniform draw 0.0156. The six new statevector values sit in that same range. The likely contributors are the penalty, depth p=1, and the slack bits, which make the ground state a stricter set than a correct task decision. This grid does not change λ, p, or the encoding, and it does not drop a seed. A λ sweep and a p=2 run were not started.

## Evidence that is and is not in the repository

Present and checked locally:

- The runner `src/spaceops_quantum/experiment/t19_grid.py` and `scripts/t19_grid.sbatch` at commit `5b03a655f55c3da8424c1c9d9326eb1be72955c8`.
- The F2 pilot archive from job 2081, including gamma, beta, the unrounded statevector probability, Aer 0.18.2, the noisy backend id, and the scenario hash.
- Recomputing `scenario_hash` from `configs/f2_six_tasks.yaml` reproduces that pilot hash.
- Recomputing `scenario_hash` from `configs/f3_six_tasks.yaml` gives `b0befab7428e1379ca735a9447cced9a4c6dd162f8623c24731bf7def006e585`. The grid writer does not store this hash, and job 2089 did not print it.
- The printed hit counts, from which the standard errors above are calculated.

Not copied from the cluster, so not independently verified in this commit:

- `~/t19-grid-v2/<cell>/cell.json` for the six cells.
- `~/t19-grid-v2/<cell>/optimizer_trace.json` for the six cells.
- `~/t19-grid-v2/grid_summary.json`.
- The Slurm files `t19-grid-2089.out` and `t19-grid-2089.err`, beyond the pasted line `failed 0` and the six-line print.
- Package versions inside the grid archives. The sbatch script asserts Aer 0.18.2 and then continues. Job 2089 reached `failed 0`, so that assert passed. The cell writer does not record `qiskit`, `qiskit-aer`, `qiskit-aqt-provider`, or `spaceops-quantum` versions.
- Backend ids inside the grid archives. The runner checks them and does not store them. The known ids from job 2064 are `offline_simulator_no_noise` and `offline_simulator_noise`.
- `(gamma, beta)` and the COBYLA trace for the five cells other than the F2 seed-0 pilot.
- A second `sshare` reading after job 2089. The reading that showed raw usage 0 was taken before this grid.

No cell was rerun to fill those gaps.

## Hardware estimate and HPC time

These are different budgets.

The HPC emulator allocation is CPU time on partition `all`. Job 2089 used 51 seconds of one node. Job 2088 used 49 seconds. Job 2081 used 4 seconds, and the earlier failed pilots were about 1–2 seconds each. Parent elapsed time since 19 November is under two minutes, on the order of 0.03 node-hour of the proposed 10 node-hour allocation. The portal balance was not read. The pre-submission `sshare` output showed raw usage 0 and did not print a numeric remainder. It was not read again after job 2089.

The 10 QPU-hour hardware budget was not used. No physical QPU job was submitted. The compiled circuits that would be the input to such a job are now measured on the offline target: F2 has 17 RXX gates and depth 29 or 30, and F3 has 42 RXX gates and depth 47 or 48. Two hundred shots at 25 ms each are 5 seconds of QPU time; at 100 ms each they are 20 seconds. Six circuits, one per cell, would be 30–120 seconds. The matching ideal-simulator arm is a CPU sample of the same compiled circuit, not a second QPU submission. Statevector search time is CPU time and is not part of the QPU estimate.

## Limitations

The problem is one satellite choosing tasks under three budgets. It is not contact-window scheduling and it is not a constellation. The quantum stage ran on a CPU node through offline simulators. A device gate list, an emulator shot quota, and a device noise model were not read. ORCA licenses are not configured in Slurm. The offline RXX counts are not a hardware-backend measurement. No physical QPU job has been submitted, and this report does not ask for one.
