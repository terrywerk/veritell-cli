
# Veritell Assertions Specification

## Purpose

Assertions are the core reliability checks used by Veritell to validate AI system behavior.

Each assertion evaluates a specific property of an AI response such as:

- grounding
- retrieval coverage
- abstention behavior
- response correctness
- formatting compliance

Assertions are executed by the Veritell test runner and return structured results.

---

# Assertion Categories

Assertions fall into three categories.

## 1. Deterministic Assertions

Run fully offline without LLM judges.

Examples:

- json_schema_valid
- response_format_valid
- expected_doc_retrieved
- retrieval_contains_answer
- keyword_coverage
- exact_match_answer
- token_budget_max

These are ideal for CI environments.

---

## 2. Hybrid Assertions

Can run with heuristics but improve with LLM judges.

Examples:

- no_unsupported_claims
- citation_supported
- contradiction_absent
- transformation_correct

Backends supported:

- heuristic
- local
- cloud

---

## 3. Judge-Based Assertions

Require LLM evaluation for best results.

Examples:

- answer_correctness
- answer_relevance
- tone_policy_compliant

Backends supported:

- local
- cloud

---

# Assertion Matrix

| Assertion | Description | Heuristic | Local LLM | Cloud |
|-----------|-------------|-----------|-----------|-------|
| response_format_valid | Output matches expected format | ✅ | — | — |
| json_schema_valid | JSON output matches schema | ✅ | — | — |
| contains_required_fields | Required fields exist | ✅ | — | — |
| forbidden_phrase_absent | Disallowed phrases not present | ✅ | — | — |
| abstention_phrase_present | Refusal phrase present | ✅ | — | — |
| expected_doc_retrieved | Gold document retrieved | ✅ | — | — |
| retrieval_contains_answer | Retrieval context contains answer | ✅ | — | — |
| retrieval_coverage_min | Retrieval quality threshold | ✅ | — | — |
| exact_match_answer | Exact match answer check | ✅ | — | — |
| keyword_coverage | Required keywords present | ✅ | — | — |
| citation_present | Citation included in response | ✅ | — | — |
| citation_supported | Citation supports claim | ⚠️ | ✅ | ✅ |
| no_unsupported_claims | No hallucinated claims | ⚠️ | ✅ | ✅ |
| should_abstain | Model abstains when appropriate | ✅ | ✅ | ✅ |
| should_answer | Model answers when appropriate | ⚠️ | ✅ | ✅ |
| answer_relevance | Response relevant to prompt | ⚠️ | ✅ | ✅ |
| answer_correctness | Response factually correct | ❌ | ✅ | ✅ |
| transformation_correct | Output transformation faithful | ⚠️ | ✅ | ✅ |
| contradiction_absent | Response does not contradict context | ⚠️ | ✅ | ✅ |
| tone_policy_compliant | Output meets style policy | ✅ | ✅ | ✅ |
| response_latency_max | Response latency threshold | ✅ | — | — |
| token_budget_max | Token usage limit | ✅ | — | — |

Legend:

- ✅ strong support
- ⚠ heuristic approximation
- ❌ not recommended

---

# Assertion Result Schema

Each assertion returns structured results.

Example:

```json
{
  "assertion": "no_unsupported_claims",
  "status": "fail",
  "method": "heuristic",
  "confidence": 0.64,
  "details": {
    "unsupported_spans": [
      "contractors receive 15 PTO days"
    ]
  }
}
```

Fields:

- assertion: assertion identifier
- status: pass / fail
- method: heuristic / local / cloud
- confidence: evaluation confidence
- details: diagnostic metadata

---

# YAML Assertion Example

Assertions are defined inside a test case.

Example:

```yaml
name: contractor_policy_grounding

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
```

---

# Assertion Interface

All assertions implement a common interface.

Example:

```python
class Assertion:

    name: str

    def supported_backends(self):
        return ["heuristic", "local", "cloud"]

    def evaluate(self, test_case, response, backend="heuristic"):
        pass
```

Example implementation:

```python
class NoUnsupportedClaims(Assertion):

    def evaluate(self, response, context, backend="heuristic"):
        ...
```

---

# Design Principles

Veritell assertions must be:

- deterministic where possible
- reproducible across runs
- composable within test cases
- CI-friendly
- transparent about evaluation backend

---

# Long-Term Goal

Assertions become the **standard vocabulary for AI reliability testing**.

Example:

```python
assert no_unsupported_claims
assert retrieval_contains_answer
assert should_abstain
```
