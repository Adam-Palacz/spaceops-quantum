"""Exact QUBO to Ising conversion.

Bits and spins are tied by ``s_i = 2 v_i - 1``. Spin +1 is bit 1 and spin -1
is bit 0. Variable order is unchanged. The Ising polynomial keeps its own
constant, and ``evaluate`` includes that constant, so the energy equals the
QUBO energy for every corresponding assignment. This module does not import
Qiskit.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from spaceops_quantum.encoding.bit_mapping import EncodingError
from spaceops_quantum.encoding.qubo import QuboModel

ISING_CONVENTION = (
    "s_i = 2 v_i - 1, so spin +1 is bit 1 and spin -1 is bit 0. "
    "E = constant + sum_i linear_i s_i + sum_{i<j} quadratic_ij s_i s_j. "
    "quadratic_ij is the full coefficient of s_i s_j. The constant is retained "
    "and evaluate includes it, matching the QUBO energy exactly."
)


@dataclass(frozen=True, slots=True)
class IsingModel:
    """Ising form of one QUBO, with the constant offset kept."""

    variable_names: tuple[str, ...]
    linear: tuple[tuple[str, Fraction], ...]
    quadratic: tuple[tuple[str, str, Fraction], ...]
    constant: Fraction
    scenario_hash: str
    n_logical_qubits: int
    convention: str = ISING_CONVENTION

    def evaluate(self, spins: Sequence[int]) -> Fraction:
        """Return the Ising energy, including the constant offset."""
        values = _validate_spins(spins, len(self.variable_names))
        index = {name: position for position, name in enumerate(self.variable_names)}
        total = self.constant
        for name, coefficient in self.linear:
            total += coefficient * values[index[name]]
        for left, right, coefficient in self.quadratic:
            total += coefficient * values[index[left]] * values[index[right]]
        return total


def to_ising(qubo: QuboModel) -> IsingModel:
    """Convert a QUBO polynomial to Ising spins without dropping the constant."""
    index = {name: position for position, name in enumerate(qubo.variable_names)}
    linear = {name: Fraction(0) for name in qubo.variable_names}
    quadratic: dict[tuple[str, str], Fraction] = {}
    constant = Fraction(qubo.constant)
    for name, coefficient in qubo.linear:
        coeff = Fraction(coefficient)
        constant += coeff / 2
        linear[name] += coeff / 2
    for left, right, coefficient in qubo.quadratic:
        coeff = Fraction(coefficient)
        constant += coeff / 4
        linear[left] += coeff / 4
        linear[right] += coeff / 4
        if index[left] < index[right]:
            key = (left, right)
        else:
            key = (right, left)
        quadratic[key] = quadratic.get(key, Fraction(0)) + coeff / 4
    ordered_quadratic = tuple(
        (left, right, coefficient)
        for (left, right), coefficient in sorted(
            quadratic.items(),
            key=lambda item: (index[item[0][0]], index[item[0][1]]),
        )
        if coefficient != 0
    )
    return IsingModel(
        variable_names=qubo.variable_names,
        linear=tuple(linear.items()),
        quadratic=ordered_quadratic,
        constant=constant,
        scenario_hash=qubo.scenario_hash,
        n_logical_qubits=qubo.n_logical_qubits,
    )


def bits_to_spins(bits: Sequence[int]) -> tuple[int, ...]:
    """Map logical bits to spins. Bit 1 becomes +1 and bit 0 becomes -1."""
    if isinstance(bits, (str, bytes, bytearray)):
        raise EncodingError(f"bits must be a sequence of 0/1, got {type(bits).__name__}")
    try:
        raw = list(bits)
    except TypeError as exc:
        raise EncodingError(f"bits must be a sequence of 0/1, got {type(bits).__name__}") from exc
    spins: list[int] = []
    for position, value in enumerate(raw):
        if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
            raise EncodingError(f"bits[{position}] must be 0 or 1, got {_got(value)}")
        spins.append(1 if value == 1 else -1)
    return tuple(spins)


def spins_to_bits(spins: Sequence[int]) -> tuple[int, ...]:
    """Map spins back to logical bits."""
    values = _validate_spins(spins, expected=None)
    return tuple((spin + 1) // 2 for spin in values)


def _validate_spins(spins: Sequence[int], expected: int | None) -> tuple[int, ...]:
    if isinstance(spins, (str, bytes, bytearray)):
        raise EncodingError(f"spins must be a sequence of -1/+1, got {type(spins).__name__}")
    try:
        raw = list(spins)
    except TypeError as exc:
        raise EncodingError(
            f"spins must be a sequence of -1/+1, got {type(spins).__name__}"
        ) from exc
    if expected is not None and len(raw) != expected:
        raise EncodingError(f"expected {expected} spins, got {len(raw)}")
    validated: list[int] = []
    for position, value in enumerate(raw):
        if isinstance(value, bool) or not isinstance(value, int) or value not in (-1, 1):
            raise EncodingError(f"spins[{position}] must be -1 or +1, got {_got(value)}")
        validated.append(value)
    return tuple(validated)


def _got(value: object) -> str:
    if isinstance(value, bool):
        return "bool"
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    return type(value).__name__
