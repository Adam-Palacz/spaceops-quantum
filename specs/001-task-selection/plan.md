# Implementation Plan for Feature 001

## Strategy
One vertical capability per gate. Mathematical logic is pure and heavily unit-tested before importing any quantum dependencies. Implement against a frozen fixture rather than beginning with a large configurable framework.

## Phase map

### P0 — Bootstrap
Introduce `pyproject.toml`, Python `src/` package, testing and linting. Resolve `uv.lock` after validating compatibility of current packages. CLI skeleton. No expensive simulation.

### P1 — Domain/oracle
Typed immutable task and scenario models; strict YAML load; `evaluate_solution`; exhaustive search; deterministic greedy; exact CLI. Tests for fixture and failure cases. **Gate G1.**

### P2 — Encoding
Deterministic binary variable map, three slack registers, QUBO builder, QUBO energy function; independent direct-penalty checker. Verify λ=41 correctness and 18 bits. Ising conversion/offset. **Gate G2.**

### P3 — QAOA
Backend-neutral QAOA interface, ideal statevector + finite-shot local Aer; p=1, fixed seed, budgeted optimization; robust bitstring decoding; tests with tiny circuits before 18-qubit F0. **Gate G3.**

### P4 — Experiment and reporting
Reproducibility manifest, samples/metrics serialization, selected seed runs, penalty sensitivity, p=2 optional, plotting/report. **Gate G4.**

### P5 — External emulator preparation, separate change
Inspect PIAST-Q environment and provider; pin compatible versions; compile to native gate target; run only on approved emulator resources; audit remote costs. **Gate G5.**

## Failure / risk strategies
- **QAOA performance:** do not mistake insufficient success probability for a coding error. Verify circuit and objective on tiny instances and compare exact expectations.
- **Slack blowup:** write qubit accounting first; 18 qubits even though there are 6 tasks. If too deep, record as research result; propose a separately reviewed encoding variant, not a hidden change.
- **Wrong endian:** single-/two-bit known states and fixture mapping tests before sampler comparison.
- **Penalty instability:** preserve provably safe λ for correctness and test several smaller penalties in documented ablation.
- **Library API changes:** pin working versions in lockfile; consult current upstream docs, not legacy copied notebooks.
- **Runtime:** bound smoke tests. Extended runs under explicit experiment command, not CI.

## Review checkpoint
At the end of each phase, update `tasks.md` and include test evidence. Start the next phase only after the user explicitly requests continued implementation or approves the gate.
