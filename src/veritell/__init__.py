"""Veritell CLI package scaffold."""

from .assertions import (
    Assertion,
    evaluate_registered_assertion,
    get_assertion,
    list_assertions,
    register_assertion,
    unregister_assertion,
)
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
    "VeritellRunSummary",
    "VeritellSuiteResult",
    "VeritellTestCase",
    "VeritellTestResult",
    "discover_test_files",
    "evaluate_registered_assertion",
    "get_assertion",
    "list_assertions",
    "load_test_case",
    "load_test_cases",
    "load_test_suite",
    "register_assertion",
    "unregister_assertion",
]
