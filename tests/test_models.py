"""Tests for the canonical Veritell models."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from veritell.models import AssertionResult, VeritellTestCase, VeritellTestResult


def test_veritell_test_case_serializes_round_trip() -> None:
    testcase = VeritellTestCase(
        id="tc-001",
        name="contractor_policy_grounding",
        description="Ensure grounded answers stay within retrieved policy docs.",
        input={"question": "How much PTO do contractors get?"},
        context={
            "retrieved_docs": ["contractor_policy_v2.txt"],
            "reference_answer": "Contractors do not receive PTO benefits.",
        },
        assertions=[
            {"type": "expected_doc_retrieved"},
            {"type": "no_unsupported_claims", "backend": "heuristic"},
        ],
        metadata={"tags": ["rag", "grounding"], "severity": "medium"},
    )

    payload = testcase.to_dict()
    restored = VeritellTestCase.from_json(testcase.to_json())

    assert payload["name"] == "contractor_policy_grounding"
    assert payload["assertions"][1]["backend"] == "heuristic"
    assert restored == testcase


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("assertions", []),
        ("assertions", [{"backend": "heuristic"}]),
    ],
)
def test_veritell_test_case_validation(field: str, value: object) -> None:
    data: dict[str, Any] = {
        "name": "valid_case",
        "input": {"question": "hello"},
        "assertions": [{"type": "exact_match"}],
    }
    data[field] = value

    with pytest.raises(ValidationError):
        VeritellTestCase(**data)


def test_assertion_result_is_serializable() -> None:
    result = AssertionResult(
        assertion="no_unsupported_claims",
        status="fail",
        method="heuristic",
        confidence=0.63,
        details={"unsupported_spans": ["14 days of PTO"]},
    )

    round_trip = AssertionResult.from_dict(result.to_dict())

    assert round_trip == result
    assert '"status":"fail"' in result.to_json()


def test_veritell_test_result_supports_nested_serialization() -> None:
    diagnosis: dict[str, str] | None = {"category": "unsupported claim"}
    result = VeritellTestResult(
        test_id="tc-001",
        status="fail",
        score=0.0,
        assertion_results=[
            AssertionResult(
                assertion="no_unsupported_claims",
                status="fail",
                method="heuristic",
                confidence=0.4,
                details={"unsupported_spans": ["incorrect policy date"]},
            )
        ],
        diagnosis=diagnosis,
    )

    restored = VeritellTestResult.from_json(result.to_json())

    assert restored == result
    assert restored.assertion_results[0].details["unsupported_spans"] == ["incorrect policy date"]
