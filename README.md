# veritell-cli

Standalone Python CLI scaffold for Veritell.

## Project layout

- `src/veritell/` — package source
- `tests/` — smoke tests for install/import/CLI behavior
- `examples/` — runnable demo suite for CLI walkthroughs and CI gating demos
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

`no_unsupported_claims` now reports explainable unsupported text segments, per-span rationale, confidence, and the best matching context/reference span in failure details.

Hybrid assertions can also use a selectable backend hierarchy:

- assertion-level `backend` override
- CLI `--judge heuristic|local|cloud`
- configured default backend

When the local judge is unavailable, supported hybrid assertions fall back to heuristics and include a clear note in terminal output and JSON details.

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

Issue 13 adds a local judge backend for hybrid assertions:

- `veritell test --judge local`
- `veritell test examples/grounded_rag.yaml --judge local --json`

Issue 15 adds backend selection hierarchy for hybrid and judge-based assertions:

- `veritell test --judge heuristic`
- `veritell test --judge local`
- `veritell test --judge cloud`

Examples:

```powershell
veritell test
veritell test --json
veritell test --fail-below 80
veritell test --judge heuristic
veritell test --judge local
veritell test --judge cloud
veritell test tests/ai/ --json --fail-below 80
veritell test examples/
```

## Backend selection hierarchy

Backend resolution follows this order:

1. assertion-level `backend`
2. CLI `--judge`
3. configured default backend
4. built-in fallback to `heuristic`

Deterministic assertions ignore CLI/default judge selection and continue running with their deterministic behavior.

Hybrid assertions such as `no_unsupported_claims` switch according to the selected backend.

## Local judge backend

The local judge path is designed for offline local-model tools such as Ollama.

### CLI usage

```powershell
veritell test --judge heuristic
veritell test --judge local
veritell test --judge cloud
veritell test examples/grounded_rag.yaml --judge local
veritell test examples/grounded_rag.yaml --judge local --json
```

### Default backend via env

```powershell
$env:VERITELL_DEFAULT_JUDGE = "local"
$env:VERITELL_LOCAL_JUDGE_MODEL = "llama3.1:8b"
$env:VERITELL_LOCAL_JUDGE_URL = "http://127.0.0.1:11434"
veritell test
```

Supported backend selection environment variables:

- `VERITELL_DEFAULT_JUDGE`
- `VERITELL_JUDGE_BACKEND`

Supported local-judge environment variables:

- `VERITELL_LOCAL_JUDGE_MODEL`
- `VERITELL_JUDGE_MODEL`
- `OLLAMA_MODEL`
- `VERITELL_LOCAL_JUDGE_URL`
- `VERITELL_LOCAL_JUDGE_TIMEOUT`

### Default backend via config

You can create `veritell.toml` in the repository root:

```toml
[judge]
default_backend = "local"

[local_judge]
model = "llama3.1:8b"
base_url = "http://127.0.0.1:11434"
timeout_seconds = 20
```

Or add the same settings to `pyproject.toml`:

```toml
[tool.veritell.judge]
default_backend = "local"

[tool.veritell.local_judge]
model = "llama3.1:8b"
base_url = "http://127.0.0.1:11434"
timeout_seconds = 20
```

Configuration precedence is:

- assertion-level `backend`
- CLI backend selection (`--judge ...`)
- default backend from env/config
- built-in defaults

If the local judge is unavailable, hybrid assertions such as `no_unsupported_claims` fall back to heuristics automatically. If `cloud` is selected before a cloud backend is configured, hybrid assertions return a clear `method="cloud"` error result instead of silently changing backend.

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

The repository also ships a runnable demo suite under `examples/`:

- `grounded_rag.yaml`
- `abstention.yaml`
- `structured_output.yaml`
- `hallucination_failure.yaml`

### What each demo demonstrates

- `grounded_rag.yaml`
  - grounded RAG validation
  - assertions: `expected_doc_retrieved`, `retrieval_contains_answer`, `no_unsupported_claims`
- `abstention.yaml`
  - refusal/abstention when evidence is missing
  - assertions: `should_abstain`, `no_unsupported_claims`
- `structured_output.yaml`
  - JSON formatting and schema validation
  - assertions: `response_format_valid`, `json_schema_valid`
  - schema file: `examples/refund_policy_schema.json`
- `hallucination_failure.yaml`
  - intentional hallucination failure
  - assertion: `no_unsupported_claims`
  - demonstrates unsupported span highlighting plus CI gating

From the repo root, you can run the full demo directory with:

```powershell
veritell test examples/
veritell test examples/ --json
```

The full demo suite includes one intentional failure (`hallucination_failure.yaml`), so it exits non-zero by design. That makes it useful for demos and CI gating walkthroughs.

You can also run a single example file:

```powershell
veritell test examples/grounded_rag.yaml
veritell test examples/abstention.yaml
veritell test examples/structured_output.yaml --json
veritell test examples/hallucination_failure.yaml
```

CI gating examples:

```powershell
veritell test examples/grounded_rag.yaml --fail-below 80
veritell test examples/hallucination_failure.yaml --fail-below 80
```

Typical terminal output includes:

- one summary line per test
- failure-only assertion detail blocks
- unsupported span highlights when present
- a suite reliability line
- optional CI gate metadata when `--fail-below` is used

For a slightly longer walkthrough, see `examples/README.md` and `docs/examples.md`.

## Current scope

This scaffold keeps imports lightweight and side-effect free while establishing the initial command surface, canonical model layer, loader/discovery flow, runner summary foundation, and assertion plugin contract for deterministic assertions and future diagnostics work.
