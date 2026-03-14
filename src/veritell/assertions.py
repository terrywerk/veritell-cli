"""Assertion plugin contract and registry for Veritell."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate as validate_json_schema

from .models import AssertionResult, VeritellTestCase

AssertionRegistry = dict[str, "Assertion"]

_ABSTENTION_MARKERS = (
    "cannot answer",
    "can't answer",
    "do not know",
    "don't know",
    "not enough information",
    "insufficient information",
    "unable to answer",
    "unknown",
)

_NEGATION_MARKERS = {"no", "not", "never", "without", "cannot", "can't", "don't", "isn't", "aren't", "won't"}
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have", "if", "in", "into",
    "is", "it", "of", "on", "or", "that", "the", "their", "then", "there", "these", "they", "this", "to",
    "was", "were", "will", "with", "would", "you", "your", "about", "after", "before", "during", "over",
    "under", "than", "them", "he", "she", "we", "our", "i", "me", "my", "us", "his", "her", "its",
}
_SUPPORTED_FORMATS = {"json", "markdown", "bullet_list"}
_CLAIM_SPLIT_RE = re.compile(r"[.!?;\n]+")
_TOKEN_RE = re.compile(r"[a-z0-9']+")
_HALLUCINATION_THRESHOLD = 0.72
_REGISTRY: AssertionRegistry = {}


class Assertion(ABC):
    """Base contract implemented by all assertion plugins."""

    name: str

    def supported_backends(self) -> tuple[str, ...]:
        return ("heuristic", "local", "cloud")

    @abstractmethod
    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params: Mapping[str, Any] | None = None,
    ) -> AssertionResult:
        """Evaluate a test case response and return a structured assertion result."""


class ResponseFormatValidAssertion(Assertion):
    name = "response_format_valid"

    def supported_backends(self) -> tuple[str, ...]:
        return ("heuristic",)

    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params: Mapping[str, Any] | None = None,
    ) -> AssertionResult:
        config = params or {}
        expected_format = str(config.get("format") or "json").strip().lower()
        if expected_format not in _SUPPORTED_FORMATS:
            supported = ", ".join(sorted(_SUPPORTED_FORMATS))
            return AssertionResult(
                assertion=self.name,
                status="error",
                method="deterministic",
                details={"reason": f"unsupported response format '{expected_format}'; supported formats: {supported}"},
            )

        if expected_format == "json":
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError as exc:
                return AssertionResult(
                    assertion=self.name,
                    status="fail",
                    method="deterministic",
                    confidence=1.0,
                    details={"format": expected_format, "reason": str(exc), "actual": response},
                )
            return AssertionResult(
                assertion=self.name,
                status="pass",
                method="deterministic",
                confidence=1.0,
                details={"format": expected_format, "parsed_type": type(parsed).__name__},
            )

        if expected_format == "bullet_list":
            lines = [line.strip() for line in response.splitlines() if line.strip()]
            passed = bool(lines) and all(line.startswith(("- ", "* ")) for line in lines)
            return AssertionResult(
                assertion=self.name,
                status="pass" if passed else "fail",
                method="deterministic",
                confidence=1.0,
                details={"format": expected_format, "line_count": len(lines), "actual": response},
            )

        stripped = response.strip()
        passed = bool(stripped) and any(token in stripped for token in ("#", "*", "- ", "`", ">"))
        return AssertionResult(
            assertion=self.name,
            status="pass" if passed else "fail",
            method="deterministic",
            confidence=1.0,
            details={"format": expected_format, "actual": response},
        )


class JsonSchemaValidAssertion(Assertion):
    name = "json_schema_valid"

    def supported_backends(self) -> tuple[str, ...]:
        return ("heuristic",)

    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params: Mapping[str, Any] | None = None,
    ) -> AssertionResult:
        config = params or {}
        schema = _resolve_json_schema(testcase, config)
        if schema is None:
            return AssertionResult(
                assertion=self.name,
                status="error",
                method="deterministic",
                details={"reason": "params.schema or params.schema_ref is required for json_schema_valid"},
            )

        try:
            payload = json.loads(response)
        except json.JSONDecodeError as exc:
            return AssertionResult(
                assertion=self.name,
                status="fail",
                method="deterministic",
                confidence=1.0,
                details={"reason": f"response is not valid JSON: {exc}", "actual": response},
            )

        try:
            validate_json_schema(instance=payload, schema=schema)
        except JsonSchemaValidationError as exc:
            return AssertionResult(
                assertion=self.name,
                status="fail",
                method="deterministic",
                confidence=1.0,
                details={"reason": exc.message, "validator": exc.validator, "path": list(exc.path)},
            )

        return AssertionResult(
            assertion=self.name,
            status="pass",
            method="deterministic",
            confidence=1.0,
            details={"schema_keys": sorted(schema.keys())},
        )


class ExactMatchAssertion(Assertion):
    name = "exact_match"

    def supported_backends(self) -> tuple[str, ...]:
        return ("heuristic",)

    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params: Mapping[str, Any] | None = None,
    ) -> AssertionResult:
        expected = _resolve_expected_answer(testcase, params or {})
        if expected is None:
            return AssertionResult(
                assertion=self.name,
                status="error",
                method="deterministic",
                details={"reason": "reference_answer or params.expected is required for exact match assertions"},
            )
        passed = equals(expected, response)
        return AssertionResult(
            assertion=self.name,
            status="pass" if passed else "fail",
            method="deterministic",
            confidence=1.0,
            details={"expected": expected, "actual": response},
        )


class ExactMatchAnswerAssertion(ExactMatchAssertion):
    name = "exact_match_answer"


class ExpectedDocRetrievedAssertion(Assertion):
    name = "expected_doc_retrieved"

    def supported_backends(self) -> tuple[str, ...]:
        return ("heuristic",)

    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params: Mapping[str, Any] | None = None,
    ) -> AssertionResult:
        expected_docs = _coerce_docs(testcase.context.get("expected_docs"))
        retrieved_docs = _coerce_docs(testcase.context.get("retrieved_docs"))
        if not expected_docs:
            return AssertionResult(
                assertion=self.name,
                status="error",
                method="deterministic",
                details={"reason": "context.expected_docs is required"},
            )
        missing_docs = [doc for doc in expected_docs if doc not in retrieved_docs]
        return AssertionResult(
            assertion=self.name,
            status="pass" if not missing_docs else "fail",
            method="deterministic",
            confidence=1.0,
            details={"expected_docs": expected_docs, "retrieved_docs": retrieved_docs, "missing_docs": missing_docs},
        )


class RetrievalContainsAnswerAssertion(Assertion):
    name = "retrieval_contains_answer"

    def supported_backends(self) -> tuple[str, ...]:
        return ("heuristic",)

    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params: Mapping[str, Any] | None = None,
    ) -> AssertionResult:
        reference_answer = _resolve_expected_answer(testcase, params or {})
        retrieved_docs = _coerce_docs(testcase.context.get("retrieved_docs"))
        if reference_answer is None:
            return AssertionResult(
                assertion=self.name,
                status="error",
                method="deterministic",
                details={"reason": "context.reference_answer is required"},
            )
        combined_docs = "\n".join(retrieved_docs).lower()
        passed = reference_answer.lower() in combined_docs
        return AssertionResult(
            assertion=self.name,
            status="pass" if passed else "fail",
            method="deterministic",
            confidence=1.0,
            details={"reference_answer": reference_answer, "retrieved_docs": retrieved_docs, "actual": response},
        )


class NoUnsupportedClaimsAssertion(Assertion):
    name = "no_unsupported_claims"

    def supported_backends(self) -> tuple[str, ...]:
        return ("heuristic",)

    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params: Mapping[str, Any] | None = None,
    ) -> AssertionResult:
        context_segments = _collect_context_segments(testcase)
        if not context_segments:
            return AssertionResult(
                assertion=self.name,
                status="error",
                method="heuristic",
                confidence=0.0,
                details={"reason": "textual context is required via context.retrieved_docs or context.reference_answer"},
            )

        claims = _split_claims(response)
        if not claims:
            return AssertionResult(
                assertion=self.name,
                status="error",
                method="heuristic",
                confidence=0.0,
                details={"reason": "response did not contain any analyzable claims", "actual": response},
            )

        analyses: list[dict[str, Any]] = []
        unsupported_spans: list[str] = []
        supported_spans: list[str] = []
        scores: list[float] = []

        for claim in claims:
            claim_tokens = _content_tokens(claim)
            if not claim_tokens:
                continue

            best_score = 0.0
            best_context = ""
            for context_segment in context_segments:
                score = _claim_support_score(claim, claim_tokens, context_segment)
                if score > best_score:
                    best_score = score
                    best_context = context_segment

            rounded_score = round(best_score, 3)
            scores.append(rounded_score)
            analyses.append({
                "claim": claim,
                "support_score": rounded_score,
                "matched_context": best_context,
            })

            if best_score >= _HALLUCINATION_THRESHOLD:
                supported_spans.append(claim)
            else:
                unsupported_spans.append(claim)

        if not analyses:
            return AssertionResult(
                assertion=self.name,
                status="error",
                method="heuristic",
                confidence=0.0,
                details={"reason": "response did not contain any claims with meaningful content"},
            )

        passed = not unsupported_spans
        reference_score = (sum(scores) / len(scores)) if passed else min(scores)
        confidence = _hallucination_confidence(reference_score, passed=passed)
        return AssertionResult(
            assertion=self.name,
            status="pass" if passed else "fail",
            method="heuristic",
            confidence=confidence,
            details={
                "supported_spans": supported_spans,
                "unsupported_spans": unsupported_spans,
                "claim_analyses": analyses,
                "context_span_count": len(context_segments),
                "threshold": _HALLUCINATION_THRESHOLD,
            },
        )


class ShouldAbstainAssertion(Assertion):
    name = "should_abstain"

    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params: Mapping[str, Any] | None = None,
    ) -> AssertionResult:
        passed = _looks_like_abstention(response)
        return AssertionResult(
            assertion=self.name,
            status="pass" if passed else "fail",
            method=backend,
            confidence=1.0,
            details={"actual": response},
        )


class ShouldAnswerAssertion(Assertion):
    name = "should_answer"

    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params: Mapping[str, Any] | None = None,
    ) -> AssertionResult:
        passed = bool(response.strip()) and not _looks_like_abstention(response)
        return AssertionResult(
            assertion=self.name,
            status="pass" if passed else "fail",
            method=backend,
            confidence=1.0,
            details={"actual": response},
        )


class UnsupportedAssertion(Assertion):
    """Fallback assertion used when no registered implementation exists."""

    def __init__(self, name: str) -> None:
        self.name = name

    def evaluate(
        self,
        testcase: VeritellTestCase,
        response: str,
        *,
        backend: str = "heuristic",
        params: Mapping[str, Any] | None = None,
    ) -> AssertionResult:
        return AssertionResult(
            assertion=self.name,
            status="skip",
            method="unsupported",
            details={"reason": f"assertion '{self.name}' is not implemented yet"},
        )


def equals(expected: str, actual: str) -> bool:
    """Return ``True`` when two strings match exactly."""

    return expected == actual


def register_assertion(assertion: type[Assertion] | Assertion, *, replace: bool = False) -> Assertion:
    """Register an assertion implementation by its unique name."""

    instance = assertion() if isinstance(assertion, type) else assertion
    name = getattr(instance, "name", "").strip()
    if not name:
        raise ValueError("assertion implementations must define a non-empty name")
    if name in _REGISTRY and not replace:
        raise ValueError(f"assertion '{name}' is already registered")
    _REGISTRY[name] = instance
    return instance


def unregister_assertion(name: str) -> None:
    """Remove an assertion implementation from the registry if present."""

    _REGISTRY.pop(name, None)


def get_assertion(name: str) -> Assertion | None:
    """Return a registered assertion implementation by name."""

    return _REGISTRY.get(name)


def list_assertions() -> tuple[str, ...]:
    """Return the registered assertion names in sorted order."""

    return tuple(sorted(_REGISTRY))


def evaluate_registered_assertion(
    testcase: VeritellTestCase,
    assertion_config: Mapping[str, Any],
    response: str,
) -> AssertionResult:
    """Resolve an assertion from the registry and evaluate it against a response."""

    assertion_name = str(assertion_config.get("type", "")).strip()
    backend = str(assertion_config.get("backend") or "heuristic")
    params = assertion_config.get("params") if isinstance(assertion_config.get("params"), Mapping) else {}
    assertion = get_assertion(assertion_name) or UnsupportedAssertion(assertion_name)

    if backend not in assertion.supported_backends():
        supported = ", ".join(assertion.supported_backends())
        return AssertionResult(
            assertion=assertion_name,
            status="error",
            method=backend,
            details={"reason": f"backend '{backend}' is not supported for assertion '{assertion_name}'; supported backends: {supported}"},
        )

    return assertion.evaluate(testcase, response, backend=backend, params=params)


def _resolve_expected_answer(testcase: VeritellTestCase, params: Mapping[str, Any]) -> str | None:
    explicit = params.get("expected")
    if isinstance(explicit, str):
        return explicit
    reference = testcase.context.get("reference_answer")
    if isinstance(reference, str):
        return reference
    return None


def _resolve_json_schema(testcase: VeritellTestCase, params: Mapping[str, Any]) -> dict[str, Any] | None:
    inline_schema = params.get("schema")
    if isinstance(inline_schema, Mapping):
        return dict(inline_schema)

    schema_ref = params.get("schema_ref")
    if not isinstance(schema_ref, str) or not schema_ref.strip():
        return None

    for container in (testcase.context.get("schemas"), testcase.metadata.get("schemas")):
        if isinstance(container, Mapping):
            candidate = container.get(schema_ref)
            if isinstance(candidate, Mapping):
                return dict(candidate)

    schema_path = Path(schema_ref)
    if schema_path.is_file():
        try:
            payload = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    return None


def _coerce_docs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if isinstance(item, str):
            normalized.append(item)
        elif isinstance(item, Mapping):
            normalized.append(json.dumps(dict(item), sort_keys=True))
        else:
            normalized.append(str(item))
    return normalized


def _collect_context_segments(testcase: VeritellTestCase) -> list[str]:
    segments: list[str] = []
    reference_answer = testcase.context.get("reference_answer")
    if isinstance(reference_answer, str) and reference_answer.strip():
        segments.extend(_split_claims(reference_answer) or [reference_answer.strip()])

    for document in _coerce_docs(testcase.context.get("retrieved_docs")):
        if document.strip():
            segments.extend(_split_claims(document) or [document.strip()])

    return [segment for segment in segments if _content_tokens(segment)]


def _split_claims(text: str) -> list[str]:
    return [claim.strip() for claim in _CLAIM_SPLIT_RE.split(text) if claim.strip()]


def _content_tokens(text: str) -> list[str]:
    tokens = _TOKEN_RE.findall(text.lower())
    return [token for token in tokens if token not in _STOPWORDS and (len(token) > 2 or token.isdigit() or token in _NEGATION_MARKERS)]


def _claim_support_score(claim: str, claim_tokens: list[str], context_segment: str) -> float:
    normalized_claim = _normalize_text(claim)
    normalized_context = _normalize_text(context_segment)
    if normalized_claim and normalized_claim in normalized_context:
        return 1.0

    context_tokens = set(_content_tokens(context_segment))
    if not context_tokens:
        return 0.0

    claim_token_set = set(claim_tokens)
    overlap_ratio = len(claim_token_set & context_tokens) / len(claim_token_set)
    bigrams = _bigrams(claim_tokens)
    bigram_ratio = (sum(1 for bigram in bigrams if bigram in normalized_context) / len(bigrams)) if bigrams else overlap_ratio
    score = max(overlap_ratio, bigram_ratio)

    leading_token = claim_tokens[0] if claim_tokens else None
    if leading_token and leading_token not in context_tokens:
        score -= 0.25

    claim_has_negation = any(token in _NEGATION_MARKERS for token in claim_tokens)
    context_has_negation = any(token in _NEGATION_MARKERS for token in context_tokens)
    if claim_has_negation != context_has_negation:
        score -= 0.35

    return max(0.0, min(1.0, score))


def _normalize_text(text: str) -> str:
    return " ".join(_TOKEN_RE.findall(text.lower()))


def _bigrams(tokens: list[str]) -> list[str]:
    return [f"{left} {right}" for left, right in zip(tokens, tokens[1:])]


def _hallucination_confidence(score: float, *, passed: bool) -> float:
    base = 0.6 if passed else 0.55
    margin = abs(score - _HALLUCINATION_THRESHOLD)
    return round(min(1.0, max(0.0, base + margin)), 3)


def _looks_like_abstention(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _ABSTENTION_MARKERS)


for _builtin in (
    ResponseFormatValidAssertion,
    JsonSchemaValidAssertion,
    ExactMatchAssertion,
    ExactMatchAnswerAssertion,
    ExpectedDocRetrievedAssertion,
    RetrievalContainsAnswerAssertion,
    NoUnsupportedClaimsAssertion,
    ShouldAbstainAssertion,
    ShouldAnswerAssertion,
):
    register_assertion(_builtin)
