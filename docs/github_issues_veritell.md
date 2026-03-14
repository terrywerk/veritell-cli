
# Veritell Initial Development Issues

Copy-paste these into GitHub issues or import into a project board.

---

## Issue 1 — Scaffold Veritell project structure

**Goal**  
Create the base Python package and folders.

**Tasks**
- Create `src/veritell/`
- Create modules:
  - `cli`
  - `models`
  - `testcase`
  - `runner`
  - `assertions`
  - `backends`
  - `diagnostics`
  - `scoring`
- Create `tests/` folder
- Create `docs/` folder
- Ensure package installs locally

**Acceptance Criteria**
- `pip install -e .` works
- Project imports without errors

---

## Issue 2 — Add Typer-based CLI shell

**Goal**  
Create the initial CLI entrypoint.

**Tasks**
- Implement CLI using Typer
- Add commands:
  - `test`
  - `scan`
  - `generate-evals`
  - `import-evals`
  - `diagnose`

**Acceptance Criteria**
- `veritell --help` works
- CLI exits non-zero on failure

---

## Issue 3 — Implement core data models

**Goal**  
Add canonical internal objects.

**Tasks**
- Create `VeritellTestCase`
- Create `AssertionResult`
- Create `VeritellTestResult`

**Acceptance Criteria**
- Models are serializable
- Models validated with type hints or Pydantic

---

## Issue 4 — Implement YAML/JSON test loader

**Goal**  
Load test cases from files into canonical models.

**Tasks**
- Support `tests/ai/*.yaml`
- Support `*.yml`
- Support `*.json`
- Validate schema from `TEST_CASE_SCHEMA.md`

**Acceptance Criteria**
- Loader returns normalized `VeritellTestCase`
- Clear errors for invalid tests

---

## Issue 5 — Add test suite discovery

**Goal**  
Automatically find test files.

**Tasks**
- Default test path: `tests/ai/`
- Allow custom path: `veritell test tests/ai/`
- Ignore unsupported files

**Acceptance Criteria**
- Error if no tests found
- Tests load correctly

---

## Issue 6 — Implement runner skeleton

**Goal**  
Orchestrate test execution.

**Tasks**
- Iterate through test cases
- Execute assertions
- Collect results

**Acceptance Criteria**
- Runner returns summary
- Pass/fail counts calculated

---

## Issue 7 — Implement Assertion base class

**Goal**  
Define assertion plugin contract.

**Tasks**
- Create `Assertion` interface
- Implement registry to resolve assertions by type

**Acceptance Criteria**
- Assertions can be dynamically registered
- Assertions return `AssertionResult`

---

## Issue 8 — Implement first deterministic assertions

**Goal**  
Ship the first useful reliability checks.

**Assertions**
- `response_format_valid`
- `json_schema_valid`
- `expected_doc_retrieved`
- `retrieval_contains_answer`

**Acceptance Criteria**
- Assertions return structured results
- Unit tests cover pass/fail cases

---

## Issue 9 — Implement heuristic hallucination detector

**Goal**  
Provide offline hallucination detection.

**Assertion**
- `no_unsupported_claims`

**Acceptance Criteria**
- Detects unsupported spans between answer and context
- Returns `method="heuristic"`
- Confidence score included

---

## Issue 10 — Implement reporters

**Goal**  
Display results in terminal and machine-readable formats.

**Tasks**
- Terminal summary output
- JSON reporter with `--json` flag

**Acceptance Criteria**
- Includes per-test assertion results
- Includes suite summary

---

## Issue 11 — Implement CI gating

**Goal**  
Allow teams to block deployment if reliability score too low.

**Command**

```
veritell test --fail-below 80
```

**Acceptance Criteria**
- Non-zero exit if below threshold
- Error message shows threshold and score

---

## Issue 12 — Add example test fixtures

**Goal**  
Provide runnable examples.

**Examples**
- Grounded RAG test
- Abstention test
- Structured output test

**Acceptance Criteria**
- Example tests located under `tests/ai/fixtures/`
- README shows how to run `veritell test`
