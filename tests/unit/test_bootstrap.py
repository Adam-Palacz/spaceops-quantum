"""Acceptance checks for the T01 package bootstrap."""

from __future__ import annotations

import shutil
import subprocess
import sys

import pytest

import spaceops_quantum
from spaceops_quantum.cli import main


def test_package_imports_without_qiskit() -> None:
    assert spaceops_quantum.__version__ == "0.1.0"
    assert "qiskit" not in sys.modules
    assert "qiskit_aer" not in sys.modules


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert spaceops_quantum.__version__ in capsys.readouterr().out


def test_cli_without_arguments_prints_usage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([]) == 0
    text = " ".join(capsys.readouterr().out.split())
    assert "spaceops-quantum" in text
    assert "validate" in text
    assert "solve" in text


def test_unknown_argument_is_rejected() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--solve"])
    assert exc_info.value.code == 2


def test_installed_script_reports_version() -> None:
    script = shutil.which("spaceops-quantum")
    assert script is not None
    completed = subprocess.run(
        [script, "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert spaceops_quantum.__version__ in completed.stdout
