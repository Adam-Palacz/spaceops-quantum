"""Problem encoding.

Importing this package must not import Qiskit.
"""

from spaceops_quantum.encoding.bit_mapping import (
    BitLayout,
    BitVariable,
    DecodedSample,
    EncodingError,
    SlackRegister,
    SlackValues,
    allocate_layout,
    decode_sample,
    encode_assignment,
    logical_bits_from_qiskit_bitstring,
    qiskit_bitstring_from_logical_bits,
    slack_bit_count,
)
from spaceops_quantum.encoding.ising import (
    ISING_CONVENTION,
    IsingModel,
    bits_to_spins,
    spins_to_bits,
    to_ising,
)
from spaceops_quantum.encoding.penalty_audit import (
    ConstraintResidual,
    QuboMinimum,
    SampleAssessment,
    assess_sample,
    find_qubo_minima,
)
from spaceops_quantum.encoding.qubo import QUBO_CONVENTION, QuboModel, build_qubo, scenario_hash

__all__ = [
    "BitLayout",
    "BitVariable",
    "DecodedSample",
    "ConstraintResidual",
    "ISING_CONVENTION",
    "IsingModel",
    "EncodingError",
    "QuboMinimum",
    "SampleAssessment",
    "SlackRegister",
    "QUBO_CONVENTION",
    "QuboModel",
    "SlackValues",
    "allocate_layout",
    "assess_sample",
    "bits_to_spins",
    "build_qubo",
    "decode_sample",
    "encode_assignment",
    "find_qubo_minima",
    "logical_bits_from_qiskit_bitstring",
    "qiskit_bitstring_from_logical_bits",
    "scenario_hash",
    "slack_bit_count",
    "spins_to_bits",
    "to_ising",
]
