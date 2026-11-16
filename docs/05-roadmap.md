# Delivery Roadmap (gated, not time-based)

## Phase S0 — Repository & specification (now)
Deliver docs, agent rules, fixture, task plan. All agents agree on the same scope and vocabulary. **Exit:** spec reviewed, open assumptions marked.

## Phase S1 — Classical foundation (G1)
Build minimal Python package, schema validation, evaluator, exhaustive oracle, greedy. Freeze fixture and tests: objective **27**, subset **T1,T2,T5,T6**, 37 feasible schedules. **Exit:** CLI and pytest green without any Qiskit installation requirement for domain modules.

## Phase S2 — QUBO correctness (G2)
Implement slack bits, coefficient expansion, bit mapping, exact small-instance equivalence, penalty audit, Ising conversion. Record 18-qubit result for F0. **Exit:** no known objective/penalty mismatch; conservative-penalty global optimum matches oracle.

## Phase S3 — Ideal QAOA (G3)
Implement ideal simulator using supported versions; p=1 bounded budget; sampled outcomes, unambiguous mapping, independent decode; seed reproducibility. **Exit:** complete run records without falsely declaring an optimal QAOA result.

## Phase S4 — Benchmark/report (G4)
Add shot-based runs, greedy comparison, penalty and depth study, statistical summaries, provenance manifest, charts and concise technical report. **Exit:** all claims trace to produced data, several independent seeds, no silent infeasible repairs. The p=1 confirmatory report is `docs/07-confirmatory-report.md`. A post-exit aggregate adds the uniform task baseline and the QUBO ground-state probability in `docs/aggregates/t15-v1.json`. Depth p=2, noisy simulation, and hardware compilation remain outside that exit.

## Phase S5 — PIAST-Q emulator preparation (G5, separate approval)
Use approved emulator environment, inspect access and package versions, compile to backend-native instruction set, measure depth/two-qubit operations, assess noise and quota. **Exit:** emulator benchmark and go/no-go document; physical QPU run remains a separately approved experiment.

## Later research (not MVP)
- Actual multi-satellite assignment + time-window scheduling under orbital/contact constraints.
- Larger instances and alternative encodings, including comparison with CP-SAT and classical metaheuristics.
- QAOA feasibility-preserving mixers and warm starts.
- External mission datasets and rigorous domain validation.
- QPU execution and a paper after emulator gate is passed.

## Scope-change rule
Every proposed extension must state: new research question, schema change, additional decision variables/qubits, classical baseline impact, new tests, expected resources, which existing phase it displaces. Without this, defer it.
