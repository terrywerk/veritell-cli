"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from veritell import cli
from veritell.backends import JudgeExecutionContext, LocalJudgeBackendUnavailable
from veritell.commands import VeritellCLIError
from veritell.models import AssertionResult

runner = CliRunner()


class FakeLocalJudgeBackend:
    def evaluate_assertion(self, assertion_name, testcase, response, *, params=None):  # noqa: ANN001
        return AssertionResult(
            assertion=assertion_name,
            status="pass",
            method="local",
            confidence=0.89,
            details={"model": "fake-local"},
        )


class UnavailableLocalJudgeBackend:
    def evaluate_assertion(self, assertion_name, testcase, response, *, params=None):  # noqa: ANN001
        raise LocalJudgeBackendUnavailable("local judge unavailable at http://127.0.0.1:11434; ensure Ollama is running")


def test_cli_help() -> None:
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "Veritell CLI scaffold" in result.output
    for command_name in ("test", "scan", "generate-evals", "import-evals", "diagnose"):
        assert command_name in result.output


def test_cli_version() -> None:
    result = runner.invoke(cli.app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == "0.1.0"


def test_cli_commands_smoke() -> None:
    cases = [
        (["scan"], "Scaffolded scan for ."),
        (["generate-evals"], "Scaffolded eval generation into tests/generated"),
        (["import-evals"], "Scaffolded eval import from imports/evals.jsonl"),
        (["diagnose"], "Scaffolded diagnostics for latest"),
    ]

    for argv, expected in cases:
        result = runner.invoke(cli.app, argv)
        assert result.exit_code == 0
        assert expected in result.output


def test_cli_test_command_uses_default_tests_ai_directory(tmp_path: Path, monkeypatch) -> None:
    suite_dir = tmp_path / "tests" / "ai"
    suite_dir.mkdir(parents=True)
    (suite_dir / "sample.yaml").write_text(
        "name: default_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: hi\nmetadata:\n  mock_response: hi\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(cli.app, ["test"])

    assert result.exit_code == 0
    assert "Suite: tests/ai" in result.output
    assert "PASS default_sample-" in result.output
    assert "score=1.00 assertions=1/1 methods=deterministic" in result.output
    assert "Summary: total=1 passed=1 failed=0 errors=0 skipped=0 reliability=100.00% score=1.00" in result.output


def test_cli_test_command_loads_custom_directory(tmp_path: Path) -> None:
    suite_dir = tmp_path / "custom-suite"
    suite_dir.mkdir()
    (suite_dir / "one.yaml").write_text(
        "name: one\ninput:\n  question: hi\ncontext:\n  reference_answer: hi\nmetadata:\n  mock_response: hi\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )
    (suite_dir / "two.json").write_text(
        '{"name":"two","input":{"question":"there"},"context":{"reference_answer":"there"},"metadata":{"mock_response":"there"},"assertions":[{"type":"exact_match"}]}',
        encoding="utf-8",
    )
    (suite_dir / "ignore.txt").write_text("ignored", encoding="utf-8")

    result = runner.invoke(cli.app, ["test", str(suite_dir)])

    assert result.exit_code == 0
    assert f"Suite: {suite_dir.as_posix()}" in result.output
    assert "PASS one-" in result.output
    assert "PASS two-" in result.output
    assert result.output.count("score=1.00 assertions=1/1 methods=deterministic") == 2
    assert "Summary: total=2 passed=2 failed=0 errors=0 skipped=0 reliability=100.00% score=1.00" in result.output


def test_cli_test_command_loads_supported_file(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.yaml"
    file_path.write_text(
        "name: cli_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: hi\nmetadata:\n  mock_response: hi\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(file_path)])

    assert result.exit_code == 0
    assert f"Suite: {file_path.as_posix()}" in result.output
    assert "PASS cli_sample-" in result.output
    assert "score=1.00 assertions=1/1 methods=deterministic" in result.output


def test_cli_test_command_json_output_includes_results_and_summary(tmp_path: Path) -> None:
    suite_dir = tmp_path / "json-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: json_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: hi\nmetadata:\n  mock_response: hi\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--json"])

    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert payload["summary"]["passed"] == 1
    assert payload["results"][0]["assertion_results"][0]["assertion"] == "exact_match"
    assert payload["results"][0]["status"] == "pass"


def test_main_wrapper_returns_zero_for_help() -> None:
    exit_code = cli.main(["--help"])

    assert exit_code == 0


def test_cli_failure_exits_non_zero(monkeypatch) -> None:
    def failing_run_test(path, json_output=False, fail_below=None, judge=None):  # noqa: ANN001, FBT002
        raise VeritellCLIError(f"boom: {path}")

    monkeypatch.setattr(cli.commands, "run_test", failing_run_test)

    result = runner.invoke(cli.app, ["test", "tests"])

    assert result.exit_code == 1
    assert "Error: boom: tests" in result.output


def test_cli_test_command_returns_non_zero_for_failed_suite(tmp_path: Path) -> None:
    suite_dir = tmp_path / "failing-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: failing_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: expected\nmetadata:\n  mock_response: actual\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir)])

    assert result.exit_code == 1
    assert "FAIL failing_sample-" in result.output
    assert "score=0.00 assertions=0/1 methods=deterministic" in result.output
    assert "failed assertions:" in result.output
    assert "- exact_match [fail] method=deterministic confidence=1.000" in result.output
    assert "expected: expected" in result.output
    assert "actual: actual" in result.output
    assert "Summary: total=1 passed=0 failed=1 errors=0 skipped=0 reliability=0.00% score=0.00" in result.output


def test_cli_test_command_json_output_preserves_non_zero_exit_for_failed_suite(tmp_path: Path) -> None:
    suite_dir = tmp_path / "failing-json-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: failing_json_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: expected\nmetadata:\n  mock_response: actual\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--json"])

    payload = json.loads(result.output)
    assert result.exit_code == 1
    assert payload["summary"]["failed"] == 1
    assert payload["results"][0]["assertion_results"][0]["status"] == "fail"


def test_cli_test_command_errors_when_no_tests_found(tmp_path: Path) -> None:
    suite_dir = tmp_path / "empty-suite"
    suite_dir.mkdir()
    (suite_dir / "notes.md").write_text("ignored", encoding="utf-8")

    result = runner.invoke(cli.app, ["test", str(suite_dir)])

    assert result.exit_code == 1
    assert "no supported test files found" in result.output


def test_cli_test_command_fail_below_passes_at_threshold(tmp_path: Path) -> None:
    suite_dir = tmp_path / "threshold-pass-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: threshold_pass_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: hi\nmetadata:\n  mock_response: hi\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--fail-below", "100"])

    assert result.exit_code == 0
    assert "Summary: total=1 passed=1 failed=0 errors=0 skipped=0 reliability=100.00% score=1.00" in result.output
    assert "Gate: threshold=100.00 score=100.00 passed=true" in result.output


