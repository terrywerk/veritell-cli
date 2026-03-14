"""Veritell CLI package scaffold."""

from .assertions import (
    Assertion,
    evaluate_registered_assertion,
    get_assertion,
    list_assertions,
    register_assertion,
    unregister_assertion,
)
from .backends import JudgeExecutionContext, LocalJudgeSettings, build_judge_context, load_local_judge_settings
from .loader import InvalidTestCaseError, discover_test_files, load_test_case, load_test_cases, load_test_suite
from .models import (
    AssertionResult,
    VeritellRunSummary,
    VeritellSuiteResult,
    VeritellTestCase,
    VeritellTestResult,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Assertion",
    "AssertionResult",
    "InvalidTestCaseError",
    "JudgeExecutionContext",
    "LocalJudgeSettings",
    "VeritellRunSummary",
    "VeritellSuiteResult",
    "VeritellTestCase",
    "VeritellTestResult",
    "build_judge_context",
    "discover_test_files",
    "evaluate_registered_assertion",
    "get_assertion",
    "list_assertions",
    "load_local_judge_settings",
    "load_test_case",
    "load_test_cases",
    "load_test_suite",
    "register_assertion",
    "unregister_assertion",
]
