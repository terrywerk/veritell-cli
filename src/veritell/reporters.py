"""Render Veritell suite results for terminal and machine-readable output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AssertionResult, VeritellSuiteResult, VeritellTestResult


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
    reliability = "n/a" if summary.score is None else f"{summary.score * 100:.2f}%"
    lines.append(
        "Summary: "
        f"total={summary.total} passed={summary.passed} failed={summary.failed} "
        f"errors={summary.errors} skipped={summary.skipped} reliability={reliability} score={score}"
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
    active_results = [assertion for assertion in result.assertion_results if assertion.status != "skip"]
    passed_results = [assertion for assertion in active_results if assertion.status == "pass"]
    methods = ",".join(sorted({assertion.method for assertion in result.assertion_results})) or "n/a"
    lines = [
        f"{result.status.upper()} {result.test_id} score={score} assertions={len(passed_results)}/{len(active_results)} methods={methods}"
    ]

    fallback_notes = [
        f"{assertion.assertion} fell back to heuristic: {assertion.details['fallback_reason']}"
        for assertion in result.assertion_results
        if isinstance(assertion.details.get("fallback_reason"), str) and assertion.details["fallback_reason"].strip()
    ]
    for note in fallback_notes:
        lines.append(f"  note: {_trim_text(note)}")

    failures = [assertion for assertion in result.assertion_results if assertion.status in {"fail", "error"}]
    if failures:
        lines.append("  failed assertions:")
        for assertion in failures:
            lines.extend(_render_failed_assertion(assertion))

    return lines


def _render_failed_assertion(assertion: AssertionResult) -> list[str]:
    confidence = "n/a" if assertion.confidence is None else f"{assertion.confidence:.3f}"
    lines = [f"    - {assertion.assertion} [{assertion.status}] method={assertion.method} confidence={confidence}"]
    details = assertion.details

    unsupported_analyses = details.get("unsupported_span_analyses")
    if isinstance(unsupported_analyses, list) and unsupported_analyses:
        lines.append("      unsupported spans:")
        for analysis in unsupported_analyses[:3]:
            if not isinstance(analysis, dict):
                continue
            span = analysis.get("span")
            rationale = analysis.get("rationale")
            if isinstance(span, str) and span.strip():
                lines.append(f"        - {_quote(span)}")
            if isinstance(rationale, str) and rationale.strip():
                lines.append(f"          rationale: {_trim_text(rationale, max_length=180)}")
        remaining = sum(1 for item in unsupported_analyses if isinstance(item, dict)) - 3
        if remaining > 0:
            lines.append(f"        ... +{remaining} more unsupported span(s)")
    elif isinstance(details.get("unsupported_spans"), list) and details["unsupported_spans"]:
        spans = [item for item in details["unsupported_spans"] if isinstance(item, str) and item.strip()]
        if spans:
            lines.append(f"      unsupported spans: {', '.join(_quote(span) for span in spans[:5])}")
            if len(spans) > 5:
                lines.append(f"      ... +{len(spans) - 5} more unsupported span(s)")

    if isinstance(details.get("reason"), str) and details["reason"].strip():
        lines.append(f"      reason: {_trim_text(details['reason'], max_length=180)}")
    if "expected" in details:
        lines.append(f"      expected: {_trim_text(_stringify(details['expected']), max_length=160)}")
    if "actual" in details:
        lines.append(f"      actual: {_trim_text(_stringify(details['actual']), max_length=160)}")
    if isinstance(details.get("missing_docs"), list) and details["missing_docs"]:
        missing_docs = ", ".join(_trim_text(_stringify(item), max_length=80) for item in details["missing_docs"])
        lines.append(f"      missing_docs: {missing_docs}")
    return lines


def _trim_text(value: str, *, max_length: int = 140) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True)


def _quote(value: str) -> str:
    return f'"{value}"'
