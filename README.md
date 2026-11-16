# SpaceOps Quantum

**Hybrid Quantum–Classical Optimization for Earth Observation Satellite Task Selection**

> Status: G4 in progress. G3 passed. One run archives the full scenario, samples, metrics, timing, and, for optimized QAOA, the evaluation trace. Fixed parameters are not reported as an optimized search. The confirmatory F1–F3 grid is locked in `configs/t15_grid.yaml` and has been executed once. The aggregate record is in `specs/001-task-selection/t15-grid.md`. PIAST-Q access is not verified.

## Research question
Can QAOA deliver valid and competitive solutions to constrained Earth-observation mission task-selection problems, and how do penalty encoding, circuit depth, sampling noise, and trapped-ion compilation affect performance relative to classical algorithms?

This is a **benchmark and feasibility study**, not a claim of quantum advantage or a production satellite scheduler.

## MVP boundary
- One synthetic mission-planning scenario with six candidate observation tasks.
- Binary task selection, not task timing or satellite assignment.
- Maximize total priority subject to **energy, storage, and downlink** budgets.
- Ground truth: exhaustive search over `2^6 = 64` subsets; sample optimal objective is **27** with tasks **T1,T2,T5,T6** (37 feasible subsets).
- Translate the original constrained model into an auditable QUBO/Ising formulation.
- Compare exact baseline, at least one classical heuristic, and QAOA (ideal then shot-based/noisy simulation).
- Generate reproducible machine-readable results and a concise technical report.

## Explicit non-goals for MVP
No multi-satellite constellation, orbital dynamics, real ephemerides, observation/downlink time windows, learned AI priority scoring, production control loop, real QPU submission, Jetson, Kubernetes, LLM agents, or spacecraft deployment. Those are subsequent research directions, only after acceptance gates.

## Documentation map
1. [`docs/00-vision.md`](docs/00-vision.md) — purpose, research intent and constraints.
2. [`docs/01-requirements.md`](docs/01-requirements.md) — requirements and definitions of done.
3. [`docs/02-mathematical-model.md`](docs/02-mathematical-model.md) — optimization model, QUBO, qubit count, reference answer.
4. [`docs/03-architecture.md`](docs/03-architecture.md) — domain, interfaces, repository design.
5. [`docs/04-experiment-protocol.md`](docs/04-experiment-protocol.md) — reproducible comparisons and metrics.
6. [`docs/05-roadmap.md`](docs/05-roadmap.md) — delivery phases and gates.
7. [`docs/06-sources-and-assumptions.md`](docs/06-sources-and-assumptions.md) — current sources, assumptions and unknowns.
8. [`specs/001-task-selection/`](specs/001-task-selection/) — executable feature specification, delivery plan and granular tasks.
9. [`AGENTS.md`](AGENTS.md) — rules for Codex and other coding agents.
10. [`.cursor/rules/spaceops-quantum.mdc`](.cursor/rules/spaceops-quantum.mdc) — Cursor project rules.
11. [`prompts/initial-agent-prompt.md`](prompts/initial-agent-prompt.md) — ready-to-paste implementation prompt.

## Agent workflow
- Read `AGENTS.md`, the feature spec, the math model, and the task list **before editing code**.
- Implement only the next uncompleted task (tests first, then code, then verification).
- Stop when an acceptance gate fails. Record blockers and decisions in the spec; do not paper over them.
- Never make up numerical results or describe simulations as experiments on actual QPU hardware.

## Classical commands

G1 checks a scenario and solves it with the exhaustive oracle or the greedy baseline. G2 adds the QUBO and Ising summary. G4 writes one archive per run. The summary report comes in a later task.

```bash
uv run spaceops-quantum validate configs/six_tasks.yaml
uv run spaceops-quantum solve --method exact --scenario configs/six_tasks.yaml
uv run spaceops-quantum solve --method greedy --scenario configs/six_tasks.yaml --seed 0
uv run spaceops-quantum qubo inspect --scenario configs/six_tasks.yaml --penalty 41
uv run spaceops-quantum experiment run --method exact --scenario configs/six_tasks.yaml --out results --id exact-f0
```

`validate` checks the scenario schema. `exact` enumerates every subset and prints the feasible optimum. `greedy` ranks tasks by priority divided by the sum of `cost / budget` ratios, breaks ties by higher priority and then by task id, and adds a task only when the remaining budgets still hold it. `--seed` is stored with the greedy result and does not change that ranking. On the six-task fixture the greedy subset matches the optimum; other instances can be worse, and the result stays feasible. `qubo inspect` prints the 18 logical variables, the QUBO constant, and the Ising image under `s = 2v - 1`. The Ising constant is kept, so the two energies match exactly. `--penalty` applies one penalty to every resource. `experiment run` writes `scenario.json`, `manifest.json`, `samples.jsonl`, `metrics.json`, and `summary.csv` under `--out/--id`. The scenario file is the instance that was solved; the manifest stores its hash, seed, and package versions. `--method sampled` records a fixed `(gamma, beta)` and shot frequency. `--method optimized` records a COBYLA trace and a statevector probability; it is not the same result. Classical rows use `p_optimum_definition: not-a-sample`. Generated files in `results/` stay gitignored.

## Planned package
Python 3.11+, `src/spaceops_quantum/`, `pytest`, `ruff`, Qiskit + Qiskit Aer, `numpy`, `scipy`. Resolve dependency versions with a committed lockfile at implementation time; validate current compatibility with the target provider before adding it. Use `uv` for reproducible local workflows.

## Current access context
EuroHPC / PIAST-Q is **emulator-first** for this project. Access to physical QPU, exact quota, provider endpoint, and job submission workflow must be verified independently before any hardware integration. Do not use confidential credentials in commits.
