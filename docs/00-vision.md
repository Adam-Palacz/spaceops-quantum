# Vision & Research Charter

## Mission
Develop a reproducible, scientifically honest benchmark for hybrid quantum–classical optimization of civilian Earth-observation satellite mission tasks, with an eventual emulator-to-PIAST-Q experiment path.

## Hypothesis
**H1:** A small constrained task-selection problem can be correctly encoded as QUBO and solved with QAOA, returning valid decoded task subsets.

**H2:** Penalty scaling and native-gate compilation significantly change the feasible-sample rate and practical resource cost of QAOA.

**H3 (exploratory):** Some instances might yield competitive solution quality under controlled evaluation budgets; no superiority over classical baselines is assumed.

The experiment is useful even if QAOA loses: documenting how and why (penalty costs, depth, noise, optimization overhead) is a valid technical result.

## Technical contribution to aim for
1. A transparent mission-task selection formulation with verified ground truth.
2. A correct QUBO with explicit slack-variable/qubit accounting.
3. A fair experimental harness comparing several solvers on identical inputs.
4. Backend-aware analysis of circuit depth / two-qubit gates / sampling and noise.
5. A report that separates ideal simulation, noisy emulation, and real QPU results.

## Scope discipline
This is one independent `spaceops-quantum` repository. Do **not** merge it with `spaceops_mission_agent_lab` or add LangGraph, MCP, LLMs, Jetson, GPUs, K8s, or a 100-satellite scheduler to MVP.

A later project phase can formalize multi-satellite assignment and scheduling; those are different mathematical problems, not minor extra fields.

## Intended audience
Researchers and engineers working on space operations, quantum optimization, HPC, and hybrid workflows, including potential EuroHPC/PIAST-Q collaborators. Documentation, experiment outputs and code comments should be written in English for external reuse.

## Success is defined by evidence
- Correct objective/feasibility calculations verified against exhaustive enumeration.
- Same decoded solutions checked independently of the solver/QUBO objective.
- Experiment parameters, seeds, run budget and system/software versions recorded.
- Explicit negative findings, not selective reporting.
- Reproducible chart/table for a draft technical article.

## Future directions (not authorized for MVP)
- Multiple satellites, revisit priorities, orbital observation windows and downlink contacts.
- Assignment/time-indexed scheduling with richer collision and resource constraints.
- Domain-realistic data from publicly licensed Earth-observation scenarios.
- Classical OR-Tools/MILP/CP-SAT, warm-start or constraint-preserving quantum variants.
- Hardware execution on PIAST-Q after approved allocation and emulator acceptance.
- Integration with the separate `spaceops_mission_agent_lab` at an interface level.
