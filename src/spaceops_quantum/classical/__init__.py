"""Classical solvers.

Importing this package must not import Qiskit.
"""

from spaceops_quantum.classical.exact import ClassicalResult, solve_exact
from spaceops_quantum.classical.greedy import GreedySolverError, solve_greedy

__all__ = [
    "ClassicalResult",
    "GreedySolverError",
    "solve_exact",
    "solve_greedy",
]
