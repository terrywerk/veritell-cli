# TEST_CASE_SCHEMA.md

## Purpose

This document defines the canonical schema for Veritell AI test cases.

A test case is the fundamental unit of reliability validation in Veritell.
All YAML, JSON, generated evals, and imported datasets should normalize into this schema.

Core principle:

```text
external input -> normalized VeritellTestCase -> runner -> assertions -> results
```

---

## File Locations

Recommended default locations:

```text
tests/ai/*.yaml
tests/ai/*.yml
tests/ai/*.json
```

Imported datasets may be stored in:

```text
.veritell/imported_evals.json
.veritell/generated_evals.json
```

---

## Canonical Test Case Shape

Every test case must normalize into this structure.

```yaml
name: contractor_policy_grounding

description: Ensure contractor PTO answers stay grounded in retrieved policy documents

input:
  question: "How much PTO do contractors get?"

context:
  retrieved_docs:
    - contractor_policy_v2.txt

assertions:
  - type: expected_doc_retrieved
  - type: retrieval_contains_answer
  - type: no_unsupported_claims
    backend: heuristic
  - type: should_answer
    backend: local

metadata:
  tags:
    - rag
    - grounding
  severity: medium
  owner: platform-team
```

---

## Required Top-Level Fields

| Field | Type | Required | Description |
|---|---|---:|---|
| `name` | string | yes | Unique, human-readable test name |
| `input` | object | yes | Prompt or request payload sent to target system |
| `assertions` | array | yes | Assertions to execute |
| `context` | object | no | Retrieval docs, expected docs, system context |
| `description` | string | no | Human-readable explanation |
| `metadata` | object | no | Tags, severity, ownership, custom fields |

---

## Field Definitions

### `name`

Requirements:
- must be a non-empty string
- should be unique within a test suite
- should be filesystem-safe when possible

Examples:

```yaml
name: contractor_policy_grounding
name: should_abstain_on_unknown_policy_year
```

---

### `description`

Optional free-text explanation of the test's intent.

Example:

```yaml
description: Verify the model abstains when the requested policy year is not present
```

---

### `input`

Defines the request sent to the target system.

Minimum supported schema:

```yaml
input:
  question: "How much PTO do contractors get?"
```

Extended examples:

```yaml
input:
  question: "Summarize the refund policy"
  conversation_history:
    - role: user
      content: "I bought a subscription last week"
  variables:
    locale: en-US
```

Rules:
- `input` must be an object
- `input.question` is strongly recommended for QA/RAG systems
- additional fields are allowed for app-specific adapters

---

### `context`

Optional supporting context for evaluation.

Supported fields:

| Field | Type | Required | Description |
|---|---|---:|---|
| `retrieved_docs` | array[string or object] | no | Docs/chunks returned by retrieval |
| `expected_docs` | array[string] | no | Gold docs expected to appear in retrieval |
| `reference_answer` | string | no | Gold answer for comparison |
| `citations` | array | no | Expected citations |
| `system_prompt` | string | no | Optional system prompt for analysis |

Example:

```yaml
context:
  retrieved_docs:
    - contractor_policy_v2.txt
  expected_docs:
    - contractor_policy_v2.txt
  reference_answer: "Contractors do not receive PTO benefits."
```

Rules:
- `context` must be an object when present
- `retrieved_docs` may contain identifiers, file paths, or structured objects
- loaders should normalize document objects where possible

---

### `assertions`

Array of assertion definitions.

Minimum example:

```yaml
assertions:
  - type: no_unsupported_claims
```

Expanded example:

```yaml
assertions:
  - type: expected_doc_retrieved
  - type: retrieval_contains_answer
    params:
      min_overlap: 0.7
  - type: no_unsupported_claims
    backend: heuristic
  - type: should_answer
    backend: local
```

Rules:
- must be a non-empty array
- each assertion must have a `type`
- `backend` is optional
- `params` is optional and assertion-specific

Assertion item schema:

| Field | Type | Required | Description |
|---|---|---:|---|
| `type` | string | yes | Assertion identifier |
| `backend` | string | no | `heuristic`, `local`, or `cloud` |
| `params` | object | no | Assertion-specific configuration |

---

### `metadata`

Optional metadata for reporting and filtering.

Supported example fields:

```yaml
metadata:
  tags:
    - rag
    - grounding
  severity: high
  owner: platform-team
  component: policy-bot
```

