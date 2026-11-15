"""SpaceOps Quantum task-selection benchmark.

This package must stay importable without Qiskit. The quantum backend layer
is a separate import and is not loaded from this module.
"""

from importlib.metadata import version

__version__ = version("spaceops-quantum")
