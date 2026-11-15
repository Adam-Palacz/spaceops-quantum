# Feature Spec 001 — Task Selection Benchmark

**Status:** READY FOR IMPLEMENTATION (once reviewed). **Owner:** project maintainer. **Dependencies:** none.

## User story
As an R&D engineer evaluating quantum optimization for civilian Earth observation, I want to load a small documented task-selection scenario, obtain a provably optimal classical result, encode it as QUBO, run a controlled QAOA experiment and compare independently evaluated feasible task selections in a reproducible report.

## Boundary
Single problem instance class: choose a subset of candidate tasks. Aggregate energy/storage/downlink budgets. Do not treat this as assigning observation times, transmitting data in contact windows, or choosing from multiple satellites.

## Inputs
- UTF-8 YAML path, strict schema in `docs/03-architecture.md`.
- Valid task: unique string ID, strictly positive integer `priority`, non-negative integer energy/storage/downlink.
- Budgets: nonnegative integers. Negative or nonintegral resource values, duplicate IDs, missing fields, empty task list and incompatible schema versions must fail with clear errors.
- Experiment parameters: solver, backend, QAOA depth p, penalty vector, shots, seed, optimizer budget, run ID.

## Outputs
- Exact optimum and feasibility trace.
- QUBO coefficients, constant, variable layout, logical qubit count, optional Ising equivalent.
- Solver solutions evaluated by the **same original evaluator**.
- Reproducible experiment record with all metrics and provenance per docs.
- A summary report and publication-facing tables without unsupported claims.

## Scenarios (Given/When/Then)

### S001 — Golden classical fixture
**Given** `configs/six_tasks.yaml`, **when** exhaustive solver runs, **then** it examines 64 task subsets, finds 37 feasible, chooses `T1,T2,T5,T6` with objective 27 and resource use energy=9, storage=10, downlink=10.

### S002 — Independent invalid subset
**Given** any set of selected task IDs, **when** evaluated, **then** objective and three resource totals are calculated from source tasks, and `feasible` is true **iff** all budgets are satisfied, with per-resource violations otherwise. No QUBO logic is involved.

### S003 — Correct QUBO encoding
**Given** F0 and λ=41 for each constraint, **when** QUBO is expanded and audited, **then** it uses 18 logical binary variables (6 task + 4 slack per constraint); QUBO energy matches the direct penalty expression; and its global optimum matches the classical optimum under a verified procedure.

### S004 — Quantum simulation sample
**Given** a supported Qiskit/Aer environment and explicit run parameters, **when** p=1 QAOA executes on local ideal or sampled simulator, **then** it produces a traceable output distribution, each measured bitstring decodes through the declared mapping, and every candidate is independently evaluated. QAOA is allowed not to find optimum.

### S005 — Fair reporting
**Given** exact, greedy and QAOA results on the same scenario, **when** reporting runs, **then** results include solver/backend and budget parameters, feasible-sample rate, best feasible utility or null, approximation ratio/gap where valid, success probability, timing and quantum resource data when available. Invalid samples are neither discarded without accounting nor silently repaired.

### S006 — Reproducibility
**Given** the same scenario, seed and locked software environment, **when** rerun deterministically under an equivalent backend, **then** classical outputs match exactly and stochastic outputs are comparable within explicitly reported sampling uncertainty; do not demand impossible exact equality from different noisy hardware.

## Rejection / non-goals
A proposal to add orbit propagation, time windows, mission agent integration, satellite assignment, LLM-based priorities or QPU submission must be moved to a separate feature spec and explicitly approved. Do not proceed by extending this spec in-place during implementation.

## Acceptance checklist
- [x] G1: oracle and input validation tests pass; fixture produces 27 and 37.
- [x] G2: QUBO and Ising mapping tests pass; correct 18-bit layout.
- [x] G3: ideal QAOA p=1 local bounded run is reproducible and decoded correctly.
- [ ] G4: metrics, output schema, report and README commands validated.

References: `docs/01-requirements.md`, `docs/02-mathematical-model.md`, `docs/04-experiment-protocol.md`.
