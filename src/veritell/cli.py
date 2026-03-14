"""Command-line entry points for Veritell."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Sequence

import click
import typer
from typer.main import get_command

from . import __version__
from . import commands

app = typer.Typer(
    add_completion=False,
    help="Veritell CLI scaffold for local development.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool | None,
        typer.Option("--version", help="Show the installed Veritell CLI version and exit.", callback=_version_callback),
    ] = None,
) -> None:
    """Run the Veritell CLI."""


def _emit_result(result: commands.CommandResult) -> None:
    typer.echo(result.message)


def _run(result: commands.CommandResult) -> None:
    _emit_result(result)
    if result.exit_code:
        raise typer.Exit(code=result.exit_code)


def _run_delegate(delegate_factory, *args: object) -> None:
    try:
        _run(delegate_factory(*args))
    except commands.VeritellCLIError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command("test")
def test_command(
    path: Annotated[Path, typer.Argument(help="Path to a test file or suite directory.")] = Path("tests/ai"),
    json_output: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON output.")] = False,
    fail_below: Annotated[
        float | None,
        typer.Option("--fail-below", help="Exit non-zero when the suite score is below this 0-100 threshold."),
    ] = None,
) -> None:
    """Run a Veritell test suite."""

    _run_delegate(commands.run_test, path, json_output, fail_below)


@app.command("scan")
def scan_command(
    path: Annotated[Path, typer.Argument(help="Path to inspect for AI-system components.")] = Path("."),
) -> None:
    """Scan a project for AI-system components."""

    _run_delegate(commands.run_scan, path)


@app.command("generate-evals")
def generate_evals_command(
    output: Annotated[Path, typer.Option("--output", help="Directory where generated evals should be written.")] = Path("tests/generated"),
) -> None:
    """Generate starter evaluation cases."""

    _run_delegate(commands.run_generate_evals, output)


@app.command("import-evals")
def import_evals_command(
    source: Annotated[Path, typer.Option("--source", help="Path to an external eval dataset.")] = Path("imports/evals.jsonl"),
) -> None:
    """Import evaluation cases from an external dataset."""

    _run_delegate(commands.run_import_evals, source)


@app.command("diagnose")
def diagnose_command(
    target: Annotated[str, typer.Argument(help="Suite, test, or run identifier to diagnose.")] = "latest",
) -> None:
    """Diagnose failures from a Veritell run."""

    _run_delegate(commands.run_diagnose, target)


def main(argv: Sequence[str] | None = None) -> int:
    command = get_command(app)
    try:
        command.main(args=list(argv) if argv is not None else None, prog_name="veritell", standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except click.exceptions.Exit as exc:
        return int(exc.exit_code)
    return 0
