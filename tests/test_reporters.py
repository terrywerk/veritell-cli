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



def test_render_terminal_report_includes_per_test_summary_and_reliability() -> None:
    report = render_terminal_report(Path("tests/ai"), _sample_suite())

    assert "Suite: tests/ai" in report
    assert "PASS sample_test score=1.00 assertions=1/1 methods=deterministic" in report
    assert "Summary: total=1 passed=1 failed=0 errors=0 skipped=0 reliability=100.00% score=1.00" in report



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



def test_render_terminal_report_includes_fallback_note_when_present() -> None:
    suite = VeritellSuiteResult(
        results=[
            VeritellTestResult(
                test_id="sample_test",
                status="pass",
                score=1.0,
                assertion_results=[
                    AssertionResult(
                        assertion="no_unsupported_claims",
                        status="pass",
                        method="heuristic",
                        confidence=0.8,
                        details={"fallback_reason": "local judge unavailable at http://127.0.0.1:11434"},
                    )
                ],
                diagnosis=None,
            )
        ],
        summary=VeritellRunSummary(total=1, passed=1, failed=0, errors=0, skipped=0, score=1.0),
    )

    report = render_terminal_report(Path("tests/ai"), suite)

    assert "note: no_unsupported_claims fell back to heuristic: local judge unavailable" in report



def test_render_terminal_report_includes_failed_assertion_details_and_unsupported_spans() -> None:
    suite = VeritellSuiteResult(
        results=[
            VeritellTestResult(
                test_id="failing_test",
                status="fail",
                score=0.0,
                assertion_results=[
                    AssertionResult(
                        assertion="no_unsupported_claims",
                        status="fail",
                        method="heuristic",
                        confidence=0.64,
                        details={
                            "unsupported_spans": ["45"],
                            "unsupported_span_analyses": [
                                {
                                    "span": "45",
                                    "rationale": "numbers not found in matched context: 45; best match came from retrieved_docs[0]",
                                }
                            ],
                            "actual": "Refunds are allowed within 45 days of purchase.",
                        },
                    )
                ],
                diagnosis=None,
            )
        ],
        summary=VeritellRunSummary(total=1, passed=0, failed=1, errors=0, skipped=0, score=0.0),
    )

    report = render_terminal_report(Path("tests/ai"), suite)

    assert "FAIL failing_test score=0.00 assertions=0/1 methods=heuristic" in report
    assert "failed assertions:" in report
    assert "- no_unsupported_claims [fail] method=heuristic confidence=0.640" in report
    assert "unsupported spans:" in report
    assert '"45"' in report
    assert "rationale: numbers not found in matched context: 45" in report
