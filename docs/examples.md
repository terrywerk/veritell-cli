# Example Fixtures

Veritell ships a runnable demo suite under `examples/`.

These examples are designed to run locally without external services. Each one includes a `metadata.mock_response` value so `veritell test` can execute the suite immediately from a fresh checkout.

## Included fixtures

### `grounded_rag.yaml`

Purpose:
- demonstrate grounded retrieval-style validation

Assertions used:
- `expected_doc_retrieved`
- `retrieval_contains_answer`
- `no_unsupported_claims`

What it checks:
- the expected evidence appears in retrieval
- the retrieved context contains the reference answer
- the response does not introduce unsupported claims

### `abstention.yaml`

Purpose:
- demonstrate abstention when evidence is missing

Assertions used:
- `should_abstain`
- `no_unsupported_claims`

What it checks:
- the model refuses instead of inventing a policy year that is not supported by context
- the abstaining response stays grounded in the available evidence

### `structured_output.yaml`

Purpose:
- demonstrate structured JSON output validation

Assertions used:
- `response_format_valid`
- `json_schema_valid`

Supporting file:
- `refund_policy_schema.json`

What it checks:
- the response is valid JSON
- the JSON matches the required output schema

### `hallucination_failure.yaml`

Purpose:
- demonstrate an intentional hallucination failure

Assertions used:
- `no_unsupported_claims`

What it checks:
- unsupported spans are highlighted when the response contradicts the documented refund window
- CI gating can fail on a low-reliability example

## Run the examples

From the repository root:

```powershell
veritell test examples/
veritell test examples/ --json
```

The full demo suite includes one intentional failing example, so the directory-level run exits non-zero by design.

Run a single example file:

```powershell
veritell test examples/grounded_rag.yaml
veritell test examples/abstention.yaml
veritell test examples/structured_output.yaml --json
veritell test examples/hallucination_failure.yaml
```

## Expected output

### Terminal mode

Run:

```powershell
veritell test examples/grounded_rag.yaml
```

Key lines:

```text
Suite: examples/grounded_rag.yaml
PASS demo_grounded_rag_contractors_pto-<generated-id> score=1.00 assertions=3/3 methods=deterministic,heuristic
Summary: total=1 passed=1 failed=0 errors=0 skipped=0 reliability=100.00% score=1.00
```

Notes:

- fixture-derived test IDs include a stable generated suffix unless the file declares an explicit `id`
- failure output expands only the failing assertions, which keeps CI logs readable while still surfacing details like unsupported spans and rationale

### JSON mode

Run:

```powershell
veritell test examples/grounded_rag.yaml --json
```

Key shape:

```json
{
  "path": "examples/grounded_rag.yaml",
  "summary": {
    "total": 1,
    "passed": 1,
    "failed": 0,
    "errors": 0,
    "skipped": 0,
    "score": 1.0
  },
  "results": [
    {
      "test_id": "demo_grounded_rag_contractors_pto-<generated-id>",
      "status": "pass",
      "score": 1.0,
      "assertion_results": [
        { "assertion": "expected_doc_retrieved", "status": "pass", "method": "deterministic" },
        { "assertion": "retrieval_contains_answer", "status": "pass", "method": "deterministic" },
        { "assertion": "no_unsupported_claims", "status": "pass", "method": "heuristic" }
      ]
    }
  ]
}
```

### Hallucination failure example

Run:

```powershell
veritell test examples/hallucination_failure.yaml
```

Key lines:

```text
FAIL demo_hallucination_failure_refund_window-<generated-id> score=0.00 assertions=0/1 methods=heuristic
  failed assertions:
    - no_unsupported_claims [fail] method=heuristic confidence=<heuristic-confidence>
      unsupported spans:
        - "45"
```

### CI gating demo

Passing gate example:

```powershell
veritell test examples/grounded_rag.yaml --fail-below 80
```

Failing gate example:

```powershell
veritell test examples/hallucination_failure.yaml --fail-below 80
```

Representative failing gate lines:

```text
Summary: total=1 passed=0 failed=1 errors=0 skipped=0 reliability=0.00% score=0.00
Gate: threshold=80.00 score=0.00 passed=false
```

JSON mode:

```powershell
veritell test examples/hallucination_failure.yaml --json --fail-below 80
```

Key shape:

```json
{
  "summary": {
    "score": 0.0
  },
  "gate": {
    "threshold": 80.0,
    "score": 0.0,
    "passed": false
  }
}
```

## Output shape

Terminal mode includes:
- suite path
- per-test status and score
- failure-only assertion detail blocks
- suite summary
- optional CI gate information

JSON mode includes:
- `path`
- `summary`
- `results`
- optional `gate`

## Notes

- Discovery intentionally ignores helper schema assets that end with `_schema.json`, so the schema file can live beside the runnable examples.
- The demo suite is intentionally small and readable; it is meant for walkthroughs, onboarding, and CI gating demos.
