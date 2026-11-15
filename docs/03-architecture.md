# Architecture and Code Contracts

## Architectural principle
**Domain first, quantum plugin last.** Classical validity must be decided without Qiskit or any backend dependency.

```text
configs/*.yaml
     │
     ▼
Scenario Loader + Schema Validation
     │
     ├──────────────► Classical Exact / Greedy ──────┐
     │                                                │
     ▼                                                ▼
QUBO Builder ──► Ising + Variable Map ──► QAOA Runner │
     │                                    │            │
     │                                    ▼            │
     │                        Backend Adapter (ideal/shot/noisy/AQT later)
     │                                    │            │
     └────────────────────────────────────┴────────────┘
                                          │
                            Independent Evaluator
                                          │
                              Results + Reporting
```

## Proposed repository
```text
spaceops-quantum/
├── README.md
├── AGENTS.md
├── .cursor/rules/spaceops-quantum.mdc
├── pyproject.toml              # implement in task T01
├── uv.lock                     # commit after resolution
├── configs/six_tasks.yaml
├── docs/
│   ├── 00-vision.md
│   ├── 01-requirements.md
│   ├── 02-mathematical-model.md
│   ├── 03-architecture.md
│   ├── 04-experiment-protocol.md
│   ├── 05-roadmap.md
│   └── 06-sources-and-assumptions.md
├── specs/001-task-selection/
│   ├── spec.md
│   ├── plan.md
│   └── tasks.md
├── src/spaceops_quantum/
│   ├── __init__.py
│   ├── domain/{models,validation,evaluation}.py
│   ├── classical/{exact,greedy}.py
│   ├── encoding/{qubo,ising,bit_mapping}.py
│   ├── quantum/{qaoa,backends}.py
│   ├── experiments/{runner,metrics,serialization}.py
│   └── cli.py
├── tests/{unit,integration,fixtures}/
├── results/                   # generated, gitignored except README
└── reports/                   # publication-facing aggregate figures
```

## Data contracts

### `Scenario`
`schema_version: 1`, `scenario_id`, `description`, `budgets` containing `energy/storage/downlink` non-negative integers, `tasks` as a nonempty list of unique IDs with positive integer priority and nonnegative integer resource costs. YAML is source-controlled; validation errors must be actionable. Use normalized units for MVP.

### `SolutionEvaluation`
`selected_task_ids: list[str]`, `priority: int`, `used: {energy,storage,downlink}`, `feasible: bool`, `violations: dict`, `scenario_id`, `bit_vector: list[int]`. One independent implementation used by all solvers.

### `QuboModel`
`variable_names: list[str]`, `linear: dict`, `quadratic: dict`, `constant: float`, `lambda_by_constraint`, `bit_layout`, `n_task_bits`, `n_slack_bits`, `n_logical_qubits`, `scenario_hash`. `evaluate(bits)` must reproduce the mathematical penalty within tolerance. Document Q convention in code and tests.

### `ExperimentRecord` (JSON lines / CSV projection)
`experiment_id`, `timestamp_utc`, `scenario_hash`, `git_sha`, `environment`, `solver`, `backend`, `parameters`, `seed`, `n_evaluations`, `shots`, `best_feasible_solution`, `best_feasible_priority` (nullable), `feasibility_rate`, `optimality_gap` (nullable), `approx_ratio` (nullable), `p_optimum`, `wall_time_sec`, `optimizer_time_sec`, `transpile_time_sec`, `circuit_depth`, `two_qubit_gates`, `error` (nullable). Maintain separate definition of sampled vs estimated `p_optimum`.

## Interfaces
- `load_scenario(path) -> Scenario`
- `evaluate_solution(scenario, selected_bits) -> SolutionEvaluation`
- `solve_exact(scenario) -> ClassicalResult`
- `solve_greedy(scenario, strategy, seed) -> ClassicalResult`
- `build_qubo(scenario, lambda_by_constraint) -> QuboModel`
- `to_ising(qubo) -> IsingModel`
- `run_qaoa(ising, backend, p, shots, seed, optimizer_config) -> QaoaResult`
- `decode_sample(bitstring, bit_layout) -> task_bits + slack_bits`
- `evaluate_run(scenario, result, exact_oracle) -> ExperimentRecord`

Exact signatures can evolve in implementation, but responsibilities and independence must stay.

## Backend separation
1. `IdealBackend` — noiseless statevector Qiskit/Aer for correctness experiments.
2. `SampledBackend` — shot-based Aer, fixed shots.
3. `NoisyBackend` — noise model with explicit provenance and parameters; label as *simulated*, not measured PIAST-Q noise unless calibrated.
4. `AQT/PIASTQBackend` (later) — provider-specific adapter; require remote access confirmation, dry-run, native-gate transpilation metrics and an explicit user-approved execute flag.

Backend integration must not leak authentication details or PIAST-Q-specific code into domain or QUBO modules. Qiskit version and provider compatibility must be locked before adding actual backend implementation.

## Commands (target UX, not yet implemented)
```bash
uv sync
uv run pytest -q
uv run spaceops-quantum validate configs/six_tasks.yaml
uv run spaceops-quantum solve --method exact --scenario configs/six_tasks.yaml
uv run spaceops-quantum qubo inspect --scenario configs/six_tasks.yaml --penalty 41
uv run spaceops-quantum experiment --backend ideal --depth 1 --seed 42 --scenario configs/six_tasks.yaml
uv run spaceops-quantum report --results results/
```

Do not add cloud services, DBs, web frontend or notebooks as the sole execution path. Jupyter notebooks can explain validated library functions but must not duplicate domain logic.
