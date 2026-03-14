"""Smoke tests for the runnable demo suite under examples/."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from veritell import cli
from veritell.loader import discover_test_files, load_test_suite
from veritell.runner import run_test_suite

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
runner = CliRunner()



def test_demo_examples_are_discoverable() -> None:
    files = discover_test_files(EXAMPLES_DIR)

    assert [path.name for path in files] == [
        "abstention.yaml",
        "grounded_rag.yaml",
        "hallucination_failure.yaml",
        "structured_output.yaml",
    ]



def test_demo_example_suite_loads_supported_tests_only() -> None:
    suite = load_test_suite(EXAMPLES_DIR)

    assert [case.name for case in suite] == [
        "demo_abstention_unknown_policy_year",
        "demo_grounded_rag_contractors_pto",
        "demo_hallucination_failure_refund_window",
        "demo_structured_output_refund_policy",
    ]



def test_demo_example_suite_contains_three_passes_and_one_failure_from_repo_root(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)

    suite = load_test_suite(EXAMPLES_DIR)
    result = run_test_suite(suite)

    assert result.summary.total == 4
    assert result.summary.passed == 3
    assert result.summary.failed == 1
    assert result.summary.errors == 0
    assert result.summary.score == 0.75



def test_cli_can_run_demo_example_directory_and_surface_the_intentional_failure(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli.app, ["test", "examples/"])

    assert result.exit_code == 1
    assert "Suite: examples" in result.output
    assert "PASS demo_grounded_rag_contractors_pto-" in result.output
    assert "FAIL demo_hallucination_failure_refund_window-" in result.output
    assert "Summary: total=4 passed=3 failed=1 errors=0 skipped=0 reliability=75.00% score=0.75" in result.output



def test_cli_ci_gating_demo_fails_for_hallucination_example(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(repo_root)

    result = runner.invoke(cli.app, ["test", "examples/hallucination_failure.yaml", "--fail-below", "80"])

    assert result.exit_code == 1
    assert "FAIL demo_hallucination_failure_refund_window-" in result.output
    assert "Gate: threshold=80.00 score=0.00 passed=false" in result.output

