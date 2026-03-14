"""Smoke tests for editable installs and import safety."""

from __future__ import annotations

import veritell
from veritell import (
    Assertion,
    AssertionResult,
    JudgeExecutionContext,
    LocalJudgeSettings,
    VeritellRunSummary,
    VeritellSuiteResult,
    VeritellTestCase,
    VeritellTestResult,
    build_judge_context,
    get_assertion,
    load_local_judge_settings,
    register_assertion,
    unregister_assertion,
)
from veritell.cli import main
from veritell.runner import run_test_suite, run_testcase
from veritell.testcase import TestCase


def test_package_imports() -> None:
    assert veritell.__version__ == "0.1.0"
    assert callable(main)
    assert Assertion is not None
    assert JudgeExecutionContext is not None
    assert LocalJudgeSettings is not None
    assert VeritellTestCase is not None
    assert AssertionResult is not None
    assert VeritellTestResult is not None
    assert VeritellRunSummary is not None
    assert VeritellSuiteResult is not None
    assert callable(build_judge_context)
    assert callable(load_local_judge_settings)
    assert callable(register_assertion)
    assert callable(unregister_assertion)
    assert get_assertion("exact_match") is not None


def test_runner_smoke() -> None:
    testcase = TestCase(
        name="exact-match",
        input={"question": "hello"},
        context={"reference_answer": "world"},
        metadata={"mock_response": "world"},
        assertions=[{"type": "exact_match"}],
    )

    result = run_testcase(testcase, actual_output="world")
    suite = run_test_suite([testcase], response_provider=lambda _: "world")

    assert isinstance(testcase, VeritellTestCase)
    assert result.status == "pass"
    assert result.score == 1.0
    assert result.diagnosis is None
    assert result.assertion_results[0].status == "pass"
    assert suite.summary.total == 1
    assert suite.summary.passed == 1
