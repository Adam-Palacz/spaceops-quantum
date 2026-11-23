# T19 emulator plan

Status: the offline CPU grid has been run. F2 and F3 are the evidence scenarios. F1 stays a diagnostic instance because it has 3 decision variables, not 6. Job 2081 completed the F2 seed-0 noisy pilot. Job 2089 completed the six-cell grid. The numbers and the missing archives are in `docs/08-t19-emulator-report.md`. No QPU job is authorized by this note.

The local Aer grid at 256 and 1024 shots stays a separate benchmark. It is not EuroHPC shot-budget evidence.

## Two different ideal numbers

`run_qaoa` on `aer-statevector` minimizes the exact expectation. Every basis-state probability is multiplied by its Ising energy, the probabilities sum to 1, and the objective has no shot noise. The archived result stores the chosen `(gamma, beta)`, the COBYLA trace, and the seed. `shots` is null.

`AQTProvider().offline.ideal()` does not return that expectation. A one-qubit Hadamard at 100 shots returned counts 47 and 53, and `get_statevector()` raised `QiskitError`. The same call at 1000 shots returned 495 and 505. Those are samples. Using them inside COBYLA would make the search follow shot noise.

The noisy stage does not optimize. It loads the archived `(gamma, beta)` from the exact trace, sets `parameter_source` to `fixed-from-ideal-trace`, and draws 200 shots on `offline.noisy()` with its own simulator seed. A 200-shot draw on `offline.ideal()` at those same parameters is allowed only as a labeled shot estimate. It is not the objective that was optimized.

## Evidence matrix

The executed runner adds a 200-shot `offline.ideal()` arm beside the noisy arm. Both arms use the parameters returned by the exact Aer search. The ideal shots are a labeled sample, not the COBYLA objective. Job 2089 ran all six cells in one Slurm job and finished in 51 seconds with no failed cell. Job 2088, the attempt before the ideal-backend id fix, failed all six cells and is kept as a failure record.

Penalty λ = 41 on every resource. It is the correctness reference, not a tuned QAOA setting. Initial parameters for seed `s` come from `random.Random(s)` on `[0, π)`. COBYLA is hard-capped at 25 exact evaluations.

| Stage | Scenarios | Seeds | What the cell does | Cells | Shots |
|---|---|---|---|---|---|
| Exact ideal search | F2, F3 | 0, 1, 2 | at most 25 statevector evaluations | 6 | none |
| Ideal readout | F2, F3 | the matching seed | the same compiled circuit | 6 | 200 |
| Noisy readout | F2, F3 | the matching seed | the same compiled circuit | 6 | 200 |

Job 2089 ran this whole table as one CPU job: 1,200 ideal-simulator shots and 1,200 noisy-simulator shots. F1 is absent.

Each cell writes `cell.json` and `optimizer_trace.json`. The trace has the COBYLA rows. The cell stores one `(gamma, beta)` pair and uses it for the audit and both shot arms. It does not write `parameter_source`, a scenario hash, package versions, or the raw count dictionary. A failed cell writes `failure.json` and the other cells continue.

Decoded metrics are the feasible-shot share, the optimum-hit share, and the approximation ratio of the best feasible shot. The exact statevector optimum probability at the same parameters is stored beside them and is not replaced by the shot share.

## 200-shot uncertainty

For `n = 200` and an optimum probability `p`, the binomial standard error is `sqrt(p (1-p) / n)`. On F2 the uniform task draw is `1/64 = 0.015625`, so the expected optimum count is 3.125 and the standard error is about 0.0088. A Wald interval of roughly ±0.017 is wider than the probability itself. Two hundred shots cannot show a small gap from that uniform draw. The pilot reports the count `k/200` and the exact statevector probability. It does not treat the shot rate as a precise probability.

## Two budgets

The emulator allocation is 10 HPC node-hours on the Slurm CPU partition. A statevector search and an offline noisy sample spend that budget. They do not spend QPU time.

The future hardware budget is 10 QPU hours. It was not spent. The compiled offline circuits from job 2089 are 17 RXX and depth 29–30 on F2, and 42 RXX and depth 47–48 on F3. Six such circuits at 200 shots would be 30 s of QPU time at 25 ms per shot and 120 s at 100 ms per shot. Those figures are not subtracted from the 10 node-hours, and this plan does not submit them. The ideal-simulator arm is CPU time on the same compiled circuit.

Measured CPU time for the exact F2 search at λ = 41, 25 evaluations, from the existing Aer archive: seed 0 took 2.68 s, seed 1 took 3.09 s, and seed 2 took 3.02 s. One F3 exact search, seed 0, took 39.3 s. Peak memory was not recorded. Job 2064, a 2-qubit offline sample, finished in 1 s under the cluster default memory.

## F2 pilot

Job 2081 completed this pilot. The archive is `specs/001-task-selection/f2-pilot-seed0/pilot.json`. The table below is the request that was approved, not an unsubmitted plan.

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
| Script | `scripts/t19_f2_pilot.sbatch`, submitted as job 2081 |

The pilot archive stores the optimizer parameters, 25 evaluations, 1 optimum hit in 200 noisy shots, and the statevector probability. Jobs 2077 and 2078 failed because Aer was 0.18.4. Job 2079 failed because the package was not installed. Job 2080 was submitted after that import error and is not a result. The grid script later asserted Aer 0.18.2 before job 2089.

The reserved cap is 10 minutes of one node, 0.17 node-hour if the scheduler billed the whole limit. Expected use is well under one minute. Either number is a small part of the 10 node-hour emulator allocation.
