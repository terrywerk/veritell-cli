"""Tests for the runner skeleton."""

from __future__ import annotations

from veritell.backends import JudgeExecutionContext, LocalJudgeBackendUnavailable
from veritell.models import AssertionResult, VeritellTestCase
from veritell.runner import run_test_suite, run_testcase


class FakeLocalJudgeBackend:
    def evaluate_assertion(self, assertion_name: str, testcase: VeritellTestCase, response: str, *, params=None) -> AssertionResult:  # noqa: ANN001
        return AssertionResult(
            assertion=assertion_name,
            status="pass",
            method="local",
            confidence=0.88,
            details={"model": "fake-local"},
        )


class UnavailableLocalJudgeBackend:
    def evaluate_assertion(self, assertion_name: str, testcase: VeritellTestCase, response: str, *, params=None) -> AssertionResult:  # noqa: ANN001
        raise LocalJudgeBackendUnavailable("local judge unavailable at http://127.0.0.1:11434; ensure Ollama is running")


def test_run_testcase_exact_match_passes() -> None:
    testcase = VeritellTestCase(
        name="exact_match_pass",
        input={"question": "hello"},
        context={"reference_answer": "world"},
        metadata={"mock_response": "world"},
        assertions=[{"type": "exact_match"}],
    )

    result = run_testcase(testcase)

    assert result.status == "pass"
    assert result.score == 1.0
    assert result.assertion_results[0].details["expected"] == "world"



def test_run_test_suite_returns_summary_counts() -> None:
    cases = [
        VeritellTestCase(
            name="pass_case",
            input={"question": "hello"},
            context={"reference_answer": "world"},
            metadata={"mock_response": "world"},
            assertions=[{"type": "exact_match"}],
        ),
        VeritellTestCase(
            name="fail_case",
            input={"question": "hello"},
            context={"reference_answer": "world"},
            metadata={"mock_response": "different"},
            assertions=[{"type": "exact_match"}],
        ),
        VeritellTestCase(
            name="skip_case",
            input={"question": "hello"},
            assertions=[{"type": "future_assertion"}],
        ),
        VeritellTestCase(
            name="error_case",
            input={"question": "hello"},
            assertions=[{"type": "exact_match"}],
        ),
    ]

    suite = run_test_suite(cases)

    assert suite.summary.total == 4
    assert suite.summary.passed == 1
    assert suite.summary.failed == 1
    assert suite.summary.errors == 1
    assert suite.summary.skipped == 1
    assert [result.status for result in suite.results] == ["pass", "fail", "skip", "error"]
    assert suite.results[2].assertion_results[0].method == "unsupported"



def test_run_test_suite_supports_response_provider() -> None:
    cases = [
        VeritellTestCase(
            name="provider_case",
            input={"question": "hello"},
            context={"reference_answer": "provided"},
            assertions=[{"type": "exact_match"}],
        )
    ]

    suite = run_test_suite(cases, response_provider=lambda testcase: testcase.context["reference_answer"])

    assert suite.summary.passed == 1
    assert suite.summary.failed == 0



def test_run_testcase_expected_doc_retrieved_passes() -> None:
    testcase = VeritellTestCase(
        name="retrieval_case",
        input={"question": "hello"},
        context={
            "expected_docs": ["policy_v2.txt"],
            "retrieved_docs": ["policy_v2.txt", "benefits.md"],
        },
        assertions=[{"type": "expected_doc_retrieved"}],
    )

    result = run_testcase(testcase)

    assert result.status == "pass"
    assert result.assertion_results[0].status == "pass"



def test_run_test_suite_counts_new_deterministic_assertions() -> None:
    cases = [
        VeritellTestCase(
            name="format_pass_case",
            input={"question": "hello"},
            metadata={"mock_response": '{"answer": "ok"}'},
            assertions=[{"type": "response_format_valid", "params": {"format": "json"}}],
        ),
        VeritellTestCase(
            name="schema_fail_case",
            input={"question": "hello"},
            metadata={"mock_response": '{"answer": 123}'},
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
        ),
    ]

    suite = run_test_suite(cases)

    assert suite.summary.total == 2
    assert suite.summary.passed == 1
    assert suite.summary.failed == 1
    assert suite.results[0].assertion_results[0].assertion == "response_format_valid"
    assert suite.results[1].assertion_results[0].assertion == "json_schema_valid"



def test_run_test_suite_counts_heuristic_no_unsupported_claims() -> None:
    cases = [
        VeritellTestCase(
            name="grounded_case",
            input={"question": "What is the PTO policy?"},
            context={
                "retrieved_docs": ["Contractors do not receive PTO benefits."],
            },
            metadata={"mock_response": "Contractors do not receive PTO benefits."},
            assertions=[{"type": "no_unsupported_claims"}],
        ),
        VeritellTestCase(
            name="hallucinated_case",
            input={"question": "What is the PTO policy?"},
            context={
                "retrieved_docs": ["Contractors do not receive PTO benefits. Full-time employees receive 15 PTO days per year."],
            },
            metadata={"mock_response": "Contractors receive 15 PTO days per year."},
            assertions=[{"type": "no_unsupported_claims"}],
        ),
    ]

    suite = run_test_suite(cases)

    assert suite.summary.total == 2
    assert suite.summary.passed == 1
    assert suite.summary.failed == 1
    assert suite.results[0].assertion_results[0].method == "heuristic"
    assert suite.results[1].assertion_results[0].details["unsupported_spans"] == ["Contractors"]



def test_run_test_suite_preserves_mixed_claim_span_details() -> None:
    testcase = VeritellTestCase(
        name="mixed_claims_case",
        input={"question": "Summarize the PTO policy."},
        context={"retrieved_docs": ["Contractors do not receive PTO benefits."]},
        metadata={"mock_response": "Contractors do not receive PTO benefits. Contractors receive bonuses."},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    suite = run_test_suite([testcase])

    assert suite.summary.failed == 1
    assert suite.results[0].assertion_results[0].details["supported_spans"] == ["Contractors do not receive PTO benefits"]
    assert suite.results[0].assertion_results[0].details["unsupported_span_analyses"][0]["span"] == "bonuses"


def test_run_testcase_uses_local_judge_when_requested() -> None:
    testcase = VeritellTestCase(
        name="local_judge_case",
        input={"question": "What is the PTO policy?"},
        context={"retrieved_docs": ["Contractors do not receive PTO benefits."]},
        metadata={"mock_response": "Contractors do not receive PTO benefits."},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    result = run_testcase(
        testcase,
        judge_context=JudgeExecutionContext(preferred_backend="local", local_backend=FakeLocalJudgeBackend()),
    )

    assert result.status == "pass"
    assert result.assertion_results[0].method == "local"
    assert result.assertion_results[0].confidence == 0.88



def test_run_testcase_falls_back_to_heuristic_when_local_judge_is_unavailable() -> None:
    testcase = VeritellTestCase(
        name="fallback_case",
        input={"question": "What is the PTO policy?"},
        context={"retrieved_docs": ["Contractors do not receive PTO benefits."]},
        metadata={"mock_response": "Contractors do not receive PTO benefits."},
        assertions=[{"type": "no_unsupported_claims"}],
    )

    result = run_testcase(
        testcase,
        judge_context=JudgeExecutionContext(preferred_backend="local", local_backend=UnavailableLocalJudgeBackend()),
    )

    assert result.status == "pass"
    assert result.assertion_results[0].method == "heuristic"
    assert "fallback_reason" in result.assertion_results[0].details
