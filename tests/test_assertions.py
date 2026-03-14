"""Tests for the assertion plugin contract and registry."""

from __future__ import annotations

import json

from veritell.assertions import (
    Assertion,
    evaluate_registered_assertion,
    get_assertion,
    list_assertions,
    register_assertion,
    unregister_assertion,
)
from veritell.models import AssertionResult, VeritellTestCase
from veritell.runner import run_testcase


class AlwaysPassAssertion(Assertion):
    name = "always_pass_test"

    def supported_backends(self) -> tuple[str, ...]:
        return ("heuristic", "local")

    def evaluate(self, testcase: VeritellTestCase, response: str, *, backend: str = "heuristic", params=None) -> AssertionResult:  # noqa: ANN001
        return AssertionResult(
            assertion=self.name,
            status="pass",
            method=backend,
            confidence=1.0,
            details={"response": response, "testcase": testcase.name},
        )



def test_built_in_assertions_are_registered() -> None:
    names = list_assertions()

    assert "exact_match" in names
    assert "response_format_valid" in names
    assert "json_schema_valid" in names
    assert "no_unsupported_claims" in names
    assert get_assertion("expected_doc_retrieved") is not None



def test_assertions_can_be_registered_dynamically() -> None:
    unregister_assertion(AlwaysPassAssertion.name)
    register_assertion(AlwaysPassAssertion)

    testcase = VeritellTestCase(
        name="dynamic_assertion_case",
        input={"question": "hello"},
        assertions=[{"type": AlwaysPassAssertion.name}],
        metadata={"mock_response": "hi"},
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], "hi")

    assert result.status == "pass"
    assert result.method == "heuristic"
    assert result.details["testcase"] == "dynamic_assertion_case"

    unregister_assertion(AlwaysPassAssertion.name)



def test_runner_uses_registered_assertions() -> None:
    unregister_assertion(AlwaysPassAssertion.name)
    register_assertion(AlwaysPassAssertion)

    testcase = VeritellTestCase(
        name="runner_dynamic_case",
        input={"question": "hello"},
        assertions=[{"type": AlwaysPassAssertion.name, "backend": "local"}],
        metadata={"mock_response": "hi"},
    )

    result = run_testcase(testcase)

    assert result.status == "pass"
    assert result.assertion_results[0].assertion == AlwaysPassAssertion.name
    assert result.assertion_results[0].method == "local"

    unregister_assertion(AlwaysPassAssertion.name)



def test_registry_rejects_duplicate_registration() -> None:
    unregister_assertion(AlwaysPassAssertion.name)
    register_assertion(AlwaysPassAssertion)

    try:
        try:
            register_assertion(AlwaysPassAssertion)
        except ValueError as exc:
            assert "already registered" in str(exc)
        else:
            raise AssertionError("expected duplicate registration to fail")
    finally:
        unregister_assertion(AlwaysPassAssertion.name)



def test_registry_returns_structured_result_for_unsupported_backend() -> None:
    unregister_assertion(AlwaysPassAssertion.name)
    register_assertion(AlwaysPassAssertion)

    testcase = VeritellTestCase(
        name="unsupported_backend_case",
        input={"question": "hello"},
        assertions=[{"type": AlwaysPassAssertion.name, "backend": "cloud"}],
        metadata={"mock_response": "hi"},
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], "hi")

    assert result.status == "error"
    assert "supported backends" in result.details["reason"]

    unregister_assertion(AlwaysPassAssertion.name)


def test_response_format_valid_passes_for_json_output() -> None:
    testcase = VeritellTestCase(
        name="json_format_pass",
        input={"question": "hello"},
        assertions=[{"type": "response_format_valid", "params": {"format": "json"}}],
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], '{"answer": "ok"}')

    assert result.status == "pass"
    assert result.details["format"] == "json"
    assert result.details["parsed_type"] == "dict"



def test_response_format_valid_fails_for_invalid_json() -> None:
    testcase = VeritellTestCase(
        name="json_format_fail",
        input={"question": "hello"},
        assertions=[{"type": "response_format_valid", "params": {"format": "json"}}],
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], 'not-json')

    assert result.status == "fail"
    assert result.details["format"] == "json"
    assert "reason" in result.details



