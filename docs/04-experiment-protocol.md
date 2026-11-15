# Experimental Design and Reporting Protocol

## Research questions
- **RQ1 — Encoding correctness:** Does the QUBO model preserve the intended constrained optimum at a sufficiently large penalty?
- **RQ2 — Algorithm quality:** What is QAOA's best feasible task value, optimum-hit probability, and valid-sample rate compared with exact and cheap classical methods?
- **RQ3 — Hardware realism:** How do penalty, circuit depth, shot count, noise and AQT-native compilation change feasibility and resources?

## Fixed fixture and derived scenarios
- **F0:** `configs/six_tasks.yaml` (verified optimum 27, 37 feasible of 64).
- **F1–F3 (later within MVP):** deterministic synthetic variants using changed priorities, tight budgets, and a simple degenerate/tie case; record generator seed, scenario and oracle. Avoid selective favorable instances.
- Do not assert applicability to 100-satellite constellations from 6-task results.

## Comparison arms
| Arm | Type | Required for MVP | Notes |
|---|---|---|---|
| Exhaustive oracle | Classical exact | Yes | 2^6 = 64 task subsets; ground truth |
| Greedy | Classical heuristic | Yes | Deterministic resource-adjusted priority ranking and stable tie-break; must be feasible |
| QAOA ideal | Quantum simulation | Yes | p=1 initially; no quantum-advantage claim |
| QAOA sampled | Quantum simulation | Yes | finite shots, stable seed; decode outcomes |
| QAOA noisy | Quantum simulation | Gate G4/G5 optional | Explicit noise parameters/provenance |
| QAOA AQT/emulator | Remote/local emulation | After G4 | No remote execution without access verification |
| QAOA PIAST-Q physical | Real hardware | **Out of MVP** | Requires new allocation/approval |

## Variables and study sequence
1. **Correctness:** fixture F0 exact, QUBO verification, ideal QAOA p=1 smoke run.
2. **Penalty sensitivity:** fixed p=1, compare λ in `{5, 10, 20, 41}`; report BOTH QUBO energy and original problem metrics. The exact penalty is not a tuned quantum optimum.
3. **Depth:** compare p=1 and p=2 after p=1 is stable; document circuit width and depth.
4. **Sampling:** compare budgeted shot counts (e.g., 256 and 1024), using fixed seeds (e.g., 0, 1, 2) for initial runs. Larger sweeps only after reproducibility is established.
5. **Noise/compilation:** report compiled gate histogram, especially 2-qubit interactions, before trying emulator/QPU. Avoid pretending generic noise equals PIAST-Q noise.

Lock a final comparison grid *before* looking at results. A quick exploratory run is allowed but labeled exploratory and excluded from confirmatory summary.

## Fairness rules
- All methods solve the same original `Scenario` and use the same independent evaluator.
- A classical oracle is ground truth, not a fair runtime competitor for tiny n by itself; keep a cheap greedy baseline as practical reference.
- Report QAOA optimizer iterations, objective evaluations, total circuit executions and shots; compare classical algorithms using their evaluation budget, not just wall time.
- Record total time broken down into preprocessing, transpilation, optimization, sampling and postprocessing. On QPU report remote queue time separately.
- If solver samples no feasible solution, keep `best_feasible_priority = null`, `feasibility_rate = 0`; do not replace with best infeasible result.
- Do not cherry-pick a seed. Include all planned runs and summary mean/median/range where sensible.
- The objective is **maximized**; for feasible solutions with known optimum >0: `approx_ratio = value/optimum`, `relative_gap = (optimum-value)/optimum`. For invalid solutions both are null.
- Success probability is the **frequency of sampling an original-problem optimum**, not the frequency of minimum QUBO energy unless both coincide.

## Required artifacts per experiment
```text
results/<experiment-id>/
  manifest.json         # exact config, dependency+git versions, seeds
  samples.jsonl         # bit strings, counts, independent decoded evaluation
  metrics.json          # success, feasible rates, best, cost/depth/timing
  circuit.qpy           # optional verified serialized circuit
  summary.csv           # derived, never manually edited
```

Never commit generated secrets or access tokens. Gitignore large raw results; commit only sanitized aggregate results deliberately selected for the public paper.

## Output / technical paper outline
1. Motivation and restrained problem statement.
2. Knapsack formulation, QUBO slack mapping and qubit overhead.
3. Classical baselines and QAOA configuration.
4. Ideal, sampled, noisy and compilation results (separate plots).
5. Ablations: λ and p, with feasibility and optimality metrics.
6. Limitations: toy tasks, proxies, no orbital truth, no demonstrated advantage, hardware access status.
7. Next work: model size, multi-satellite schedule and PIAST-Q validation.

## Hard gate before PIAST-Q submission
Demonstrate all mathematical tests pass; capture circuit resource estimates; reconcile installed provider with actual backend access and native gates; verify consumption and approved allowance in portal; require explicit approval before physical execution.
