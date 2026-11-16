# Confirmatory report — Feature 001

This report compares the locked T15 grid. It is an ideal-simulator and fixed-parameter shot study at QAOA depth p=1. It is not a hardware measurement, a noisy-simulator study, or a claim of quantum advantage.

Source: one execution of `uv run spaceops-quantum experiment grid --out results/t15` on 2026-11-16. Exit code 0. Process wall clock 542.3 s. Sum of archived cell times 535.8 s. 66 archives, 0 failures. Raw archives remain gitignored in `results/t15/`. The lock is `configs/t15_grid.yaml`. Rounded ranges below are minimum / median / maximum across the three seeds, to three decimal places.

## Problem and resources

Each instance is a synthetic three-budget task selection. The exact priority comes from `solve_exact` and does not use the reference block as the score. Logical width is `n_tasks + ceil(log2(budget+1))` per resource.

| Scenario | Tasks | Budgets | Logical qubits | Exact priority | Optimal subsets | Feasible task subsets | Cell time |
|---|---|---|---|---|---|---|---|
| F1 | 3 | 1/1/1 | 6 | 5 | A and B | 4 / 8 | 18.8 s |
| F2 | 6 | 1/1/1 | 9 | 18 | A, B, C only | 16 / 64 | 40.4 s |
| F3 | 6 | 3/3/3 | 12 | 17 | A, B only | 13 / 64 | 476.6 s |

F3 accounts for almost all of the solver time. Transpile time was not measured. Circuit depth was not varied: every quantum cell is p=1, so circuit-depth sensitivity is not evaluated.

## How to read a result

| Method | Performance number | What the best feasible priority means |
|---|---|---|
| Exact and greedy | Objective priority. Ratio is `value / optimum`. Gap is `(optimum - value) / optimum`. | The subset returned by that solver. |
| Ideal QAOA | `p_optimum`: statevector probability of every feasible subset whose priority equals the exact optimum. | Support fact only. All 42 ideal cells contain an optimum somewhere in the statevector, so their support approximation ratio is 1. That does not mean the search concentrated on the optimum. |
| Fixed-parameter shots | Shot frequency of those same optimal subsets, plus the feasibility rate. | Best feasible priority among the shots that were drawn. |

An infeasible subset with the same priority is not a success. F1 has two optimal subsets, A and B. Both count.

## Classical comparison

| Scenario | Exact priority | Greedy priority | Greedy ratio | Greedy gap |
|---|---|---|---|---|
| F1 | 5 | 3 | 0.600 | 0.400 |
| F2 | 18 | 18 | 1 | 0 |
| F3 | 17 | 17 | 1 | 0 |

Greedy stays feasible. On F1 it selects the cheaper competing task and misses both optimal subsets. On F2 and F3 it matches the exact objective. Classical cell time for all six solves was 1.4 s.

## Ideal QAOA

COBYLA, p=1, `max_evaluations=25`, initial (γ, β) drawn from seed on `[0, π)`. The same penalty is applied to energy, storage, and downlink. Cells: 3 scenarios × 4 penalties × 3 seeds = 36. Values are minimum / median / maximum of `p_optimum`.

| λ | F1 | F2 | F3 |
|---|---|---|---|
| 5 | 0.093 / 0.252 / 0.398 | 0.027 / 0.041 / 0.247 | 0.016 / 0.017 / 0.028 |
| 10 | 0.114 / 0.204 / 0.493 | 0.007 / 0.027 / 0.030 | 0.006 / 0.014 / 0.147 |
| 20 | 0.100 / 0.215 / 0.247 | 0.001 / 0.027 / 0.051 | 0.006 / 0.014 / 0.025 |
| 41 | 0.069 / 0.131 / 0.198 | 0.003 / 0.010 / 0.022 | 0.011 / 0.017 / 0.023 |

λ=41 is the correctness reference because each fixture's total priority is at most 39. It is not a tuned QAOA setting. No penalty here is uniformly best across scenarios and seeds.

Feasibility rate on those 12 penalty cells per scenario, again minimum / median / maximum:

| Scenario | Feasibility rate |
|---|---|
| F1 | 0.346 / 0.621 / 0.983 |
| F2 | 0.077 / 0.400 / 0.959 |
| F3 | 0.121 / 0.202 / 0.432 |

High feasibility is not high optimum mass. The F2 cell at λ=20 and seed 0 has feasibility 0.959 and `p_optimum` 0.001.

A separate budget arm at λ=41 and seed 0 changes only `max_evaluations`. The 25-evaluation point is the penalty-arm cell for that seed.

| Evaluations | F1 | F2 | F3 |
|---|---|---|---|
| 1 | 0.122 | 0.026 | 0.012 |
| 10 | 0.091 | 0.002 | 0.019 |
| 25, from the penalty arm | 0.131 | 0.003 | 0.023 |

On this single seed, a larger budget does not monotonically raise `p_optimum`. The `max_evaluations=1` cell emitted the expected COBYLA `MAXFUN` warning; the recorded trace still respects the hard cap.

Ideal cell time summed to 529.4 s.

## Fixed-parameter shots

(γ, β) = (0.1, 0.2), the pre-registered F0 smoke pair, not a parameter found by this grid. λ=41. `parameter_source` is `fixed` and the optimizer budget is null. 256 and 1024 shots use the same pair. Three simulator seeds.

| Scenario | Shots | Success frequency | Feasibility rate | Observed feasible priority |
|---|---|---|---|---|
| F1 | 256 | 0.250 / 0.254 / 0.281 | 0.535 / 0.535 / 0.555 | 5, 5, 5 |
| F1 | 1024 | 0.235 / 0.248 / 0.274 | 0.521 / 0.533 / 0.542 | 5, 5, 5 |
| F2 | 256 | 0.012 / 0.016 / 0.016 | 0.277 / 0.285 / 0.336 | 18, 18, 18 |
| F2 | 1024 | 0.017 / 0.019 / 0.019 | 0.271 / 0.286 / 0.314 | 18, 18, 18 |
| F3 | 256 | 0.039 / 0.039 / 0.039 | 0.277 / 0.289 / 0.305 | 17, 17, 17 |
| F3 | 1024 | 0.026 / 0.029 / 0.045 | 0.277 / 0.288 / 0.293 | 17, 17, 17 |

Every shot cell drew at least one feasible optimum, so the gap of the best observed shot is 0. Most shots are still not optimal: F2 success frequency stays near 0.02. Raising the shot count from 256 to 1024 does not show a consistent gain. Shot cell time summed to 4.9 s.

## Limitations

- The instances have 6, 9, and 12 logical qubits. F0, the 18-qubit encoding reference, is not part of this grid.
- Depth p=2, noise, and AQT-native compilation were not run. Gate and depth counts are absent.
- Ideal `approx_ratio` of 1 is a complete-support fact. The comparable quantum numbers are `p_optimum` and, for shots, the success frequency together with the feasibility rate.
- Three seeds are the whole locked sample. They show wide ranges, especially on F1 and on F2 at λ=5.
- No PIAST-Q job was submitted. Emulator shot limits remain unverified.
- These results do not transfer to orbital scheduling or a satellite constellation.
