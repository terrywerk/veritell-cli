# Demo Example Suite

This folder is a runnable Veritell demo suite.

All examples are offline-friendly and use `metadata.mock_response`, so they work from a fresh checkout without external services.

## Included demos

- `grounded_rag.yaml` — grounded RAG validation
- `abstention.yaml` — abstention when evidence is missing
- `structured_output.yaml` — structured JSON output validation
- `hallucination_failure.yaml` — intentional hallucination failure with unsupported span highlighting

## Run from the repository root

```powershell
veritell test examples/grounded_rag.yaml
veritell test examples/abstention.yaml
veritell test examples/structured_output.yaml
veritell test examples/hallucination_failure.yaml
```

## Run the full demo suite

```powershell
veritell test examples/
veritell test examples/ --json
```

The full suite includes one intentional failure (`hallucination_failure.yaml`), so the overall command exits non-zero. That is useful for demos because it shows both a passing path and a reliability failure in one run.

## CI gating examples

Passing gate example:

```powershell
veritell test examples/grounded_rag.yaml --fail-below 80
```

Failing gate example:

```powershell
veritell test examples/hallucination_failure.yaml --fail-below 80
```

