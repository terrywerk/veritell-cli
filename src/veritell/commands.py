"""Thin command delegates for the Veritell CLI shell."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .loader import InvalidTestCaseError, load_test_suite
from .reporters import render_json_report, render_terminal_report
from .runner import run_test_suite


@dataclass(slots=True, frozen=True)
class CommandResult:
    """Structured response returned by CLI delegates."""

    command: str
    message: str
    exit_code: int = 0


class VeritellCLIError(RuntimeError):
    """Raised when a CLI command cannot complete successfully."""


def run_test(path: Path, json_output: bool = False, fail_below: float | None = None) -> CommandResult:
    try:
        cases = load_test_suite(path)
    except InvalidTestCaseError as exc:
        raise VeritellCLIError(str(exc)) from exc

    suite = run_test_suite(cases)
    gate = _build_gate_result(suite.summary.score, fail_below)
    report = render_json_report(path, suite, gate=gate) if json_output else render_terminal_report(path, suite, gate=gate)
    exit_code = 1 if (suite.summary.failed or suite.summary.errors or (gate is not None and not gate["passed"])) else 0
    return CommandResult("test", report, exit_code=exit_code)


def run_scan(path: Path) -> CommandResult:
    return CommandResult("scan", f"Scaffolded scan for {path.as_posix()}")


def run_generate_evals(output: Path) -> CommandResult:
    return CommandResult("generate-evals", f"Scaffolded eval generation into {output.as_posix()}")


def run_import_evals(source: Path) -> CommandResult:
    return CommandResult("import-evals", f"Scaffolded eval import from {source.as_posix()}")


def run_diagnose(target: str) -> CommandResult:
    if not target.strip():
        raise VeritellCLIError("diagnose target cannot be empty")
    return CommandResult("diagnose", f"Scaffolded diagnostics for {target}")


def _build_gate_result(score: float | None, fail_below: float | None) -> dict[str, float | bool] | None:
    if fail_below is None:
        return None
    if not 0 <= fail_below <= 100:
        raise VeritellCLIError("--fail-below must be between 0 and 100")

    percent_score = round((score or 0.0) * 100, 2)
    threshold = round(float(fail_below), 2)
    return {
        "threshold": threshold,
        "score": percent_score,
        "passed": percent_score >= threshold,
    }
