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
from veritell.backends import JudgeExecutionContext, LocalJudgeBackendUnavailable
from veritell.models import AssertionResult, VeritellTestCase
from veritell.runner import run_testcase


class AlwaysPassAssertion(Assertion):
    name = "always_pass_test"

    def supported_backends(self) -> tuple[str, ...]:
        return ("heuristic", "local")

    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params=None,  # noqa: ANN001
        judge_context=None,  # noqa: ANN001
    ) -> AssertionResult:
        return AssertionResult(
            assertion=self.name,
            status="pass",
            method=backend,
            confidence=1.0,
            details={"response": response, "testcase": testcase.name},
        )


class FakeLocalJudgeBackend:
    def evaluate_assertion(self, assertion_name: str, testcase: VeritellTestCase, response: str, *, params=None) -> AssertionResult:  # noqa: ANN001
        return AssertionResult(
            assertion=assertion_name,
            status="pass",
            method="local",
            confidence=0.91,
            details={"model": "fake-local", "reasoning": f"judged {testcase.name}"},
        )


class UnavailableLocalJudgeBackend:
    def evaluate_assertion(self, assertion_name: str, testcase: VeritellTestCase, response: str, *, params=None) -> AssertionResult:  # noqa: ANN001
        raise LocalJudgeBackendUnavailable("local judge unavailable at http://127.0.0.1:11434; ensure Ollama is running")


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

    result = run_testcase(testcase, judge_context=JudgeExecutionContext(preferred_backend="local"))

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
    assert result.details["claim_analyses"][0]["matched_context_source"] == "retrieved_docs[0]"



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
    assert result.details["unsupported_spans"] == ["Contractors"]
    assert result.details["unsupported_span_analyses"][0]["span"] == "Contractors"
    assert "best match came from retrieved_docs[0]" in result.details["unsupported_span_analyses"][0]["rationale"]
    assert result.details["claim_analyses"][0]["support_score"] < result.details["threshold"]



def test_no_unsupported_claims_flags_negation_mismatch_with_rationale() -> None:
    testcase = VeritellTestCase(
        name="negation_mismatch_case",
        input={"question": "What is the PTO policy?"},
        context={"retrieved_docs": ["Contractors do not receive PTO benefits."]},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], "Contractors receive PTO benefits.")

    assert result.status == "fail"
    assert result.details["unsupported_spans"] == ["Contractors receive PTO benefits"]
    assert result.details["claim_analyses"][0]["negation_mismatch"] is True
    assert "negation mismatch" in result.details["claim_analyses"][0]["rationale"]



def test_no_unsupported_claims_flags_number_mismatch_with_span_and_rationale() -> None:
    testcase = VeritellTestCase(
        name="number_mismatch_case",
        input={"question": "What is the refund window?"},
        context={"retrieved_docs": ["Refunds are allowed within 30 days of purchase."]},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], "Refunds are allowed within 45 days of purchase.")

    assert result.status == "fail"
    assert result.details["unsupported_spans"] == ["45"]
    assert result.details["claim_analyses"][0]["number_mismatches"] == ["45"]
    assert "numbers not found" in result.details["claim_analyses"][0]["rationale"]



