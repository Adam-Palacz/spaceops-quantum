"""Logical bit layout for task variables and binary slack registers.

Variable order is ``[x_T1, …, x_Tn, e_s0…, m_s0…, d_s0…]``. Index 0 is the
first task. A Qiskit measurement string keeps qubit 0 on the right, so it is
converted by ``logical_bits_from_qiskit_bitstring`` before decoding. This
module does not build a QUBO and does not import Qiskit.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from spaceops_quantum.domain.models import Scenario

_RESOURCES = (
    ("energy", "e"),
    ("storage", "m"),
    ("downlink", "d"),
)


class EncodingError(ValueError):
    """A bit layout or bit vector does not match the encoding contract."""


@dataclass(frozen=True, slots=True)
class BitVariable:
    """One logical binary variable."""

    index: int
    name: str
    kind: str
    task_id: str | None = None
    resource: str | None = None
    weight: int | None = None


@dataclass(frozen=True, slots=True)
class SlackRegister:
    """Binary slack for one budget. Bit k has weight ``2**k``."""

    resource: str
    prefix: str
    budget: int
    n_bits: int
    start_index: int
    names: tuple[str, ...]
    weights: tuple[int, ...]

    @property
    def max_value(self) -> int:
        if self.n_bits == 0:
            return 0
        return (1 << self.n_bits) - 1


@dataclass(frozen=True, slots=True)
class SlackValues:
    """Integer slack for energy, storage and downlink."""

    energy: int
    storage: int
    downlink: int


@dataclass(frozen=True, slots=True)
class DecodedSlackBits:
    """Slack bits in register order, least significant bit first."""

    energy: tuple[int, ...]
    storage: tuple[int, ...]
    downlink: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DecodedSample:
    """Task bits and slack recovered from one logical bit vector."""

    task_bits: tuple[int, ...]
    slack_bits: DecodedSlackBits
    slack_values: SlackValues


@dataclass(frozen=True, slots=True)
class BitLayout:
    """Stable logical-variable map for one scenario."""

    scenario_id: str
    variables: tuple[BitVariable, ...]
    registers: tuple[SlackRegister, ...]
    task_ids: tuple[str, ...]
    n_task_bits: int
    n_slack_bits: int
    n_logical_qubits: int

    @property
    def variable_names(self) -> tuple[str, ...]:
        return tuple(variable.name for variable in self.variables)


def slack_bit_count(budget: int) -> int:
    """Return ``ceil(log2(budget + 1))`` for a non-negative integer budget."""
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        raise EncodingError(f"budget must be an integer >= 0, got {budget!r}")
    span = budget + 1
    bits = 0
    power = 1
    while power < span:
        power *= 2
        bits += 1
    return bits


def allocate_layout(scenario: Scenario) -> BitLayout:
    """Allocate task bits and one slack register per budget."""
    task_ids = tuple(task.id for task in scenario.tasks)
    if len(task_ids) != len(set(task_ids)):
        raise EncodingError("task ids must be unique")
    variables = [
        BitVariable(index=index, name=f"x_{task_id}", kind="task", task_id=task_id)
        for index, task_id in enumerate(task_ids)
    ]
    registers: list[SlackRegister] = []
    cursor = len(task_ids)
    for resource, prefix in _RESOURCES:
        budget = getattr(scenario.budgets, resource)
        n_bits = slack_bit_count(budget)
        names = tuple(f"{prefix}_s{power}" for power in range(n_bits))
        weights = tuple(1 << power for power in range(n_bits))
        for offset, (name, weight) in enumerate(zip(names, weights, strict=True)):
            variables.append(
                BitVariable(
                    index=cursor + offset,
                    name=name,
                    kind="slack",
                    resource=resource,
                    weight=weight,
                )
            )
        registers.append(
            SlackRegister(
                resource=resource,
                prefix=prefix,
                budget=budget,
                n_bits=n_bits,
                start_index=cursor,
                names=names,
                weights=weights,
            )
        )
        cursor += n_bits
    n_task_bits = len(task_ids)
    n_slack_bits = cursor - n_task_bits
    return BitLayout(
        scenario_id=scenario.scenario_id,
        variables=tuple(variables),
        registers=tuple(registers),
        task_ids=task_ids,
        n_task_bits=n_task_bits,
        n_slack_bits=n_slack_bits,
        n_logical_qubits=cursor,
    )


def encode_assignment(
    layout: BitLayout,
    task_bits: Sequence[int],
    slack: SlackValues,
) -> tuple[int, ...]:
    """Pack task bits and integer slack into logical order."""
    tasks = _validate_logical_bits(task_bits, layout.n_task_bits, what="task bits")
    encoded = [0] * layout.n_logical_qubits
    for index, bit in enumerate(tasks):
        encoded[index] = bit
    for register, value in zip(layout.registers, _slack_triple(slack), strict=True):
        _write_slack(encoded, register, value)
    return tuple(encoded)


def decode_sample(bitstring: Sequence[int], layout: BitLayout) -> DecodedSample:
    """Split a logical bit vector into task bits and slack.

    ``bitstring`` is indexed like ``layout.variables``. A Qiskit display
    string is not accepted here.
    """
    if isinstance(bitstring, str):
        raise EncodingError(
            "decode_sample expects logical 0/1 bits; convert a Qiskit string with "
            "logical_bits_from_qiskit_bitstring first"
        )
    bits = _validate_logical_bits(
        bitstring,
        layout.n_logical_qubits,
        what="logical bits",
    )
    task_bits = bits[: layout.n_task_bits]
    slack_groups: list[tuple[int, ...]] = []
    slack_numbers: list[int] = []
    for register in layout.registers:
        group = bits[register.start_index : register.start_index + register.n_bits]
        slack_groups.append(group)
        slack_numbers.append(
            sum(bit * weight for bit, weight in zip(group, register.weights, strict=True))
        )
    return DecodedSample(
        task_bits=task_bits,
        slack_bits=DecodedSlackBits(
            energy=slack_groups[0],
            storage=slack_groups[1],
            downlink=slack_groups[2],
        ),
        slack_values=SlackValues(
            energy=slack_numbers[0],
            storage=slack_numbers[1],
            downlink=slack_numbers[2],
        ),
    )


def logical_bits_from_qiskit_bitstring(text: str) -> tuple[int, ...]:
    """Map a Qiskit bitstring to logical order.

    Qiskit prints qubit 0 as the rightmost character. Logical index 0 stays
    the first task variable.
    """
    if not isinstance(text, str) or any(character not in "01" for character in text):
        raise EncodingError("Qiskit bitstring must contain only characters 0 and 1")
    return tuple(int(character) for character in reversed(text))


def qiskit_bitstring_from_logical_bits(bits: Sequence[int]) -> str:
    """Render logical bits as a Qiskit display string, qubit 0 on the right."""
    if isinstance(bits, str):
        raise EncodingError("logical bits must be a sequence of 0/1, not str")
    validated = _validate_logical_bits(bits, expected=None, what="logical bits")
    return "".join(str(bit) for bit in reversed(validated))


def _slack_triple(slack: SlackValues) -> tuple[int, int, int]:
    if not isinstance(slack, SlackValues):
        raise EncodingError(f"slack must be SlackValues, got {type(slack).__name__}")
    return (slack.energy, slack.storage, slack.downlink)


def _write_slack(encoded: list[int], register: SlackRegister, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EncodingError(
            f"{register.resource} slack must be an integer >= 0, got {value!r}"
        )
    if value > register.max_value:
        raise EncodingError(
            f"{register.resource} slack {value} does not fit in {register.n_bits} bits "
            f"(maximum {register.max_value})"
        )
    for offset in range(register.n_bits):
        encoded[register.start_index + offset] = (value >> offset) & 1


def _validate_logical_bits(
    bits: Sequence[int],
    expected: int | None,
    *,
    what: str,
) -> tuple[int, ...]:
    if isinstance(bits, (str, bytes, bytearray)):
        raise EncodingError(f"{what} must be a sequence of 0/1, got {type(bits).__name__}")
    try:
        raw = list(bits)
    except TypeError as exc:
        raise EncodingError(
            f"{what} must be a sequence of 0/1, got {type(bits).__name__}"
        ) from exc
    if expected is not None and len(raw) != expected:
        raise EncodingError(f"expected {expected} {what}, got {len(raw)}")
    validated: list[int] = []
    for index, value in enumerate(raw):
        if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
            raise EncodingError(f"{what}[{index}] must be 0 or 1, got {_got(value)}")
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
