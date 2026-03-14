"""Render Veritell suite results for terminal and machine-readable output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import VeritellSuiteResult, VeritellTestResult


def render_terminal_report(
    path: str | Path, suite: VeritellSuiteResult, gate: dict[str, Any] | None = None
) -> str:
    """Render a human-readable suite report with per-test assertion details and summary."""

    path_text = Path(path).as_posix()
    lines = [f"Suite: {path_text}"]

    for result in suite.results:
        lines.extend(_render_test_result(result))

    summary = suite.summary
    score = f"{summary.score:.2f}" if summary.score is not None else "n/a"
    lines.append(
        "Summary: "
        f"total={summary.total} passed={summary.passed} failed={summary.failed} "
        f"errors={summary.errors} skipped={summary.skipped} score={score}"
    )
    if gate is not None:
        lines.append(
            f"Gate: threshold={gate['threshold']:.2f} score={gate['score']:.2f} passed={str(gate['passed']).lower()}"
        )
    return "\n".join(lines)


def render_json_report(
    path: str | Path, suite: VeritellSuiteResult, gate: dict[str, Any] | None = None
) -> str:
    """Render a machine-readable JSON report containing per-test results and suite summary."""

    payload = {
        "path": Path(path).as_posix(),
        "summary": suite.summary.to_dict(),
        "results": [result.to_dict() for result in suite.results],
    }
    if gate is not None:
        payload["gate"] = gate
    return json.dumps(payload, indent=2, sort_keys=True)


def _render_test_result(result: VeritellTestResult) -> list[str]:
    score = f"{result.score:.2f}" if result.score is not None else "n/a"
    lines = [f"Test {result.test_id}: status={result.status} score={score}"]
    for assertion in result.assertion_results:
        confidence = "n/a" if assertion.confidence is None else f"{assertion.confidence:.3f}"
        lines.append(
            f"  - {assertion.assertion}: status={assertion.status} method={assertion.method} confidence={confidence}"
        )
    if result.diagnosis:
        lines.append(f"  diagnosis: {json.dumps(result.diagnosis, sort_keys=True)}")
    return lines