def test_cli_test_command_fail_below_returns_non_zero_below_threshold(tmp_path: Path) -> None:
    suite_dir = tmp_path / "threshold-fail-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: threshold_fail_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: hi\nmetadata:\n  mock_response: hi\nassertions:\n  - exact_match\n  - future_assertion\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--fail-below", "80"])

    assert result.exit_code == 0
    assert "PASS threshold_fail_sample-" in result.output
    assert "score=1.00 assertions=1/1 methods=deterministic,unsupported" in result.output
    assert "Gate: threshold=80.00 score=100.00 passed=true" in result.output


def test_cli_test_command_json_output_includes_gate_metadata(tmp_path: Path) -> None:
    suite_dir = tmp_path / "json-gate-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: json_gate_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: hi\nmetadata:\n  mock_response: hi\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--json", "--fail-below", "80"])

    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert payload["gate"]["threshold"] == 80.0
    assert payload["gate"]["score"] == 100.0
    assert payload["gate"]["passed"] is True


def test_cli_test_command_rejects_invalid_fail_below_value(tmp_path: Path) -> None:
    suite_dir = tmp_path / "invalid-threshold-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: invalid_threshold_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: hi\nmetadata:\n  mock_response: hi\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--fail-below", "-1"])

    assert result.exit_code == 1
    assert "--fail-below must be between 0 and 100" in result.output


def test_cli_test_command_uses_local_judge_when_requested(tmp_path: Path, monkeypatch) -> None:
    suite_dir = tmp_path / "local-judge-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: local_judge_sample\ninput:\n  question: What is the PTO policy?\ncontext:\n  retrieved_docs:\n    - Contractors do not receive PTO benefits.\nmetadata:\n  mock_response: Contractors do not receive PTO benefits.\nassertions:\n  - no_unsupported_claims\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cli.commands,
        "build_judge_context",
        lambda judge, base_dir=None: JudgeExecutionContext(preferred_backend=judge, default_backend="heuristic", local_backend=FakeLocalJudgeBackend()),
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--judge", "local"])

    assert result.exit_code == 0
    assert "PASS local_judge_sample-" in result.output
    assert "score=1.00 assertions=1/1 methods=local" in result.output