def test_no_unsupported_claims_handles_mixed_supported_and_unsupported_claims() -> None:
    testcase = VeritellTestCase(
        name="mixed_claims_case",
        input={"question": "Summarize the PTO policy."},
        context={"retrieved_docs": ["Contractors do not receive PTO benefits."]},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    response = "Contractors do not receive PTO benefits. Contractors receive bonuses."
    result = evaluate_registered_assertion(testcase, testcase.assertions[0], response)

    assert result.status == "fail"
    assert result.details["supported_spans"] == ["Contractors do not receive PTO benefits"]
    assert result.details["unsupported_spans"] == ["bonuses"]
    assert len(result.details["unsupported_span_analyses"]) == 1
    assert result.details["unsupported_span_analyses"][0]["claim"] == "Contractors receive bonuses"



def test_no_unsupported_claims_uses_reference_answer_as_supporting_context() -> None:
    testcase = VeritellTestCase(
        name="reference_support_case",
        input={"question": "What is the refund window?"},
        context={"reference_answer": "Refunds are allowed within 30 days of purchase."},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    result = evaluate_registered_assertion(testcase, testcase.assertions[0], "Refunds are allowed within 30 days of purchase.")

    assert result.status == "pass"
    assert result.details["claim_analyses"][0]["matched_context_source"] == "reference_answer"


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


def test_no_unsupported_claims_uses_local_backend_when_requested() -> None:
    testcase = VeritellTestCase(
        name="local_judge_claims_case",
        input={"question": "What is the PTO policy?"},
        context={"retrieved_docs": ["Contractors do not receive PTO benefits."]},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    result = evaluate_registered_assertion(
        testcase,
        testcase.assertions[0],
        "Contractors do not receive PTO benefits.",
        judge_context=JudgeExecutionContext(preferred_backend="local", local_backend=FakeLocalJudgeBackend()),
    )

    assert result.status == "pass"
    assert result.method == "local"
    assert result.confidence == 0.91
    assert result.details["model"] == "fake-local"



def test_no_unsupported_claims_falls_back_to_heuristic_when_local_judge_unavailable() -> None:
    testcase = VeritellTestCase(
        name="local_judge_fallback_case",
        input={"question": "What is the PTO policy?"},
        context={"retrieved_docs": ["Contractors do not receive PTO benefits."]},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    result = evaluate_registered_assertion(
        testcase,
        testcase.assertions[0],
        "Contractors do not receive PTO benefits.",
        judge_context=JudgeExecutionContext(preferred_backend="local", local_backend=UnavailableLocalJudgeBackend()),
    )

    assert result.status == "pass"
    assert result.method == "heuristic"
    assert "fallback_reason" in result.details
    assert "local judge unavailable" in result.details["fallback_reason"]


def test_exact_match_ignores_selected_judge_backend() -> None:
    testcase = VeritellTestCase(
        name="deterministic_ignore_case",
        input={"question": "hello"},
        context={"reference_answer": "world"},
        assertions=[{"type": "exact_match"}],
    )

    result = evaluate_registered_assertion(
        testcase,
        testcase.assertions[0],
        "world",
        judge_context=JudgeExecutionContext(preferred_backend="cloud", default_backend="local"),
    )

    assert result.status == "pass"
    assert result.method == "deterministic"



def test_assertion_level_backend_override_beats_cli_selection() -> None:
    testcase = VeritellTestCase(
        name="override_backend_case",
        input={"question": "What is the PTO policy?"},
        context={"retrieved_docs": ["Contractors do not receive PTO benefits."]},
        assertions=[{"type": "no_unsupported_claims", "backend": "heuristic"}],
    )

    result = evaluate_registered_assertion(
        testcase,
        testcase.assertions[0],
        "Contractors do not receive PTO benefits.",
        judge_context=JudgeExecutionContext(preferred_backend="local", local_backend=FakeLocalJudgeBackend()),
    )

    assert result.status == "pass"
    assert result.method == "heuristic"



def test_default_backend_is_used_when_no_assertion_or_cli_override_exists() -> None:
    testcase = VeritellTestCase(
        name="default_backend_case",
        input={"question": "What is the PTO policy?"},
        context={"retrieved_docs": ["Contractors do not receive PTO benefits."]},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    result = evaluate_registered_assertion(
        testcase,
        testcase.assertions[0],
        "Contractors do not receive PTO benefits.",
        judge_context=JudgeExecutionContext(default_backend="local", local_backend=FakeLocalJudgeBackend()),
    )

    assert result.status == "pass"
    assert result.method == "local"



def test_hybrid_assertion_returns_structured_cloud_error_when_cloud_selected() -> None:
    testcase = VeritellTestCase(
        name="cloud_backend_case",
        input={"question": "What is the PTO policy?"},
        context={"retrieved_docs": ["Contractors do not receive PTO benefits."]},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    result = evaluate_registered_assertion(
        testcase,
        testcase.assertions[0],
        "Contractors do not receive PTO benefits.",
        judge_context=JudgeExecutionContext(preferred_backend="cloud"),
    )

    assert result.status == "error"
    assert result.method == "cloud"
    assert "not configured" in result.details["reason"]
