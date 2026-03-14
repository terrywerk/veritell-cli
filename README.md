# veritell-cli

Standalone Python CLI scaffold for Veritell.

## Project layout

- `src/veritell/` — package source
- `tests/` — smoke tests for install/import/CLI behavior
- `docs/` — package notes and future design docs

## Canonical models

Issue 3 adds the first canonical internal objects as validated Pydantic models:

- `VeritellTestCase`
- `AssertionResult`
- `VeritellTestResult`
- `VeritellRunSummary`
- `VeritellSuiteResult`

These models provide built-in validation plus JSON/dict serialization helpers for loader, runner, and reporting work.

## Assertion plugins

Issue 7 adds the assertion plugin contract and registry, and Issue 8 ships the first deterministic assertions.

Public assertion API:

- `Assertion`
- `register_assertion(...)`
- `unregister_assertion(...)`
- `get_assertion(...)`
- `list_assertions()`
- `evaluate_registered_assertion(...)`

Built-in deterministic assertions now include:

- `response_format_valid`
- `json_schema_valid`
- `expected_doc_retrieved`
- `retrieval_contains_answer`
- `exact_match`
- `exact_match_answer`

Built-in heuristic assertions now include:

- `no_unsupported_claims`

Built-in scaffold assertions are registered on import and the runner now resolves each test-case assertion by `type` through the registry. Unsupported assertions return structured `AssertionResult` objects with `status="skip"` instead of crashing the run.

## Test loading, discovery, and execution

Veritell now supports explicit file loading, suite discovery, and runner execution.

Supported test definitions:

- `tests/ai/*.yaml`
- `tests/ai/*.yml`
- `tests/ai/*.json`

Current loader API:

- `veritell.load_test_case(path)`
- `veritell.load_test_cases([...])`
- `veritell.discover_test_files(path="tests/ai")`
- `veritell.load_test_suite(path="tests/ai")`

Discovery rules:

- `veritell test` defaults to `tests/ai/`
- `veritell test tests/ai/` allows a custom suite path
- unsupported files are ignored
- an `InvalidTestCaseError` is raised when no supported test files are found or a supported file is invalid

Runner behavior in the current scaffold:

- iterates through normalized test cases
- resolves assertions through the registry
- collects `AssertionResult` entries into `VeritellTestResult`
- computes suite totals and pass/fail/error/skip counts in `VeritellRunSummary`

The loader validates the schema rules from `docs/TEST_CASE_SCHEMA.md`, fills optional blocks like `context` and `metadata`, normalizes assertion strings into objects, and raises clear file-aware errors when a test file is invalid.

## Reporting

Issue 10 adds two reporting modes on top of the suite runner:

- terminal output by default
- machine-readable JSON via `veritell test --json`

Both formats include:

- per-test results
- per-test assertion results
- suite summary totals

Issue 11 adds CI gating via a score threshold:

- `veritell test --fail-below 80`
- `veritell test --json --fail-below 80`

The threshold is expressed on a `0-100` scale. When the suite score falls below that threshold, the command exits non-zero and includes gate metadata with both the threshold and actual score.

Examples:

```powershell
veritell test
veritell test --json
veritell test --fail-below 80
veritell test tests/ai/ --json --fail-below 80
veritell test tests/ai/fixtures/
```

## CLI shell

The initial Typer-based CLI exposes the Phase 1 command shell described in the project docs:

- `veritell test`
- `veritell scan`
- `veritell generate-evals`
- `veritell import-evals`
- `veritell diagnose`

For now, the CLI stays intentionally thin and delegates to scaffold handlers, but `veritell test` now executes a discovered suite and prints a summary like `1 passed, 0 failed, 0 errors, 0 skipped`.

## Local development

### Editable install

```powershell
python -m pip install -e .[dev]
```

### Smoke checks

```powershell
veritell --help
python -m veritell --help
python -m pytest
```

After you add a suite under `tests/ai/`, you can run:

```powershell
veritell test
veritell test tests/ai/
```

The repository also ships runnable examples under `tests/ai/fixtures/`:

- `grounded_rag.yaml`
- `abstention.yaml`
- `structured_output.yaml`

### What each fixture demonstrates

- `grounded_rag.yaml`
  - grounded RAG validation
  - assertions: `expected_doc_retrieved`, `retrieval_contains_answer`, `no_unsupported_claims`
- `abstention.yaml`
  - refusal/abstention when the evidence is missing
  - assertions: `should_abstain`, `no_unsupported_claims`
- `structured_output.yaml`
  - JSON formatting and schema validation
  - assertions: `response_format_valid`, `json_schema_valid`
  - schema file: `tests/ai/fixtures/refund_policy_schema.json`

From the repo root, you can run the full example directory with:

```powershell
veritell test tests/ai/fixtures/
veritell test tests/ai/fixtures/ --json
veritell test tests/ai/fixtures/ --fail-below 80
```

You can also run a single example file:

```powershell
veritell test tests/ai/fixtures/grounded_rag.yaml
veritell test tests/ai/fixtures/abstention.yaml
veritell test tests/ai/fixtures/structured_output.yaml --json
```

Typical terminal output includes:

- one section per test
- per-assertion status, method, and confidence
- a suite summary line
- optional CI gate metadata when `--fail-below` is used

For a slightly longer walkthrough, see `docs/examples.md`.

## Current scope

This scaffold keeps imports lightweight and side-effect free while establishing the initial command surface, canonical model layer, loader/discovery flow, runner summary foundation, and assertion plugin contract for deterministic assertions and future diagnostics work.
