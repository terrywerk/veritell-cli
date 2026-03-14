"""Runner utilities for the Veritell CLI scaffold."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from .assertions import evaluate_registered_assertion
from .backends import JudgeExecutionContext
from .models import (
    AssertionResult,
    VeritellRunSummary,
    VeritellSuiteResult,
    VeritellTestCase,
    VeritellTestResult,
)

RunResult = VeritellTestResult
SuiteResult = VeritellSuiteResult
ResponseProvider = Callable[[VeritellTestCase], str | None]


def run_testcase(
    testcase: VeritellTestCase,
    actual_output: str | None = None,
    *,
    response_provider: ResponseProvider | None = None,
    judge_context: JudgeExecutionContext | None = None,
) -> RunResult:
    """Evaluate a single normalized test case and return a structured result."""

    response_text = _resolve_output(testcase, actual_output=actual_output, response_provider=response_provider)
    assertion_results = [
        evaluate_registered_assertion(testcase, assertion, response_text, judge_context=judge_context)
        for assertion in testcase.assertions
    ]
    status = _derive_status(assertion_results)
    active_results = [result for result in assertion_results if result.status != "skip"]
    passed_results = [result for result in active_results if result.status == "pass"]
    score = (len(passed_results) / len(active_results)) if active_results else None
    diagnosis = _build_diagnosis(assertion_results)
    return RunResult(
        test_id=testcase.id or testcase.name,
        status=status,
        assertion_results=assertion_results,
        score=score,
        diagnosis=diagnosis,
    )


def run_test_suite(
    testcases: Iterable[VeritellTestCase],
    *,
    response_provider: ResponseProvider | None = None,
    judge_context: JudgeExecutionContext | None = None,
) -> SuiteResult:
    """Run a suite of normalized test cases and return per-test results plus summary counts."""

    results = [run_testcase(testcase, response_provider=response_provider, judge_context=judge_context) for testcase in testcases]
    summary = VeritellRunSummary(
        total=len(results),
        passed=sum(result.status == "pass" for result in results),
        failed=sum(result.status == "fail" for result in results),
        errors=sum(result.status == "error" for result in results),
        skipped=sum(result.status == "skip" for result in results),
        score=(sum((result.score or 0.0) for result in results) / len(results)) if results else None,
    )
    return SuiteResult(results=results, summary=summary)



def _resolve_output(
    testcase: VeritellTestCase,
    *,
    actual_output: str | None,
    response_provider: ResponseProvider | None,
) -> str:
    if actual_output is not None:
        return actual_output
    if response_provider is not None:
        provided = response_provider(testcase)
        return "" if provided is None else str(provided)

    for candidate in (
        testcase.metadata.get("mock_response"),
        testcase.context.get("response"),
        testcase.context.get("reference_answer"),
    ):
        if isinstance(candidate, str):
            return candidate
    return ""


def _derive_status(assertion_results: list[AssertionResult]) -> str:
    statuses = {result.status for result in assertion_results}
    if "error" in statuses:
        return "error"
    if "fail" in statuses:
        return "fail"
    if statuses == {"skip"}:
        return "skip"
    return "pass"



def _build_diagnosis(assertion_results: list[AssertionResult]) -> dict[str, Any] | None:
    failures = [result.assertion for result in assertion_results if result.status in {"fail", "error"}]
    if not failures:
        return None
    return {
        "failing_assertions": failures,
        "failure_count": len(failures),
    }
