"""Sampled archive written from a real Aer shot run, outside the parent process."""

from __future__ import annotations

import subprocess
import sys
import textwrap

_SCRIPT = textwrap.dedent(
    r"""
    import json
    from pathlib import Path

    from spaceops_quantum.cli import main

    scenario = Path("sampled-scenario.yaml")
    scenario.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "scenario_id: qaoa-two-tasks",
                "description: two tasks",
                "budgets: {energy: 1, storage: 0, downlink: 0}",
                "tasks:",
                "  - {id: A, priority: 3, energy: 1, storage: 0, downlink: 0}",
                "  - {id: B, priority: 2, energy: 1, storage: 0, downlink: 0}",
            ]
        ),
        encoding="utf-8",
    )
    code = main(
        [
            "experiment", "run", "--method", "sampled",
            "--scenario", str(scenario),
            "--out", "archives",
            "--id", "sampled-pair",
            "--seed", "4",
            "--shots", "32",
            "--penalty", "6",
            "--gamma", "0.2",
            "--beta", "0.3",
        ]
    )
    if code != 0:
        raise SystemExit(code)
    manifest = json.loads(Path("archives/sampled-pair/manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads(Path("archives/sampled-pair/metrics.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in Path("archives/sampled-pair/samples.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert manifest["seed"] == 4
    assert manifest["shots"] == 32
    assert manifest["parameter_source"] == "fixed"
    assert manifest["optimizer_max_evaluations"] is None
    assert manifest["parameters"] == [0.2, 0.3]
    assert manifest["packages"]["qiskit"] == "2.4.1"
    assert manifest["scenario_hash"] == metrics["scenario_hash"]
    assert metrics["p_optimum_definition"] == "shot-frequency"
    assert sum(row["count"] for row in rows) == 32
    assert all(row["probability"] == row["count"] / 32 for row in rows)
    print("ok")
    """
)


def test_sampled_cli_archive_stays_out_of_process(tmp_path) -> None:
    assert "qiskit" not in sys.modules
    completed = subprocess.run(
        [sys.executable, "-c", _SCRIPT],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
        cwd=tmp_path,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert "ok" in completed.stdout
    assert "qiskit" not in sys.modules
