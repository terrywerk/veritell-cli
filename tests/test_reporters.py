"""Tests for terminal and JSON reporters."""

from __future__ import annotations

import json
from pathlib import Path

from veritell.models import AssertionResult, VeritellRunSummary, VeritellSuiteResult, VeritellTestResult
from veritell.reporters import render_json_report, render_terminal_report


def _sample_suite() -> VeritellSuiteResult:
    return VeritellSuiteResult(
        results=[
            VeritellTestResult(
                test_id="sample_test",
                status="pass",
                score=1.0,
                assertion_results=[
                    AssertionResult(
                        assertion="exact_match",
                        status="pass",
                        method="deterministic",
                        confidence=1.0,
                        details={"expected": "ok", "actual": "ok"},
                    )
                ],
                diagnosis=None,
            )
        ],
        summary=VeritellRunSummary(total=1, passed=1, failed=0, errors=0, skipped=0, score=1.0),
    )



def test_render_terminal_report_includes_per_test_assertions_and_summary() -> None:
    report = render_terminal_report(Path("tests/ai"), _sample_suite())

    assert "Suite: tests/ai" in report
    assert "Test sample_test: status=pass score=1.00" in report
    assert "- exact_match: status=pass method=deterministic confidence=1.000" in report
    assert "Summary: total=1 passed=1 failed=0 errors=0 skipped=0 score=1.00" in report



def test_render_json_report_includes_results_and_summary() -> None:
    payload = json.loads(render_json_report(Path("tests/ai"), _sample_suite()))

    assert payload["path"] == "tests/ai"
    assert payload["summary"]["passed"] == 1
    assert payload["results"][0]["test_id"] == "sample_test"
    assert payload["results"][0]["assertion_results"][0]["assertion"] == "exact_match"


def test_render_terminal_report_includes_gate_metadata_when_present() -> None:
    report = render_terminal_report(Path("tests/ai"), _sample_suite(), gate={"threshold": 80.0, "score": 100.0, "passed": True})

    assert "Gate: threshold=80.00 score=100.00 passed=true" in report



def test_render_json_report_includes_gate_metadata_when_present() -> None:
    payload = json.loads(
        render_json_report(Path("tests/ai"), _sample_suite(), gate={"threshold": 80.0, "score": 100.0, "passed": True})
    )

    assert payload["gate"]["threshold"] == 80.0
    assert payload["gate"]["score"] == 100.0
    assert payload["gate"]["passed"] is True
