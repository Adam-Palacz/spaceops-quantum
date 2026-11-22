# T17 — read-only PIAST-Q access check

Status: measurements through job 2064 are in `t17-environment-note.md`. A private environment has `qiskit` 2.4.1 and `qiskit-aqt-provider` 2.0.1. On partition `all`, both AQT offline simulators completed a 100-shot Bell circuit. Slurm still reports no ORCA licenses. No remote QPU was contacted. The offline target gate set and the F1–F3 compiled RXX counts are in `t18-aqt-audit.json`. The T19 matrix is written and has not been run. A portal balance for the proposed 10 hours was not read.

## Question

Can the approved account see a PIAST-Q emulator backend, and what limits and native gates does that backend report? The answer has to come from the environment, not from the local Aer simulator and not from an unverified quota claim.

## Allowed actions

1. Confirm that a provider package is installed. Record its version. If it is absent, stop and record "not installed".
2. Compare that version with the local pins: `qiskit==2.4.1` and `qiskit-aer==0.18.2`.
3. If an operator session already exists, list backend names and read published properties: qubit count, native gate set, maximum shots, and any stated job or circuit limit.
4. Write those facts into an environment note. Omit tokens, passwords, private endpoints, and account identifiers.

## Forbidden in T17

- Submitting a sampler job, an estimator job, or any circuit, including a one-shot smoke circuit.
- Calling a physical QPU.
- Copying credentials into the repository, the terminal transcript, or the environment note.
- Treating the local Aer shot counts 256 and 1024 as the emulator limit. Decision 001 keeps that limit unverified until this check.
- Starting T18 compilation, T19 emulator experiments, or Feature 002.

## Evidence to bring back

- Provider package version, or an explicit statement that it is not installed.
- Backend name and whether it is an emulator.
- Native gates actually reported by that backend. The expected AQT names R, RZ, and RXX are a hypothesis until the backend lists them.
- Reported shot limit, job or circuit limit, and qubit count.
- A statement that no job was submitted.

## Stop

T17 ends when the environment note exists, or when access cannot be confirmed. T18, the hardware-aware depth and two-qubit-gate audit of F1–F3, requires a separate approval after that note. T18 still does not submit an emulator job unless a later approval says so.
