# Sources, Assumptions, Open Questions

Updated: 2026-11-12. Sources are reference links, not API contracts to copy blindly.

## Sources (official or primary technical docs)
- EuroHPC JU PIAST-Q system overview: https://www.eurohpc-ju.europa.eu/eurohpc-quantum-computers/our-quantum-computers_en
  - PIAST-Q is trapped-ion, with **20 data qubits** per the current EuroHPC fact sheet, all-to-all connectivity. This does not guarantee a specific circuit can execute.
- PCSS/PIAST-Q: https://quantum.psnc.pl/piast-q/
- EuroHPC Quantum Access Pilot: https://www.eurohpc-ju.europa.eu/eurohpc-ju-opens-access-its-quantum-computers-2026-06-25_en
- Current IBM QAOA tutorial: https://qiskit.qotlabs.org/docs/tutorials/quantum-approximate-optimization-algorithm
- Qiskit Optimization QUBO tutorial: https://qiskit-community.github.io/qiskit-optimization/tutorials/03_minimum_eigen_optimizer.html
- Qiskit AQT provider documentation: https://qiskit-community.github.io/qiskit-aqt-provider/index.html
- AQT gate API: https://arnica.aqt.eu/api/v1/docs

**Compatibility note:** The current AQT provider v2 docs report Python 3.10–3.14 / Qiskit 2.3–2.4.1 support. Verify the versions and access method in the actual PIAST-Q environment before writing the adapter. Native AQT operations include the R, RZ and RXX family, but derive real transpilation targets from the backend rather than hardcoding an assumed universal set.

## Context from earlier project discussions (must be verified in portal)
- Separate project repository: `Adam-Palacz/spaceops-quantum`.
- EuroHPC application history: draft `DRAFT-23586` and later emulator-oriented proposal `EHPC-QCP-2026Q03-091`.
- Previously discussed allocation: emulator-first, up to 10 node-hours, 1 GB and 30 days, then reassessment for physical QPU. **Do not assume quota or remote access based on this document**; confirm approval status and remaining resources in the operator portal.
- Project creator previously obtained PIAST-Q terminal access. This is not proof that API/remote submission is currently provisioned.

## Decision — T10 local simulator versions (2026-11-15)

`uv lock` on this machine resolved the quantum group to **Qiskit 2.4.1** and **Qiskit Aer 0.18.2**. Qiskit 2.4.1 is the top of the AQT provider v2 documented range 2.3–2.4.1. Aer 0.18.2 declares `qiskit>=1.1,<3`. These pins are a local simulator lock only. They do not verify PIAST-Q portal access, the AQT provider package, native gate targets, or quota. Noisy simulation remains a later task.

## Decision — T11 ideal QAOA (2026-11-15)

Ideal QAOA is depth p=1 on the Aer statevector. The classical optimizer is SciPy COBYLA with an explicit evaluation budget. The cost operator uses `s_i = -Z_i`, which matches `s_i = 2 v_i - 1`; products stay `Z_i Z_j`. The Ising constant is added from the original polynomial. Samples are decoded with the original budget evaluator. The checked instance has two tasks and three logical qubits.

## Decision — T12 fixture smoke (2026-11-15)

F0 at λ=41 is one ideal p=1 evaluation with `max_evaluations=1`, seed 0 and parameters `(0.1, 0.2)`. On this machine that evaluation returned all 262144 basis states in about 194 seconds of pytest time. The decoded task patterns are 37 feasible and 27 infeasible. The best feasible priority is 27 because that complete support contains T1, T2, T5, T6; the single evaluation is not an optimized search. A direct run of the same call reported expectation about 8826, which is above the QUBO minimum -27.

## Decision — T13 shot records (2026-11-15)

Finite-shot runs use Aer `seed_simulator`. Each observed bitstring keeps `count` and probability `count / shots`. Logical index 0 is qubit 0, so a Qiskit string is reversed before decoding. Feasibility uses the original budgets. A run whose shots are all infeasible stores `best_feasible_priority` empty, feasibility rate 0, and null approximation ratio and gap; the infeasible priority stays on the sample. `sampled_optimum_probability` is the shot frequency of the exact task selection, separate from the ideal-statevector probability. The checked circuits are the two- and three-qubit instances, not another 18-qubit sweep. JSONL archives remain a later task.

## Decisions
- Build one single-satellite/candidate-task *selection* model first; no temporal slots.
- Preserve the six-task dataset and all three budgets from prior design.
- Treat quota as limited and remote QPU execution as a separately authorized operation.
- Keep future space-ops agent and quantum scheduler repositories independent.
- Use synthetic normalized costs; label unitless resource budget proxy explicitly.

## Open technical questions for later phases
1. Exact available simulator/emulator gateway and whether it is local/offline, Slurm-based or remotely authenticated.
2. Provider support and gate-set introspection on the granted environment; native compilation behavior.
3. Whether a lower-qubit encoding without binary slack can be justified and equivalently validated.
4. Circuit cost of default 18-qubit encoding at p=1 and p=2.
5. Which real mission dataset offers published ground truth and permissive reuse for a later paper.

Agents must document answers through verified environment introspection or source-backed evidence, not assumptions.
