"""Tests for YAML/JSON test case loading and normalization."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from veritell.loader import InvalidTestCaseError, discover_test_files, load_test_case, load_test_cases, load_test_suite
from veritell.models import VeritellTestCase


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return path


def test_load_yaml_file_returns_normalized_test_case(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "policy.yaml",
        """
        name: contractor_policy_grounding
        input:
          question: How much PTO do contractors get?
        assertions:
          - expected_doc_retrieved
          - type: no_unsupported_claims
            backend: heuristic
        metadata:
          severity: medium
        """,
    )

    testcase = load_test_case(path)

    assert isinstance(testcase, VeritellTestCase)
    assert testcase.name == "contractor_policy_grounding"
    assert testcase.id is not None
    assert testcase.context == {}
    assert testcase.assertions[0] == {"type": "expected_doc_retrieved"}
    assert testcase.assertions[1]["backend"] == "heuristic"


def test_load_yml_file_preserves_optional_blocks(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "policy_suite.yml",
        """
        schema_version: v1
        name: refund_policy_json_output
        description: Validate structured output.
        input:
          question: Return the refund policy as JSON
        context:
          system_prompt: You are a policy bot.
        assertions:
          - type: response_format_valid
          - type: json_schema_valid
            params:
              schema_ref: refund_policy_schema.json
        metadata:
          tags:
            - structured-output
        """,
    )

    testcase = load_test_case(path)

    assert testcase.description == "Validate structured output."
    assert testcase.context["system_prompt"] == "You are a policy bot."
    assert testcase.assertions[1]["params"]["schema_ref"] == "refund_policy_schema.json"
    assert testcase.metadata["tags"] == ["structured-output"]


def test_load_json_file_returns_normalized_test_case(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "policy.json",
        """
        {
          "name": "unknown_policy_year_should_abstain",
          "input": {"question": "What was the PTO policy in 2003?"},
          "context": {"retrieved_docs": []},
          "assertions": [
            {"type": "should_abstain"},
            {"type": "no_unsupported_claims", "backend": "local"}
          ]
        }
        """,
    )

    testcase = load_test_case(path)

    assert testcase.name == "unknown_policy_year_should_abstain"
    assert testcase.context["retrieved_docs"] == []
    assert testcase.assertions[1]["backend"] == "local"


def test_discover_test_files_ignores_unsupported_files(tmp_path: Path) -> None:
    supported_yaml = _write(
        tmp_path,
        "alpha.yaml",
        """
        name: alpha
        input:
          question: hi
        assertions:
          - exact_match
        """,
    )
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    supported_json = _write(
        nested_dir,
        "beta.json",
        """
        {
          "name": "beta",
          "input": {"question": "there"},
          "assertions": [{"type": "exact_match"}]
        }
        """,
    )
    _write(
        tmp_path,
        "ignore.txt",
        "not a supported test file",
    )

    discovered = discover_test_files(tmp_path)

    assert discovered == [supported_yaml, supported_json]


def test_load_multiple_files_warns_on_duplicate_names(tmp_path: Path) -> None:
    one = _write(
        tmp_path,
        "one.yaml",
        """
        name: duplicate_name
        input:
          question: hi
        assertions:
          - exact_match
        """,
    )
    two = _write(
        tmp_path,
        "two.json",
        """
        {
          "name": "duplicate_name",
          "input": {"question": "there"},
          "assertions": [{"type": "exact_match"}]
        }
        """,
    )

    with pytest.warns(UserWarning, match="Duplicate test name 'duplicate_name'"):
        cases = load_test_cases([one, two])

    assert len(cases) == 2


def test_load_test_suite_from_directory_loads_all_supported_tests(tmp_path: Path) -> None:
    suite_dir = tmp_path / "tests" / "ai"
    suite_dir.mkdir(parents=True)
    _write(
        suite_dir,
        "one.yaml",
        """
        name: one
        input:
          question: hi
        assertions:
          - exact_match
        """,
    )
    _write(
        suite_dir,
        "two.yml",
        """
        name: two
        input:
          question: there
        assertions:
          - exact_match
        """,
    )
    _write(
        suite_dir,
        "notes.md",
        "# ignored",
    )

    cases = load_test_suite(suite_dir)

    assert [case.name for case in cases] == ["one", "two"]


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        (
            "missing_assertions.yaml",
            """
            name: missing_assertions
            input:
              question: hi
            """,
            "at least 1 item",
        ),
        (
            "invalid_backend.json",
            """
            {
              "name": "bad_backend",
              "input": {"question": "hi"},
              "assertions": [{"type": "exact_match", "backend": "remote"}]
            }
            """,
            "backend must be one of",
        ),
        (
            "bad_version.yml",
            """
            schema_version: v9
            name: future_case
            input:
              question: hi
            assertions:
              - exact_match
            """,
            "unsupported schema_version",
        ),
    ],
)
def test_invalid_tests_raise_clear_errors(tmp_path: Path, filename: str, content: str, message: str) -> None:
    path = _write(tmp_path, filename, content)

    with pytest.raises(InvalidTestCaseError, match=message) as exc_info:
        load_test_case(path)

    assert filename in str(exc_info.value)


def test_invalid_yaml_syntax_raises_clear_error(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "broken.yaml",
        """
        name: broken
        input:
          question: hi
        assertions:
          - type: exact_match
          - type: [
        """,
    )

    with pytest.raises(InvalidTestCaseError, match="failed to parse file") as exc_info:
        load_test_case(path)

    assert "broken.yaml" in str(exc_info.value)


def test_missing_input_question_warns_without_failing(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "no_question.yaml",
        """
        name: no_question
        input:
          prompt: hi
        assertions:
          - exact_match
        metadata:
          severity: severe
        """,
    )

    with pytest.warns(UserWarning) as recorded:
        testcase = load_test_case(path)

    messages = [str(warning.message) for warning in recorded]
    assert any("input.question is recommended but missing" in message for message in messages)
    assert any("metadata.severity 'severe' is outside recommended values" in message for message in messages)
    assert testcase.input == {"prompt": "hi"}


def test_load_test_suite_errors_when_no_supported_files_found(tmp_path: Path) -> None:
    suite_dir = tmp_path / "tests" / "ai"
    suite_dir.mkdir(parents=True)
    _write(suite_dir, "notes.txt", "ignored")

    with pytest.raises(InvalidTestCaseError, match="no supported test files found") as exc_info:
        load_test_suite(suite_dir)

    assert "tests" in str(exc_info.value)

