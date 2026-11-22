# T19 emulator plan — not run

Status: design only, revised after the T18 review. F2 and F3 are the evidence scenarios. F1 stays a diagnostic instance because it has 3 decision variables, not 6. Do not submit this plan, the F2 pilot, or any QPU job until the pilot below is approved.

The local Aer grid at 256 and 1024 shots stays a separate benchmark. It is not EuroHPC shot-budget evidence.

## Two different ideal numbers

`run_qaoa` on `aer-statevector` minimizes the exact expectation. Every basis-state probability is multiplied by its Ising energy, the probabilities sum to 1, and the objective has no shot noise. The archived result stores the chosen `(gamma, beta)`, the COBYLA trace, and the seed. `shots` is null.

`AQTProvider().offline.ideal()` does not return that expectation. A one-qubit Hadamard at 100 shots returned counts 47 and 53, and `get_statevector()` raised `QiskitError`. The same call at 1000 shots returned 495 and 505. Those are samples. Using them inside COBYLA would make the search follow shot noise.

The noisy stage does not optimize. It loads the archived `(gamma, beta)` from the exact trace, sets `parameter_source` to `fixed-from-ideal-trace`, and draws 200 shots on `offline.noisy()` with its own simulator seed. A 200-shot draw on `offline.ideal()` at those same parameters is allowed only as a labeled shot estimate. It is not the objective that was optimized.

## Evidence matrix, not run

Penalty λ = 41 on every resource. It is the correctness reference, not a tuned QAOA setting. Initial parameters for seed `s` come from `random.Random(s)` on `[0, π)`. COBYLA is hard-capped at 25 exact evaluations.

| Stage | Scenarios | Seeds | What one job does | Jobs | Shots |
|---|---|---|---|---|---|
| Exact ideal search | F2, F3 | 0, 1, 2 | at most 25 statevector evaluations | 6 | none |
| Noisy readout | F2, F3 | the matching seed | 1 circuit at the archived parameters | 6 | 200 |

Maximum noisy shots: 1,200. No job has more than one shot circuit. F1 is absent from this table.

Each exact job archives `optimizer_trace.json`, the winning `(gamma, beta)`, the seed, `parameter_source: optimizer`, and `shots: null`. Each noisy job stores the copied parameters, `parameter_source: fixed-from-ideal-trace`, the simulator seed, and every decoded shot. A failed job keeps `failure.json`.

Decoded metrics are the feasible-shot share, the optimum-hit share, and the approximation ratio of the best feasible shot. The exact statevector optimum probability at the same parameters is stored beside them and is not replaced by the shot share.

## 200-shot uncertainty

For `n = 200` and an optimum probability `p`, the binomial standard error is `sqrt(p (1-p) / n)`. On F2 the uniform task draw is `1/64 = 0.015625`, so the expected optimum count is 3.125 and the standard error is about 0.0088. A Wald interval of roughly ±0.017 is wider than the probability itself. Two hundred shots cannot show a small gap from that uniform draw. The pilot reports the count `k/200` and the exact statevector probability. It does not treat the shot rate as a precise probability.

## Two budgets

The emulator allocation is 10 HPC node-hours on the Slurm CPU partition. A statevector search and an offline noisy sample spend that budget. They do not spend QPU time.

The future hardware budget is 10 QPU hours. At 25 ms per shot, 1,200 noisy shots would be 30 s. At 100 ms per shot they would be 120 s. Those figures are estimates for a later device run. They are not subtracted from the 10 node-hours, and this plan does not submit them.

Measured CPU time for the exact F2 search at λ = 41, 25 evaluations, from the existing Aer archive: seed 0 took 2.68 s, seed 1 took 3.09 s, and seed 2 took 3.02 s. One F3 exact search, seed 0, took 39.3 s. Peak memory was not recorded. Job 2064, a 2-qubit offline sample, finished in 1 s under the cluster default memory.

## F2 pilot, waiting for approval

One job, not the six-scenario grid.

| Item | Value |
|---|---|
| Scenario | F2, 6 decision variables, 9 logical qubits |
| Seed | 0 |
| Exact search | Aer statevector, COBYLA, at most 25 evaluations, no shots |
| Noisy readout | `offline.noisy()`, 200 shots, the archived `(gamma, beta)`, no second search |
| Partition | `all` |
| Tasks / CPUs | 1 task, 2 CPUs |
| Memory | 4G requested. This is a cap with margin, not a measured peak |
| Time limit | 10 minutes. The measured exact F2 search is about 3 s; the limit is the Slurm cap |
| License and token | none |
| Script | `scripts/t19_f2_pilot.sbatch`, not submitted |

Expected outputs if the pilot is later approved: `optimizer_trace.json` with at most 25 rows of index, gamma, beta, and exact energy; a manifest with seed 0 and a null shot count for the search; a noisy record whose parameters equal that archived pair; counts out of 200; feasible share, optimum-hit share, approximation ratio, and the exact statevector optimum probability at those parameters. A Python import failure or a missing `qiskit-aer` install is a recorded failure, not a hidden retry. The cluster virtual environment has `qiskit-aqt-provider` 2.0.1. The exact search also needs `qiskit-aer` 0.18.2, which was not checked there.

The reserved cap is 10 minutes of one node, 0.17 node-hour if the scheduler billed the whole limit. Expected use is well under one minute. Either number is a small part of the 10 node-hour emulator allocation.
