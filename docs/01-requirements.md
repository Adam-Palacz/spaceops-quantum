# Product & Research Requirements Document (PRD)

**Version:** 0.1 / candidate spec. **Feature:** `001-task-selection`.

## Problem
A civilian Earth-observation operator has candidate tasks, each with a scalar utility (`priority`) and resource costs. Select which tasks to execute while respecting three aggregate budgets. For MVP these are **dimensionless normalized budget units**; they are not physically faithful power, storage occupancy, or transmission windows.

## Personas / use
- Research engineer: verify mathematical correctness and compare solvers.
- HPC/QPU engineer: understand qubit count and compilation cost before running on scarce resources.
- Space-operations stakeholder: interpret chosen task set, utility, budget use and limitations.

## Functional requirements
| ID | Priority | Requirement | Acceptance evidence |
|---|---|---|---|
| FR-01 | MUST | Read and validate YAML scenario (`tasks`, `budgets`, schema version) | Schema tests for valid/invalid values |
| FR-02 | MUST | Independent deterministic feasibility and objective evaluation | Unit tests / edge cases |
| FR-03 | MUST | Enumerate all task subsets and identify feasible exact optimum | Golden fixture: objective 27, selected T1/T2/T5/T6; 37 feasible |
| FR-04 | MUST | Implement at least one deterministic classical heuristic | Fixed seed/tie-breaking, feasible output |
| FR-05 | MUST | Construct QUBO for inequality budgets with non-negative encoded slack variables | Verified energy / constraint equivalence tests |
| FR-06 | MUST | Report exact logical qubit count prior to any quantum run | Six task bits + 12 slack bits = 18 for fixture |
| FR-07 | MUST | Implement ideal-statevector QAOA with configurable p and optimizer budget | Reproducible seeded smoke experiment |
| FR-08 | MUST | Implement shot-based QAOA / sampled outcome decoding | All decoded bitstrings checked by independent evaluator |
| FR-09 | MUST | Evaluate original objective, feasibility, gap, success probability, cost and quantum resources | Structured JSON/CSV records and summary |
| FR-10 | MUST | Create a reproducible command interface for validate/exact/QUBO/experiment/report | CLI integration tests and usage docs |
| FR-11 | SHOULD | Noisy Aer simulator and backend compilation metrics | Ideal/noisy comparison, native gate histogram |
| FR-12 | LATER | Adapt to PIAST-Q-compatible emulator through isolated backend plugin | Emulator access / credentials validated; no hardware spend |

## Nonfunctional requirements
- **Reproducibility:** scenario hash, git SHA, lockfile hash, Qiskit/Aer/provider versions, Python version, OS/hardware, seed, shots, QAOA p, λ, optimizer, evaluation count, transpiler settings, backend ID and run timestamp saved.
- **Auditability:** every proposed subset evaluated with the *original* constraints; do not infer validity from penalized QUBO energy.
- **Testing:** pytest tests for parsing, solver correctness, QUBO conversion, bit order, sampler decoding, output schemas.
- **Cost control:** no unapproved remote or physical QPU calls; no heavy parameter sweeps in unit tests.
- **Clear boundaries:** domain and classical code must work with no quantum package imported.
- **Public-repo hygiene:** no API tokens, infrastructure endpoints requiring confidentiality, private proposals, personal IDs, or sensitive access files committed.

## Release gates
### G1 — Classical oracle
Sample fixture yields exact best priority 27; all constraints satisfied, 37/64 feasible. Other synthetic cases and ties have tests.

### G2 — QUBO correctness
For small instances, every x has an expected best slack penalty. QUBO quadratic expression matches the direct penalty evaluator. With a conservative λ, the global QUBO optimum decodes to the classical optimum.

### G3 — Quantum runnable
Ideal simulator can run p=1 with bounded optimizer evaluations; decode is correct; seed and metrics stored. Failure to find optimum is recorded as such, not marked as software failure.

### G4 — Benchmark credible
At least exact, greedy, QAOA ideal, QAOA sampled; comparisons use identical instances and fully documented budgets, uncertainty and hardware/runtime contexts.

### G5 — Emulator candidate
Native-gate compilation verified, circuit depth and 2-qubit gate count measured, access approved, usage estimate evaluated. Only then consider QPU expansion.

## Definition of done for MVP
G1–G4 pass; README command examples work cleanly from a fresh checkout; a generated report compares solver results and explicitly states that full satellite scheduling and quantum advantage are not established.
