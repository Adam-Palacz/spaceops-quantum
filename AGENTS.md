# Agent Instructions — SpaceOps Quantum

Applies to Cursor, Codex, and all automated coding agents operating in this repository.

## Source-of-truth precedence
1. `specs/001-task-selection/spec.md` (behavior and acceptance conditions)
2. `docs/02-mathematical-model.md` (math, task set and reference result)
3. `docs/01-requirements.md` and `docs/04-experiment-protocol.md` (requirements and evidence)
4. `specs/001-task-selection/plan.md` (implementation approach)
5. `specs/001-task-selection/tasks.md` (current stage and ordering)
6. This document (agent conduct). For contradictions, **do not silently pick an interpretation**: record the inconsistency and propose a focused spec edit.

## Mandatory workflow
1. Read README and the above documents. Before implementing anything, summarize current phase, targeted task IDs, affected files and acceptance tests.
2. Work on the first uncompleted task only. Small, reviewable changes. Do not execute the entire roadmap in one prompt.
3. Write tests proving the documented behavior before or together with the implementation.
4. Run relevant tests/linters, record exact commands and whether they passed.
5. Update the task checklist with proof of completion and document any new assumptions in the spec/decision log.
6. Stop at every delivery gate; ask for the next phase or separate approval where required.

## Non-negotiable science rules
- Classical exhaustive oracle is independent of the QUBO and of Qiskit.
- F0 fixture: T1,T2,T5,T6; priority **27**; budgets used **9/10/10**; **37** feasible subsets of 64.
- If any code/test claims optimum 29, it is wrong: do not adjust the fixture to fit that number.
- `feasible` is calculated from original problem constraints, never from QUBO energy.
- QAOA output can be suboptimal; do not force or cherry-pick an optimum.
- Keep QUBO variable order and endianness explicit; unit-test decoding.
- Report logical-qubit count including slack: F0 is **18**, not 6.
- Never claim quantum advantage from 6-task simulation or label simulated noise as measurements from real hardware.

## Strict MVP exclusions
No multi-satellite scheduler, orbit/time windows, AI-agent features, spaceops_mission_agent_lab integration, Jetson, NVIDIA GPU deployment, Kubernetes, UI, database, external paid services, physical QPU runs or large experiments without prior acceptance.

## Security/cost
- Never print or commit access tokens, PIAST-Q portal credentials, private network endpoints, SSH keys or personally identifiable proposal contents.
- No live QPU execution, remote paid API calls, quota-consuming compute or speculative server deployments without explicit authorization.
- Safe actions: unit tests, package bootstrap, local simulation bounded by accepted test budgets.

## Engineering standards
- Python with type hints; small pure functions for mathematical logic.
- Separate domain/feasibility, classical baseline, QUBO/Ising, quantum backend and experiment/report layers.
- Avoid unpinned dependencies; resolve `uv.lock` in implementation step and record versions.
- Reproducible `pytest`, `ruff`, explicit CLI commands. No notebook-only business logic.
- No hidden repair of infeasible bitstrings or silent normalization of invalid input.
- Stable sorting/tie-breaking and explicit random seeds.
- Structured results include git SHA, scenario hash, packages, optimizer budget, shots, logical qubits, gate/depth metrics where available.

## Update format after each task
```text
Task completed: Txx
Files modified: ...
Tests: command → pass/fail + count
Validated behavior: ...
Known limitations: ...
Next permitted task: Tyy
```

If no code changes are needed, state this instead of inventing work. If a spec change is required, create a short decision note and request approval before violating the existing scope.
