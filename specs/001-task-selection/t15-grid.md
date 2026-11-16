# T15 confirmatory grid — locked, not executed

Status: locked on 2026-11-16. No cell of this grid has been run.

The machine-readable lock is `configs/t15_grid.yaml`. F1–F3 are `configs/f1_three_tasks.yaml`, `configs/f2_six_tasks.yaml`, and `configs/f3_six_tasks.yaml`. Each reference block was filled from `solve_exact` before any QAOA sample. Solvers still score the tasks; they do not read the reference as the answer.

## Instances

| Id | Tasks | Budgets | Logical qubits | Exact priority | Canonical subset | Optimal subsets | Feasible / total | Total priority |
|---|---|---|---|---|---|---|---|---|
| F1 | 3 | 1/1/1 | 6 | 5 | A | A and B | 4 / 8 | 13 |
| F2 | 6 | 1/1/1 | 9 | 18 | A, B, C | A, B, C only | 16 / 64 | 39 |
| F3 | 6 | 3/3/3 | 12 | 17 | A, B | A, B only | 13 / 64 | 38 |

F1 is the tie. F2 and F3 each have one optimal subset. Every fixture has a feasible nonempty subset and an infeasible subset. Total priority is at most 39, so λ=41 still puts every infeasible assignment at positive penalized energy while a feasible assignment with matching slack stays at `-priority`.

## Arms

All quantum cells use p=1. Depth p=2 is not in this grid.

- **Classical.** Exact and greedy on each scenario. Greedy seed 0, strategy `resource_density`. 6 runs. No statevector evaluation.
- **Penalty.** Ideal COBYLA QAOA. λ in {5, 10, 20, 41} on every resource. Seeds {0, 1, 2} draw the initial (γ, β) with `random.Random(seed)` on `[0, π)`. `max_evaluations` is 25. 36 runs, 900 statevector evaluations.
- **Shots.** Fixed (γ, β) = (0.1, 0.2). That pair is the pre-registered F0 smoke pair, not a result of this grid. `parameter_source` is `fixed` and the optimizer budget is null. λ=41. Shots {256, 1024}. Seeds {0, 1, 2}. 18 runs, 18 statevector evaluations.
- **Budget.** Ideal COBYLA at λ=41 and seed 0, with `max_evaluations` in {1, 10}. The 25-evaluation cell at the same λ and seed is already in the penalty arm and is not repeated. 6 runs, 33 statevector evaluations.

## Count and cost

66 archived runs. 951 statevector evaluations: 317 on each of F1, F2, and F3.

The only measured anchor is the F0 smoke: one ideal evaluation of all 262144 basis states took about 194–207 seconds. Scaling that assessment cost by `2^(n-18)` at 200 seconds gives about 15 seconds for F1, 124 seconds for F2, and 991 seconds for F3, about 19 minutes in total. That figure does not include a fixed per-evaluation startup. One extra second on every evaluation would add about 16 minutes. This is a planning estimate, not a measured T15 runtime.

No PIAST-Q call and no physical QPU execution are part of this grid.
