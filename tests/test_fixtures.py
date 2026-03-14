"""Smoke tests for shipped example fixtures."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from veritell import cli
from veritell.loader import discover_test_files, load_test_suite
from veritell.runner import run_test_suite

FIXTURES_DIR = Path(__file__).resolve().parent / "ai" / "fixtures"
runner = CliRunner()


def test_example_fixtures_are_discoverable() -> None:
    files = discover_test_files(FIXTURES_DIR)

    assert [path.name for path in files] == [
        "abstention.yaml",
        "grounded_rag.yaml",
        "structured_output.yaml",
    ]



def test_example_fixture_suite_loads_supported_tests_only() -> None:
    suite = load_test_suite(FIXTURES_DIR)

    assert [case.name for case in suite] == [
        "abstention_unknown_policy_year",
        "grounded_rag_contractors_pto",
        "structured_output_refund_policy",
    ]



def test_example_fixture_suite_runs_successfully_from_repo_root(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)

    suite = load_test_suite(FIXTURES_DIR)
    result = run_test_suite(suite)

    assert result.summary.total == 3
    assert result.summary.passed == 3
    assert result.summary.failed == 0
    assert result.summary.errors == 0



def test_cli_can_run_shipped_fixture_directory(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli.app, ["test", "tests/ai/fixtures/"])

    assert result.exit_code == 0
    assert "Suite: tests/ai/fixtures" in result.output
    assert "Summary: total=3 passed=3 failed=0 errors=0 skipped=0 score=1.00" in result.output
