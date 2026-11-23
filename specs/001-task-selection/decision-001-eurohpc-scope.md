# Decision 001 — EuroHPC scope delta

**Status:** accepted on 2026-11-15, with three amendments. T01–T13 are unchanged.
T14 may start. T15 does not start until its grid is locked under the rules below.

**Later execution, 2026-11-23:** The T19 offline grid was separately approved and Slurm job 2089 completed on a CPU node. The accepted bullets below are unchanged. The result is `docs/08-t19-emulator-report.md`. No physical QPU job was submitted.

## Already aligned

Feature 001 is task selection under three aggregate budgets. It is not contact-window scheduling, orbit propagation, or multi-satellite assignment. That boundary is already in `spec.md`, `docs/02-mathematical-model.md`, and `docs/00-vision.md`.

The frozen reference remains F0: six tasks, budgets 10/10/10, **18 logical qubits** (6 task bits + 4 slack bits on each of three resources), optimum **27**, tasks T1, T2, T5, T6, use 9/10/10, 37 feasible subsets of 64. QUBO, Ising, and p=1 QAOA are not rebuilt.

PIAST-Q access is not verified. Native AQT operations are already described as the R, RZ, and RXX family, with the rule that real targets come from the backend. Noisy simulation and the JSONL experiment archive are still later work. G5 stays deferred.

## Accepted scope

1. **Smaller instances for the experiment grid.** Keep F0 as the 18-qubit reference. Add deterministic scenarios whose logical width is inside 6–12, using the existing width rule `n_tasks + ceil(log2(budget+1))` per resource. Widths that fall out of that rule without a new encoding:
   - 3 tasks, budgets 1/1/1 → 6 logical qubits
   - 6 tasks, budgets 1/1/1 → 9 logical qubits
   - 6 tasks, budgets 3/3/3 → 12 logical qubits
   Each instance gets its optimum, feasible count, and resource use from `solve_exact` before any QAOA run. No optimum is chosen after seeing quantum samples.

2. **Where they enter.** T14 still builds the existing manifest, JSONL samples, and metrics for one scenario. The new instances are inputs to the T15 grid, not a new solver. The grid is locked before results are read.

3. **Feature 002 stays outside 001.** Temporal downlink scheduling, contact windows, and transmission timing are a separate feature after this experiment closes. No schema change and no time index in Feature 001.

4. **Emulator limits stay unverified notes for T17.** Record, but do not treat as measured, the claimed ceilings: up to 200 shots per circuit, about 50 circuits per job, and native R, RZ, and RXX gates. T17 checks them in the real environment before any emulator job. T18 still measures depth and two-qubit gates from the backend rather than from a hardcoded gate set. T19 still requires a separate approval to execute.

## Accepted decisions

- **Local shot budget.** Keep 256 and 1024 for local Aer. The claimed emulator ceiling of 200 shots per circuit stays unverified until T17. Do not copy the local counts onto PIAST-Q without that check and a separate execution approval.
- **Depth.** The confirmatory grid stays at p=1. p=2 is a separate later experiment. Circuit-depth sensitivity is not yet evaluated, and reports must say so.
- **F0.** F0 remains the 18-qubit encoding reference and one bounded execution smoke. It is not evidence that QAOA found the optimum. A complete statevector support that contains priority 27 only shows that the decoder saw every assignment.
- **Nontrivial 6–12 qubit instances.** F1, F2, and F3 are the confirmatory scenarios. Width alone is not enough: each one must contain competing tasks, at least one feasible nonempty subset, at least one infeasible subset, and an optimum computed by `solve_exact` before any QAOA sample is read. The reference block may store that optimum; solvers must not use it as the score.
  - **F1:** 3 tasks, budgets 1/1/1, 6 logical qubits.
  - **F2:** 6 tasks, budgets 1/1/1, 9 logical qubits.
  - **F3:** 6 tasks, budgets 3/3/3, 12 logical qubits.
  These identifiers replace the earlier unnamed “priorities / tight budget / tie” trio. The fixtures themselves are written when the T15 grid is locked, not during T14.
- **Optimizer accounting.** Before T15, lock `max_evaluations` and the seed list. A 256-versus-1024 comparison uses the same fixed parameters, so the shot count is not mixed with a new optimization. An optimizer comparison uses the same shot count and records the evaluation limit. T14 stores `parameter_source` and `optimizer_max_evaluations` so those arms stay distinguishable. `optimizer_max_evaluations` is null on a fixed-parameter sample.
- **Archive before the grid.** The T14 archive schema is corrected before T15. Each run stores the full scenario, wall time, original violations, equality residuals, and penalized QUBO energy. Optimized QAOA stores its evaluation budget and trace. Fixed-parameter samples are not reported as optimized QAOA. Schema v2 is accepted.
- **Success and the locked grid.** Optimum-hit probability counts every feasible subset whose priority equals the exact objective. `configs/t15_grid.yaml` locks F1–F3, penalties, seeds, shots, the fixed parameter pair, and the optimizer budgets. The locked cells were executed once after that acceptance; the aggregate record is in `specs/001-task-selection/t15-grid.md`. On an ideal statevector record, the performance number is `p_optimum`; support-derived priority and approximation ratio are not QAOA performance.

## Not in this delta

No rewrite of T01–T13. No change to the QUBO or Ising convention. No new encoding that drops slack. No PIAST-Q adapter, credentials, or job submission. No Feature 002 spec file until Feature 001 is closed and that feature is requested.