def test_json_schema_valid_passes_with_inline_schema() -> None:
    testcase = VeritellTestCase(
        name="json_schema_pass",
        input={"question": "hello"},
        assertions=[
            {
                "type": "json_schema_valid",
                "params": {
                    "schema": {
                        "type": "object",
                        "properties": {"answer": {"type": "string"}},
                        "required": ["answer"],
                    }
                },
            }
        ],
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], json.dumps({"answer": "ok"}))

    assert result.status == "pass"
    assert "schema_keys" in result.details



def test_json_schema_valid_fails_when_payload_breaks_schema() -> None:
    testcase = VeritellTestCase(
        name="json_schema_fail",
        input={"question": "hello"},
        assertions=[
            {
                "type": "json_schema_valid",
                "params": {
                    "schema": {
                        "type": "object",
                        "properties": {"answer": {"type": "string"}},
                        "required": ["answer"],
                    }
                },
            }
        ],
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], json.dumps({"answer": 123}))

    assert result.status == "fail"
    assert result.details["validator"] == "type"



def test_expected_doc_retrieved_returns_structured_fail_result() -> None:
    testcase = VeritellTestCase(
        name="expected_doc_fail",
        input={"question": "hello"},
        context={"expected_docs": ["policy.txt"], "retrieved_docs": ["benefits.txt"]},
        assertions=[{"type": "expected_doc_retrieved"}],
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], "ignored")

    assert result.status == "fail"
    assert result.details["missing_docs"] == ["policy.txt"]



def test_retrieval_contains_answer_returns_structured_pass_result() -> None:
    testcase = VeritellTestCase(
        name="retrieval_answer_pass",
        input={"question": "hello"},
        context={
            "reference_answer": "contractors do not receive PTO",
            "retrieved_docs": ["Policy states contractors do not receive PTO benefits."],
        },
        assertions=[{"type": "retrieval_contains_answer"}],
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], "ignored")

    assert result.status == "pass"
    assert result.details["reference_answer"] == "contractors do not receive PTO"


def test_no_unsupported_claims_passes_when_claims_are_grounded() -> None:
    testcase = VeritellTestCase(
        name="grounded_claims_case",
        input={"question": "What is the PTO policy?"},
        context={
            "retrieved_docs": [
                "Contractors do not receive PTO benefits. Full-time employees receive 15 PTO days per year."
            ]
        },
        assertions=[{"type": "no_unsupported_claims"}],
    )

    response = "Contractors do not receive PTO benefits."
    result = evaluate_registered_assertion(testcase, testcase.assertions[0], response)

    assert result.status == "pass"
    assert result.method == "heuristic"
    assert result.confidence is not None
    assert result.details["unsupported_spans"] == []
    assert result.details["supported_spans"] == ["Contractors do not receive PTO benefits"]



def test_no_unsupported_claims_detects_unsupported_spans() -> None:
    testcase = VeritellTestCase(
        name="unsupported_claims_case",
        input={"question": "What is the PTO policy?"},
        context={
            "retrieved_docs": [
                "Contractors do not receive PTO benefits. Full-time employees receive 15 PTO days per year."
            ]
        },
        assertions=[{"type": "no_unsupported_claims"}],
    )

    response = "Contractors receive 15 PTO days per year."
    result = evaluate_registered_assertion(testcase, testcase.assertions[0], response)

    assert result.status == "fail"
    assert result.method == "heuristic"
    assert result.confidence is not None
    assert result.details["unsupported_spans"] == ["Contractors receive 15 PTO days per year"]
    assert result.details["claim_analyses"][0]["support_score"] < result.details["threshold"]



def test_no_unsupported_claims_errors_without_context() -> None:
    testcase = VeritellTestCase(
        name="unsupported_claims_no_context",
        input={"question": "What is the PTO policy?"},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], "Contractors do not receive PTO benefits.")

    assert result.status == "error"
    assert result.method == "heuristic"
    assert result.confidence == 0.0
    assert "textual context is required" in result.details["reason"]