def test_cli_test_command_falls_back_to_heuristic_when_local_judge_unavailable(tmp_path: Path, monkeypatch) -> None:
    suite_dir = tmp_path / "local-fallback-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: local_fallback_sample\ninput:\n  question: What is the PTO policy?\ncontext:\n  retrieved_docs:\n    - Contractors do not receive PTO benefits.\nmetadata:\n  mock_response: Contractors do not receive PTO benefits.\nassertions:\n  - no_unsupported_claims\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        cli.commands,
        "build_judge_context",
        lambda judge, base_dir=None: JudgeExecutionContext(preferred_backend=judge, default_backend="heuristic", local_backend=UnavailableLocalJudgeBackend()),
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--judge", "local"])

    assert result.exit_code == 0
    assert "PASS local_fallback_sample-" in result.output
    assert "score=1.00 assertions=1/1 methods=heuristic" in result.output
    assert "note: no_unsupported_claims fell back to heuristic: local judge unavailable" in result.output


def test_cli_test_command_allows_cloud_selection_for_deterministic_assertions(tmp_path: Path) -> None:
    suite_dir = tmp_path / "cloud-deterministic-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: cloud_deterministic_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: hi\nmetadata:\n  mock_response: hi\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--judge", "cloud"])

    assert result.exit_code == 0
    assert "PASS cloud_deterministic_sample-" in result.output
    assert "score=1.00 assertions=1/1 methods=deterministic" in result.output


def test_cli_test_command_returns_cloud_error_for_hybrid_assertions(tmp_path: Path) -> None:
    suite_dir = tmp_path / "cloud-hybrid-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: cloud_hybrid_sample\ninput:\n  question: What is the PTO policy?\ncontext:\n  retrieved_docs:\n    - Contractors do not receive PTO benefits.\nmetadata:\n  mock_response: Contractors do not receive PTO benefits.\nassertions:\n  - no_unsupported_claims\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--judge", "cloud"])

    assert result.exit_code == 1
    assert "ERROR cloud_hybrid_sample-" in result.output
    assert "score=0.00 assertions=0/1 methods=cloud" in result.output
    assert "- no_unsupported_claims [error] method=cloud confidence=0.000" in result.output
    assert "reason: cloud judge backend is not configured yet" in result.output


def test_cli_test_command_uses_configured_default_backend_when_no_flag_is_provided(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "veritell.toml").write_text(
        "[judge]\ndefault_backend = 'local'\n",
        encoding="utf-8",
    )
    suite_dir = tmp_path / "tests" / "ai"
    suite_dir.mkdir(parents=True)
    (suite_dir / "sample.yaml").write_text(
        "name: configured_default_sample\ninput:\n  question: What is the PTO policy?\ncontext:\n  retrieved_docs:\n    - Contractors do not receive PTO benefits.\nmetadata:\n  mock_response: Contractors do not receive PTO benefits.\nassertions:\n  - no_unsupported_claims\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli.commands,
        "build_judge_context",
        lambda judge, base_dir=None: JudgeExecutionContext(default_backend="local", local_backend=FakeLocalJudgeBackend()),
    )

    result = runner.invoke(cli.app, ["test"])

    assert result.exit_code == 0
    assert "PASS configured_default_sample-" in result.output
    assert "score=1.00 assertions=1/1 methods=local" in result.output


def test_cli_test_command_rejects_invalid_judge_backend(tmp_path: Path) -> None:
    suite_dir = tmp_path / "invalid-judge-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: invalid_judge_sample\ninput:\n  question: hi\ncontext:\n  reference_answer: hi\nmetadata:\n  mock_response: hi\nassertions:\n  - exact_match\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir), "--judge", "bogus"])

    assert result.exit_code == 1
    assert "judge backend must be one of" in result.output


def test_cli_test_command_highlights_unsupported_spans_in_terminal_output(tmp_path: Path) -> None:
    suite_dir = tmp_path / "unsupported-spans-suite"
    suite_dir.mkdir()
    (suite_dir / "sample.yaml").write_text(
        "name: unsupported_spans_sample\ninput:\n  question: What is the refund window?\ncontext:\n  retrieved_docs:\n    - Refunds are allowed within 30 days of purchase.\nmetadata:\n  mock_response: Refunds are allowed within 45 days of purchase.\nassertions:\n  - no_unsupported_claims\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli.app, ["test", str(suite_dir)])

    assert result.exit_code == 1
    assert "FAIL unsupported_spans_sample-" in result.output
    assert "score=0.00 assertions=0/1 methods=heuristic" in result.output
    assert "unsupported spans:" in result.output
    assert '"45"' in result.output
    assert "rationale: numbers not found in matched context: 45" in result.output

