# Example Fixtures

Veritell ships a small runnable example suite under `tests/ai/fixtures/`.

These fixtures are designed to run locally without external services. Each one includes a `metadata.mock_response` value so `veritell test` can execute the suite immediately from a fresh checkout.

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

## Run the examples

From the repository root:

```powershell
veritell test tests/ai/fixtures/
veritell test tests/ai/fixtures/ --json
veritell test tests/ai/fixtures/ --fail-below 80
```

Run a single example file:

```powershell
veritell test tests/ai/fixtures/grounded_rag.yaml
veritell test tests/ai/fixtures/structured_output.yaml --json
```

## Expected output

### Terminal mode

Run:

```powershell
veritell test tests/ai/fixtures/grounded_rag.yaml
```

Key lines:

```text
Suite: tests/ai/fixtures/grounded_rag.yaml
Test grounded_rag_contractors_pto-<generated-id>: status=pass score=1.00
  - expected_doc_retrieved: status=pass method=deterministic confidence=1.000
  - retrieval_contains_answer: status=pass method=deterministic confidence=1.000
  - no_unsupported_claims: status=pass method=heuristic confidence=<heuristic-confidence>
Summary: total=1 passed=1 failed=0 errors=0 skipped=0 score=1.00
```

Notes:

- fixture-derived test IDs include a stable generated suffix unless the file declares an explicit `id`
- heuristic confidence is included, but the exact numeric value may change as the heuristic evolves

### JSON mode

Run:

```powershell
veritell test tests/ai/fixtures/grounded_rag.yaml --json
```

Key shape:

```json
{
  "path": "tests/ai/fixtures/grounded_rag.yaml",
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
      "test_id": "grounded_rag_contractors_pto-<generated-id>",
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

### Failing output with `--fail-below`

Run:

```powershell
veritell test <suite-path> --fail-below 80
```

Key lines:

```text
Summary: total=1 passed=1 failed=0 errors=0 skipped=1 score=0.50
Gate: threshold=80.00 score=50.00 passed=false
```

This still prints the full report, but the command exits non-zero because `passed=false`.

JSON mode:

```powershell
veritell test <suite-path> --json --fail-below 80
```

Key shape:

```json
{
  "summary": {
    "score": 0.5
  },
  "gate": {
    "threshold": 80.0,
    "score": 50.0,
    "passed": false
  }
}
```

## Output shape

Terminal mode includes:
- suite path
- per-test status and score
- per-assertion status, method, and confidence
- suite summary
- optional CI gate information

JSON mode includes:
- `path`
- `summary`
- `results`
- optional `gate`

## Notes

- Discovery intentionally ignores helper schema assets that end with `_schema.json`, so the schema file can live beside the runnable fixtures.
- The examples are meant to be small and readable first; they are not intended to represent a full production evaluation suite.
