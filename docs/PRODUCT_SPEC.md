
# Veritell Product Specification

## Product Vision

Veritell is an **AI reliability testing framework** that enables developers to validate AI systems using repeatable test cases and assertions—similar to how pytest validates traditional software.

Core principle:

test case → runner → assertions → results → diagnostics

The system must work **locally first**, with optional cloud intelligence.

---

# Target Users

## Primary
- AI engineers
- ML engineers
- RAG application developers
- AI consultancies

## Secondary
- Responsible AI teams
- Risk / compliance teams
- CIO / CTO stakeholders

---

# Core Concepts

## Test Case

The fundamental unit of reliability validation.

Example:

```yaml
name: contractor_policy_grounding

input:
  question: "How much PTO do contractors get?"

context:
  retrieved_docs:
    - contractor_policy_v2.txt

assertions:
  - no_unsupported_claims
  - retrieval_contains_answer
  - should_answer
```

---

## Assertions

Assertions check reliability properties of AI outputs.

Examples:

- retrieval_contains_answer
- no_unsupported_claims
- should_abstain
- json_schema_valid
- citation_supported

Assertions may run with different backends:

- heuristic
- local
- cloud

---

# Core CLI

Primary commands:

```
veritell test
veritell scan
veritell generate-evals
veritell import-evals
veritell diagnose
```

Example usage:

```
veritell test tests/ai
veritell test --fail-below 80
veritell test --json
```

---

# Test Execution Flow

1. CLI invoked
2. test loader reads YAML tests
3. runner invokes AI system
4. assertions execute
5. results aggregated
6. diagnostics explain failures
7. optional upload to cloud

---

# Assertion Result Schema

Example result:

```json
{
  "assertion": "no_unsupported_claims",
  "status": "fail",
  "method": "heuristic",
  "confidence": 0.63,
  "details": {}
}
```

Fields:

- assertion
- status
- method
- confidence
- details

---

# Internal Data Models

## VeritellTestCase

```python
class VeritellTestCase:
    id: str
    name: str
    input: dict
    context: dict
    assertions: list
    metadata: dict
```

## AssertionResult

```python
class AssertionResult:
    assertion: str
    status: str
    method: str
    confidence: float | None
    details: dict
```

## VeritellTestResult

```python
class VeritellTestResult:
    test_id: str
    status: str
    assertion_results: list
    score: float | None
    diagnosis: dict | None
```

---

# CI/CD Integration

Example pipeline command:

```
veritell test --fail-below 80
```

If reliability score falls below threshold deployment fails.

---

# MVP Scope

Initial implementation includes:

1. CLI framework
2. YAML test loader
3. test runner
4. deterministic assertions
5. heuristic unsupported-claim detection
6. scoring system
7. diagnostics skeleton

Estimated MVP build: **6–8 weeks**.

