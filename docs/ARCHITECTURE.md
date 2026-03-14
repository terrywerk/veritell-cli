# Veritell Architecture

## Purpose

This document defines the reference architecture for Veritell as an **AI reliability test framework** with optional cloud diagnostics.

Core principle:

```text
test case -> runner -> assertions -> results -> diagnostics
```

Veritell should be built as a **test-case-first system**, not a dashboard-first or trace-first system.

---

## Reference Architecture

```text
                         ┌──────────────────────────────┐
                         │      User AI Application     │
                         │  (RAG app, agent, chatbot)   │
                         └──────────────┬───────────────┘
                                        │
                                        │ prompts / context / outputs
                                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                           Veritell Python Package                         │
│                                                                            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │ CLI / pytest │──▶│ Test Loader  │──▶│ Test Runner  │──▶│  Scoring    │  │
│  │ plugin       │   │ YAML / JSON  │   │ orchestration│   │  & Summary  │  │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬──────┘  │
│         │                  │                  │                  │          │
│         │                  │                  ▼                  │          │
│         │                  │         ┌───────────────┐           │          │
│         │                  └────────▶│ Assertion     │◀──────────┘          │
│         │                            │ Engine        │                      │
│         │                            └──────┬────────┘                      │
│         │                                   │                               │
│         │          ┌────────────────────────┼────────────────────────┐      │
│         │          │                        │                        │      │
│         ▼          ▼                        ▼                        ▼      │
│   ┌────────────┐ ┌──────────────┐   ┌──────────────┐        ┌────────────┐ │
│   │ Scanner    │ │ Retrieval    │   │ Judge        │        │ Diagnostics│ │
│   │ framework  │ │ analyzers    │   │ backends     │        │ engine     │ │
│   │ detection  │ │ + gold docs  │   │ heuristic/   │        │ root cause │ │
│   └────────────┘ └──────────────┘   │ local/cloud  │        └────────────┘ │
│                                      └──────────────┘                        │
│                                                                            │
│  Outputs:                                                                  │
│  - test results                                                            │
│  - assertion results                                                       │
│  - reliability score                                                       │
│  - failure taxonomy                                                        │
│  - optional upload bundle                                                  │
└────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ optional upload
                                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                             Veritell.ai Cloud                             │
│                                                                            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │ Ingestion    │──▶│ Storage      │──▶│ Advanced     │──▶│ Dashboards  │  │
│  │ API          │   │ runs/results │   │ diagnostics  │   │ reports     │  │
│  └──────────────┘   └──────────────┘   └──────────────┘   └─────────────┘  │
│                                                                            │
│  Also provides:                                                            │
│  - cloud judges                                                            │
│  - trend analysis                                                          │
│  - benchmarking                                                            │
│  - enterprise reporting                                                    │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Design Rules

1. The local package must remain useful without the cloud.
2. All execution should normalize into canonical test cases and results.
3. Assertions are the main unit of reliability logic.
4. Diagnostics explain failed assertions; they should not bypass them.
5. Cloud capabilities are additive, not required.
6. Integrations should be adapters, not hard dependencies.
7. The system should be CI-friendly and deterministic where possible.

---

## Core Modules

### 1. CLI / Pytest Plugin

Developer entry point.

Responsibilities:
- `veritell test`
- `veritell scan`
- `veritell generate-evals`
- `veritell import-evals`
- `veritell diagnose`

Guideline:
Keep this layer thin. It should mostly parse input and delegate to services.

---

### 2. Test Loader

Loads test definitions from:
- YAML
- JSON
- imported eval datasets

Responsibilities:
- parse files
- validate schema
- normalize into `VeritellTestCase`

---

### 3. Test Runner

The orchestrator.

Responsibilities:
- iterate over test cases
- call target systems or adapters
- execute assertions
- collect assertion results
- compute suite status

---

### 4. Assertion Engine

Core reliability layer.

Responsibilities:
- resolve assertions
- choose backend per assertion
- execute checks
- return structured assertion results

Example assertions:
- `expected_doc_retrieved`
- `retrieval_contains_answer`
- `no_unsupported_claims`
- `should_abstain`
- `json_schema_valid`

---

### 5. Judge Backends

Evaluation backends used by assertions.

Supported backend types:
- `heuristic`
- `local`
- `cloud`

Responsibilities:
- enable offline operation
- allow local model judging
- support advanced cloud diagnostics

---

### 6. Diagnostics Engine

Runs after assertions fail.

Responsibilities:
- classify failures into taxonomy
- recommend fixes
- aggregate evidence
- explain root cause

Example taxonomy:
- unsupported claim
- retrieval miss
- bad transformation
- missing abstention

---

### 7. Cloud Layer

Optional intelligence layer.

Responsibilities:
- ingest uploaded runs
- store results
- run advanced diagnostics
- provide dashboards and reports
- benchmark across systems
- support enterprise workflows

---

## Internal Data Model

These three objects should remain stable across the system.

### VeritellTestCase

```python
class VeritellTestCase:
    id: str
    name: str
    input: dict
    context: dict
    assertions: list
    metadata: dict
```

### AssertionResult

```python
class AssertionResult:
    assertion: str
    status: str
    method: str
    confidence: float | None
    details: dict
```

### VeritellTestResult

```python
class VeritellTestResult:
    test_id: str
    status: str
    assertion_results: list[AssertionResult]
    score: float | None
    diagnosis: dict | None
```

---

## Recommended Repo Structure

```text
src/veritell/
  cli/
  testcase/
  runner/
  assertions/
  backends/
  diagnostics/
  scanner/
  scoring/
  reports/
  integrations/
  models/

tests/
docs/
```

---

## Execution Flow

### `veritell test`

```text
1. CLI parses command
2. Test Loader reads tests/ai/*.yaml
3. Loader creates VeritellTestCase objects
4. Runner invokes target system / adapter
5. Assertion Engine executes all assertions
6. Scoring computes per-test and suite score
7. Diagnostics runs on failures
8. Reporter prints terminal / JSON output
9. Optional uploader sends bundle to cloud
```

---

## Assertion Backend Strategy

Assertions should support one or more of these backends:

- `heuristic`
- `local`
- `cloud`

Product rule:
- deterministic assertions always run locally
- hybrid assertions fall back to heuristics
- local/cloud judges upgrade quality when available

Example:

```yaml
assertions:
  - type: expected_doc_retrieved
  - type: retrieval_contains_answer
  - type: no_unsupported_claims
    backend: heuristic
  - type: should_answer
    backend: local
```

---

## What Not To Do

Avoid these early mistakes:

### Do not make the cloud required
This will hurt adoption and CI usability.

### Do not couple assertions directly to LangChain
Use adapters and keep the framework app-agnostic.

### Do not start with dashboards
Build the local runner first.

### Do not store everything as raw traces
Normalize into test cases and results.

### Do not let diagnostics bypass assertions
Diagnostics should explain failures, not create a separate evaluation path.

---

## MVP Vertical Slice

Build this first:

```text
YAML test case
-> veritell test
-> runner
-> deterministic assertions
-> heuristic no_unsupported_claims
-> terminal output
-> JSON output
```

Then add, in order:
1. local judge backend
2. cloud upload
3. diagnostics engine
4. integrations
5. dashboards

---

## Final Mental Model

Veritell is:

```text
AI test runner + assertion library + diagnostics engine
```

Or:

```text
pytest + mypy + sentry
for AI systems
```
