# First Prompt — Cursor or Codex

Paste this into an agent opened **at the root of `spaceops-quantum`** after copying this spec pack into that repository.

---

You are working in the `spaceops-quantum` repository using **specification-driven development**.

Before changing any file, read in this order:
1. `AGENTS.md`
2. `README.md`
3. `specs/001-task-selection/spec.md`
4. `docs/02-mathematical-model.md`
5. `docs/03-architecture.md`
6. `specs/001-task-selection/plan.md`
7. `specs/001-task-selection/tasks.md`

**Implement only task T01 (repository bootstrap).** Do NOT implement task selection, QUBO, QAOA or emulator integration yet.

Acceptance for this first iteration:
- Set up a minimal modern Python 3.11+ package in `src/spaceops_quantum` with `pyproject.toml`, an entry-point CLI stub, pytest, ruff and uv lockfile.
- Keep domain and quantum dependencies separable so basic domain tests need not import Qiskit.
- Preserve all existing documentation and fixture data.
- Ensure a fresh `uv sync`, `uv run pytest -q`, and `uv run ruff check .` pass (if network or tool dependencies are unavailable, report clearly instead of claiming success).
- Update task T01 only after demonstrating the acceptance evidence.
- Summarize exact changed files, executed commands/results, open issues, and the next permitted task T02.

Important scientific constraints that must inform subsequent tasks:
- F0 exact optimum is **27**, not 29; selected tasks T1,T2,T5,T6, costs 9/10/10, feasible 37/64.
- QUBO task selection requires 6 task bits plus 12 slack bits = 18 logical qubits for F0.
- No physical QPU or remote quota-consuming execution, no full constellation scheduling, no agent/Jetson/Kubernetes integration in this feature.

Start with a brief execution plan, then implement T01 and show verification. Do not ask broad discovery questions already answered by the specs.

---

## Prompt after T01

Read `AGENTS.md`, the relevant documents, and the latest `tasks.md`. Implement **T02 only**, including positive/negative schema tests, then run the tests and update the checkbox only if they pass. Do not implement T03 or later tasks. Report evidence and stop.
