"""Core data models for Veritell."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ALLOWED_BACKENDS = {"heuristic", "local", "cloud"}


class VeritellModel(BaseModel):
    """Base model with strict top-level validation and serialization helpers."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, payload: str) -> Self:
        return cls.model_validate_json(payload)


class VeritellTestCase(VeritellModel):
    """Canonical normalized test case used across loaders and runners."""

    id: str | None = None
    name: str = Field(min_length=1)
    description: str | None = None
    input: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)
    assertions: list[dict[str, Any]] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("assertions")
    @classmethod
    def validate_assertions(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for assertion in value:
            assertion_type = assertion.get("type")
            if not isinstance(assertion_type, str) or not assertion_type.strip():
                raise ValueError("each assertion must include a non-empty 'type'")

            backend = assertion.get("backend")
            if backend is not None and backend not in _ALLOWED_BACKENDS:
                allowed = ", ".join(sorted(_ALLOWED_BACKENDS))
                raise ValueError(f"assertion backend must be one of: {allowed}")

            params = assertion.get("params")
            if params is not None and not isinstance(params, dict):
                raise ValueError("assertion 'params' must be an object when provided")
        return value


class AssertionResult(VeritellModel):
    """Structured result for a single assertion execution."""

    assertion: str = Field(min_length=1)
    status: Literal["pass", "fail", "error", "skip"]
    method: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)


class VeritellTestResult(VeritellModel):
    """Canonical per-test execution result returned by the runner."""

    test_id: str = Field(min_length=1)
    status: Literal["pass", "fail", "error", "skip"]
    assertion_results: list[AssertionResult] = Field(default_factory=list)
    score: float | None = None
    diagnosis: dict[str, Any] | None = None


class VeritellRunSummary(VeritellModel):
    """Aggregated runner counts for a suite execution."""

    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    errors: int = Field(ge=0)
    skipped: int = Field(ge=0)
    score: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.passed + self.failed + self.errors + self.skipped != self.total:
            raise ValueError("summary counts must add up to total")
        return self


class VeritellSuiteResult(VeritellModel):
    """Runner output for an entire suite of tests."""

    results: list[VeritellTestResult] = Field(default_factory=list)
    summary: VeritellRunSummary


@dataclass(slots=True, frozen=True)
class ModelSpec:
    """Minimal model description used by the scaffold."""

    name: str
    provider: str = "local"

