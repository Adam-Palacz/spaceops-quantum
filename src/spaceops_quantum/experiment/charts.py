"""Deterministic SVG charts for the sanitized T15 aggregate."""

from __future__ import annotations

from pathlib import Path


def write_charts(aggregate: dict[str, object], destination: Path) -> None:
    """Write the two comparison charts next to the aggregate."""

    summary = aggregate["summary"]
    if not isinstance(summary, dict):
        raise ValueError("aggregate summary is missing")
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "t15-ratio.svg").write_text(
        _ratio_chart(summary["ideal_penalty"]),
        encoding="utf-8",
    )
    (destination / "t15-ground-vs-optimum.svg").write_text(
        _ground_chart(summary["ideal_penalty"]),
        encoding="utf-8",
    )


def _ratio_chart(groups: object) -> str:
    rows = _rows(groups)
    scenarios = ("f1-three-tasks-v1", "f2-six-tasks-v1", "f3-six-tasks-v1")
    colors = {
        "f1-three-tasks-v1": "#1b4f72",
        "f2-six-tasks-v1": "#b9770e",
        "f3-six-tasks-v1": "#196f3d",
    }
    penalties = (5, 10, 20, 41)
    width, height = 680, 380
    left, right, top, bottom = 70, 40, 40, 70
    plot_width = width - left - right
    plot_height = height - top - bottom
    ceiling = 4.0
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        'viewBox="0 0 680 380">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="70" y="24" font-family="sans-serif" font-size="16">'
        "Median p_optimum / p_uniform, ideal QAOA p=1</text>",
    ]
    for mark in (0, 1, 2, 3, 4):
        y = top + plot_height - (mark / ceiling) * plot_height
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" '
            'stroke="#dddddd"/>'
        )
        parts.append(
            f'<text x="8" y="{y + 4:.1f}" font-family="sans-serif" font-size="12">{mark}</text>'
        )
    unity = top + plot_height - (1 / ceiling) * plot_height
    parts.append(
        f'<line x1="{left}" y1="{unity:.1f}" x2="{left + plot_width}" y2="{unity:.1f}" '
        'stroke="#922b21" stroke-dasharray="5 4"/>'
    )
    parts.append(
        f'<text x="{left + 8}" y="{unity - 6:.1f}" font-family="sans-serif" '
        'font-size="12" fill="#922b21">uniform task draw</text>'
    )
    for index, penalty in enumerate(penalties):
        x = left + (index + 0.5) * (plot_width / len(penalties))
        parts.append(
            f'<text x="{x - 8:.1f}" y="{height - 28}" font-family="sans-serif" '
            f'font-size="12">{penalty}</text>'
        )
    for scenario in scenarios:
        points: list[str] = []
        for index, penalty in enumerate(penalties):
            value = _median(rows, scenario, penalty, "p_optimum_over_uniform_median")
            x = left + (index + 0.5) * (plot_width / len(penalties))
            y = top + plot_height - (min(value, ceiling) / ceiling) * plot_height
            points.append(f"{x:.1f},{y:.1f}")
        parts.append(
            f'<polyline fill="none" stroke="{colors[scenario]}" stroke-width="2" '
            f'points="{" ".join(points)}"/>'
        )
    parts.append(
        '<text x="250" y="364" font-family="sans-serif" font-size="12">penalty λ</text>'
    )
    parts.append("</svg>\n")
    return "\n".join(parts)


def _ground_chart(groups: object) -> str:
    rows = [row for row in _rows(groups) if row["key"] == 41]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="680" height="360" '
        'viewBox="0 0 680 360">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="40" y="24" font-family="sans-serif" font-size="16">'
        "λ=41 median: task optimum versus QUBO ground state</text>",
    ]
    labels = ("f1-three-tasks-v1", "f2-six-tasks-v1", "f3-six-tasks-v1")
    maximum = max(float(row["p_optimum_median"]) for row in rows) if rows else 1
    maximum = max(maximum, 0.05)
    for index, scenario in enumerate(labels):
        row = next(item for item in rows if item["scenario_id"] == scenario)
        x = 80 + index * 190
        optimum_height = 240 * float(row["p_optimum_median"]) / maximum
        ground_height = 240 * float(row["p_ground_state_median"]) / maximum
        parts.append(
            f'<rect x="{x}" y="{300 - optimum_height:.1f}" width="40" '
            f'height="{optimum_height:.1f}" fill="#1b4f72"/>'
        )
        parts.append(
            f'<rect x="{x + 50}" y="{300 - ground_height:.1f}" width="40" '
            f'height="{ground_height:.1f}" fill="#b9770e"/>'
        )
        short = scenario.split("-")[0].upper()
        parts.append(
            f'<text x="{x}" y="324" font-family="sans-serif" font-size="12">{short}</text>'
        )
    parts.append(
        '<rect x="80" y="340" width="12" height="12" fill="#1b4f72"/>'
        '<text x="98" y="351" font-family="sans-serif" font-size="12">p_optimum</text>'
        '<rect x="220" y="340" width="12" height="12" fill="#b9770e"/>'
        '<text x="238" y="351" font-family="sans-serif" font-size="12">p_ground_state</text>'
    )
    parts.append("</svg>\n")
    return "\n".join(parts)


def _rows(groups: object) -> list[dict[str, object]]:
    if not isinstance(groups, list):
        raise ValueError("chart groups must be a list")
    return [row for row in groups if isinstance(row, dict)]


def _median(rows: list[dict[str, object]], scenario: str, penalty: int, field: str) -> float:
    for row in rows:
        if row["scenario_id"] == scenario and row["key"] == penalty:
            return float(row[field])
    raise ValueError(f"missing {scenario} λ={penalty}")
