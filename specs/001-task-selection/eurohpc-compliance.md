# EuroHPC compliance — Feature 001 against the technical assessment

Reviewed 2026-11-22. This note does not change the T01–T16 solvers or the local 256/1024-shot grid. That grid remains a separate Aer benchmark. It is not EuroHPC evidence.

PCSS Support stated that allocation `EHPC-QCP-2026Q03-091` allows emulator benchmarks without an API token through the Qiskit AQT provider. The measured emulator path is `AQTProvider().offline.ideal()` and `AQTProvider().offline.noisy()`. No remote QPU job is authorized by this review.

## Decision variables and logical qubits

A decision variable is one task bit. A slack qubit is a bit of a binary slack register. Logical qubits are the sum. The offline backend register has 20 qubits. The compiled circuit uses only the logical width of the instance.

| Instance | Decision variables | Slack qubits | Logical qubits | Fits 6–12 logical | Fits 6–12 decisions |
|---|---|---|---|---|---|
| F1 | 3 | 3 | 6 | yes | no, 3 task bits |
| F2 | 6 | 3 | 9 | yes | yes, at the floor |
| F3 | 6 | 6 | 12 | yes | yes, at the floor |
| F0, not in the emulator plan | 6 | 12 | 18 | no, 18 is outside 6–12 and inside the optional 20 | yes, 6 task bits |

Slack bits are not extra scheduling choices. They encode the unused budget so the QUBO penalty can be written with binary variables.

## Requirement matrix

| Requirement | Current state |
|---|---|
| 6–12 optimization variables, optionally 20 | Met for logical qubits on F1–F3. Met for decision variables on F2 and F3 only. F1 has 3 task choices and is diagnostic, not evidence for this minimum. |
| Classical exact optimum and greedy baseline | Implemented and tested. F1 greedy scores 3 against exact 5. F2 and F3 greedy match the exact priority. |
| End-to-end QAOA on AQT ideal and noisy simulators | Done on CPU, not on a QPU. Job 2089 ran F2 and F3, seeds 0, 1, and 2: exact Aer search, then 200 shots on `offline.ideal()` and 200 shots on `offline.noisy()`. Exit 0 in 51 seconds. This shows AQT-compatible execution. It does not show a quantum advantage. The local 256/1024 Aer grid remains a separate benchmark. |
| Native gates RZ, R(θ, φ), RXX | The offline target reports `rz`, `r`, `rxx`, and `measure`. Compiled F1–F3 circuits use `r` and `rxx`. Standalone `rz` count is 0 at the audited parameters because `r` carries the Z rotation. |
| Terminal full-register measurement only | The audited circuits measure every logical qubit once, after the unitary. One `barrier` from `measure_all()` is present and is not a hardware gate. |
| At most 200 shots per circuit and about 50 circuits per job | The local grid used 256 and 1024 shots. Those runs are not compliant evidence. Job 2089 used 200 shots on each offline simulator. One Slurm job held six compiled circuits. A provider-enforced shot ceiling was not read. |
| Compiled RXX count and depth | `t18-aqt-audit.json` records (γ, β) = (0.1, 0.2). Job 2089 recompiled the optimized parameters: F2 is 17 RXX and depth 29–30, F3 is 42 RXX and depth 47–48. |
| Hardware campaign below about 400 native two-qubit gates | F1 has 10 RXX, F2 has 17, F3 has 42. All three are inside that budget at the audited parameters. |
| Circuits × shots × jobs for 10 QPU hours at 25–100 ms per shot | Not spent. Six compiled circuits at 200 shots would be 30 s at 25 ms per shot and 120 s at 100 ms. Job 2089's 51 seconds are HPC CPU time, not QPU time. |

## Scheduling scope

Feature 001 selects a subset of tasks under three aggregate budgets. It does not assign contact windows, downlink time, or multiple satellites. That temporal problem is Feature 002 and stays outside this benchmark. The assessment's scheduling language is therefore only partly covered: the model answers which tasks fit the budgets, and it does not answer when they are transmitted.

Clarification to send to PCSS, one question:

> Does the technical assessment accept a single-satellite task-selection model under three aggregate resource budgets, or does a valid scheduling result also require contact windows and transmission times?

## Unresolved mismatches

- F1 has 3 decision variables and is diagnostic only. Stretching it to 6 task bits would be a new instance, not a relabeling of slack.
- No time index is in the model. Adding one is a Feature 002 change and needs its own approval.
- The fixed-parameter RXX counts remain in the T18 audit. The optimized circuits were recompiled in job 2089; F2 depth varies by one across seeds. Those counts are offline-target counts, not a hardware-backend measurement.
- The local 256/1024 grid is not EuroHPC shot-budget evidence.
- Remaining portal hours were not read. The 10-hour figure is the proposed budget, not a measured balance.
- Depth p=2, noise calibration against the device, and a QPU submission are not part of this review.