Recommended metadata fields:

| Field | Type | Description |
|---|---|---|
| `tags` | array[string] | Labels for grouping/filtering |
| `severity` | string | low / medium / high / critical |
| `owner` | string | Responsible team or engineer |
| `component` | string | App module or bot name |

Rules:
- arbitrary metadata keys are allowed
- core runner should preserve unknown metadata

---

## JSON Schema-Friendly Canonical Shape

```json
{
  "name": "contractor_policy_grounding",
  "description": "Ensure contractor PTO answers stay grounded",
  "input": {
    "question": "How much PTO do contractors get?"
  },
  "context": {
    "retrieved_docs": ["contractor_policy_v2.txt"],
    "expected_docs": ["contractor_policy_v2.txt"],
    "reference_answer": "Contractors do not receive PTO benefits."
  },
  "assertions": [
    { "type": "expected_doc_retrieved" },
    { "type": "retrieval_contains_answer" },
    { "type": "no_unsupported_claims", "backend": "heuristic" }
  ],
  "metadata": {
    "tags": ["rag", "grounding"],
    "severity": "medium"
  }
}
```

---

## Validation Rules

The loader should reject a test case when:

- `name` is missing or empty
- `input` is missing or not an object
- `assertions` is missing or empty
- any assertion is missing `type`
- `backend` is not one of:
  - `heuristic`
  - `local`
  - `cloud`

The loader should warn, but not fail, when:

- `name` is duplicated in the same suite
- `input.question` is missing
- `metadata.severity` is outside recommended values
- unsupported metadata fields are present

---

## Normalization Rules

All inputs must be normalized into a `VeritellTestCase`.

Normalization behavior:

1. Convert YAML or JSON into dict form
2. Fill missing optional blocks with empty objects where appropriate
3. Normalize assertion objects
4. Preserve metadata
5. Generate a stable internal `id` if not present externally

Suggested internal model:

```python
class VeritellTestCase:
    id: str
    name: str
    description: str | None
    input: dict
    context: dict
    assertions: list[dict]
    metadata: dict
```

---

## Imported Dataset Mapping

External datasets should map into the canonical format.

### Minimal import mapping

Input dataset:

```json
{
  "question": "What is the PTO policy for contractors?",
  "expected_answer": "Contractors do not receive PTO benefits."
}
```

Normalized test case:

```json
{
  "name": "imported_test_001",
  "input": {
    "question": "What is the PTO policy for contractors?"
  },
  "context": {
    "reference_answer": "Contractors do not receive PTO benefits."
  },
  "assertions": [
    { "type": "answer_correctness", "backend": "local" }
  ],
  "metadata": {
    "source": "import"
  }
}
```

---

## Example Test Cases

### 1. Grounded RAG answer

```yaml
name: contractor_policy_grounding

input:
  question: "How much PTO do contractors get?"

context:
  retrieved_docs:
    - contractor_policy_v2.txt
  expected_docs:
    - contractor_policy_v2.txt

assertions:
  - type: expected_doc_retrieved
  - type: retrieval_contains_answer
  - type: no_unsupported_claims
```

### 2. Abstention case

```yaml
name: unknown_policy_year_should_abstain

input:
  question: "What was the contractor PTO policy in 2003?"

context:
  retrieved_docs: []

assertions:
  - type: should_abstain
  - type: no_unsupported_claims
```

### 3. Structured output case

```yaml
name: refund_policy_json_output

input:
  question: "Return the refund policy as JSON"

assertions:
  - type: response_format_valid
  - type: json_schema_valid
    params:
      schema_ref: refund_policy_schema.json
```

---

## Versioning

Add optional schema versioning support for future compatibility.

Example:

```yaml
schema_version: v1
name: contractor_policy_grounding
input:
  question: "How much PTO do contractors get?"
assertions:
  - type: no_unsupported_claims
```

Recommended behavior:
- default to `v1` if omitted
- reject unknown future versions unless explicitly supported

---

## Design Principles

The schema must be:

- simple enough to hand-author
- strict enough for CI
- extensible for future assertions
- stable across CLI, API, and cloud
- compatible with imported datasets

---

## Long-Term Goal

Developers should be able to create AI tests as naturally as software tests.

Example:

```text
tests/ai/policy_grounding.yaml
tests/ai/abstention_unknown_year.yaml
tests/ai/refund_json_output.yaml
```

Then run:

```bash
veritell test
```
