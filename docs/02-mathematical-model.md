# Mathematical Model — Version 0.1

## 1. Decision problem: resource-constrained task selection
Let tasks i = 1,…,n have positive utility `p_i` and non-negative integer costs `e_i` (energy), `m_i` (storage), and `d_i` (downlink). Define binary task decisions `x_i`.

Maximize

\[ \max_{x\in\{0,1\}^n} \sum_i p_i x_i \]

subject to

\[ \sum_i e_i x_i \le B_e,\quad \sum_i m_i x_i \le B_m,\quad \sum_i d_i x_i \le B_d. \]

**Scope warning:** This is multi-dimensional 0/1 knapsack / *task selection*, not a calendar- or orbit-aware scheduler. The meaning of storage and downlink is a simple aggregate cost proxy, not state propagation or contact-window allocation.

## 2. Frozen golden dataset

| Task | Priority | Energy | Storage | Downlink |
|---|---:|---:|---:|---:|
| T1 | 10 | 4 | 3 | 5 |
| T2 | 8 | 2 | 4 | 2 |
| T3 | 7 | 5 | 2 | 3 |
| T4 | 6 | 3 | 5 | 4 |
| T5 | 5 | 1 | 2 | 2 |
| T6 | 4 | 2 | 1 | 1 |

`B_e = B_m = B_d = 10` (unitless).

**Verified exact result** (exhaustive 64-subset enumeration): selected **{T1,T2,T5,T6}**, utility **27**, energy **9**, storage **10**, downlink **10**, **37 feasible** subsets. The prior informal claim that the optimum was 29 is incorrect; tests must use 27.

## 3. QUBO with non-negative slack
For each resource r ∈ {e,m,d}, equality is introduced by `a_r · x + s_r = B_r`, where `s_r ≥ 0` is an integer slack. Encode slack in binary:

\[ s_r = \sum_{k=0}^{K_r-1}2^k z_{r,k},\qquad K_r = \lceil\log_2(B_r+1)\rceil. \]

We minimize the penalized unconstrained objective

\[ E(x,z) = -\sum_i p_i x_i + \sum_{r\in\{e,m,d\}} \lambda_r (a_r\cdot x + \sum_k 2^k z_{r,k} - B_r)^2. \]

Because binary variables satisfy `v² = v`, expanding the squares yields a **quadratic** unconstrained binary polynomial. Implement coefficients explicitly and test against the direct expression; do not confuse `xᵀQx` triangular vs symmetric conventions. Retain the constant offset separately.

Note: four binary bits per budget 10 encode slack 0–15, but a **zero-penalty** equality with nonnegative costs necessarily has `s_r = B_r - a_r·x` within 0–10. Excess representable slack does not introduce invalid zero-penalty assignments.

## 4. Logical qubits and hardware feasibility
For B = 10, `ceil(log2(11)) = 4` slack bits per constraint. With n=6 and three budgets: **6 + 3×4 = 18 logical qubits**. With n=8 under the same budgets: **20 logical qubits**. An extra processing budget would require 4 more qubits on these assumptions; it is **not** in MVP.

Logical-qubit count alone does not imply executability on a 20-data-qubit physical device: circuit depth, connectivity, supported gates, timing, provider quotas and noise must be measured.

A large 18-qubit QUBO is already nontrivial for QAOA and can yield deep circuits. This is the central hardware-constrained research issue, not an implementation detail.

## 5. Penalty choice and correctness
If all costs and budgets are integral, any infeasible `x` has a minimum squared budget violation of at least 1 under the nonnegative slack encoding. Since total priority in the fixture is **40**, setting all `λ_r = 41` gives a conservative sufficient safeguard: an infeasible bitstring's E is ≥ `-40 + 41 > 0`, while the empty feasible selection has E = 0. Thus a global minimizer of this penalized QUBO is feasible. The global optimum among feasible bitstrings has utility 27.

This **does not** mean λ=41 is a good QAOA setting; large penalties can make the energy landscape poorly conditioned. Benchmark sensitivity to λ (e.g., 5, 10, 20, 41), but maintain a correctness reference at λ=41. If λ differs per constraint, any violated constraint must still be sufficiently penalized for the same guarantee.

## 6. Encoding/decoding contracts
- Variable order: `[x_T1, …, x_Tn, e_s0…e_sK, m_s0…m_sK, d_s0…d_sK]`.
- Declare bit positions explicitly in serialized output; Qiskit's displayed little-endian bitstrings must not be interpreted by string position without a tested mapping.
- QAOA cost Hamiltonian at p=1: `H = sum_i h_i (-Z_i) + sum_{i<j} J_ij Z_i Z_j`. The sign on `Z_i` matches `s_i = 2 v_i - 1`, because Pauli Z is +1 on bit 0. The Ising constant stays outside the circuit and is added when the expectation is compared with the Ising polynomial.
- QAOA samples `x` **and** `z`; report a candidate as feasible only when the **original `x` budget constraints** pass. Also report QUBO equality/penalty violations separately.
- Feasible candidate quality = original priority, not negative QUBO energy. An infeasible sample has `feasible=false`, not a fabricated approximation ratio.
- Any postprocessing/repair is a distinct experimental arm; never silently repair the primary QAOA result.

## 7. Testing obligations
- Enumerate the 64 primary decisions; assert best 27 and feasible 37.
- Verify all golden selected tasks and each budget.
- For every primary decision in the fixture, compute min slack penalty directly; compare to QUBO calculation for corresponding slack assignment.
- For a smaller 2–3-task scenario, exhaustively enumerate **all task and slack bits** and verify equivalence.
- Include empty, one-task, tie, infeasible, zero-cost and invalid-input cases.
- Verify Ising conversion preserves ordering and energy up to constant offset.
