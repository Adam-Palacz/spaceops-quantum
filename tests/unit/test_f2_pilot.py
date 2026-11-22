"""The F2 pilot refuses a remote backend and does not import Qiskit on import."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from spaceops_quantum.experiment.f2_pilot import (
    PilotError,
    assert_noisy_offline,
    prepare_output,
)

_ROOT = Path(__file__).resolve().parents[2]
_SOURCE = _ROOT / "src" / "spaceops_quantum" / "experiment" / "f2_pilot.py"


def test_import_does_not_load_qiskit() -> None:
    assert "qiskit" not in sys.modules
    text = _SOURCE.read_text(encoding="utf-8")
    assert "direct_access" not in text
    assert ".cloud(" not in text
    assert "import openqapi" not in text.lower()
    assert "offline.noisy" in text
    assert "backend.target" in text


def test_only_the_offline_noisy_id_is_accepted() -> None:
    assert_noisy_offline("offline_simulator_noise")
    with pytest.raises(PilotError, match="refusing"):
        assert_noisy_offline("aqt_qpu")


def test_populated_output_is_refused(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(PilotError, match="not empty"):
        prepare_output(tmp_path)
    assert (tmp_path / "keep.txt").read_text(encoding="utf-8") == "keep"
