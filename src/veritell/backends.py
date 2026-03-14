"""Judge backend adapters and runtime context for Veritell."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib import error, request

from .models import AssertionResult, VeritellTestCase

try:  # pragma: no cover - Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

_DEFAULT_JUDGE_BACKEND = "heuristic"
_DEFAULT_LOCAL_JUDGE_URL = "http://127.0.0.1:11434"
_DEFAULT_LOCAL_JUDGE_MODEL = "llama3.1:8b"
_DEFAULT_LOCAL_JUDGE_TIMEOUT_SECONDS = 20.0
_SUPPORTED_JUDGE_BACKENDS = {"heuristic", "local", "cloud"}


@dataclass(slots=True, frozen=True)
class LocalJudgeSettings:
    """Config for the local judge backend."""

    model: str = _DEFAULT_LOCAL_JUDGE_MODEL
    base_url: str = _DEFAULT_LOCAL_JUDGE_URL
    timeout_seconds: float = _DEFAULT_LOCAL_JUDGE_TIMEOUT_SECONDS


class LocalJudgeBackendError(RuntimeError):
    """Raised when the local judge backend cannot produce a usable result."""


class LocalJudgeBackendUnavailable(LocalJudgeBackendError):
    """Raised when the local judge backend is not reachable locally."""


class LocalJudgeBackendProtocol(Protocol):
    """Protocol used for local judge backend injection in tests and runtime."""

    def evaluate_assertion(
        self,
        assertion_name: str,
        testcase: VeritellTestCase,
        response: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> AssertionResult:
        """Evaluate a supported assertion using the local judge."""


@dataclass(slots=True, frozen=True)
class JudgeExecutionContext:
    """Backend selection and resolved runtime adapters for a suite execution."""

    preferred_backend: str | None = None
    default_backend: str = _DEFAULT_JUDGE_BACKEND
    local_backend: LocalJudgeBackendProtocol | None = None
    local_settings: LocalJudgeSettings | None = None


class LocalJudgeBackend:
    """Local LLM judge adapter, designed for offline tools like Ollama."""

    def __init__(self, settings: LocalJudgeSettings) -> None:
        self.settings = settings

    def evaluate_assertion(
        self,
        assertion_name: str,
        testcase: VeritellTestCase,
        response: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> AssertionResult:
        if assertion_name == "no_unsupported_claims":
            return self._evaluate_no_unsupported_claims(testcase, response)
        if assertion_name == "should_abstain":
            return self._evaluate_should_abstain(testcase, response)
        if assertion_name == "should_answer":
            return self._evaluate_should_answer(testcase, response)
        raise LocalJudgeBackendError(f"local judge does not support assertion '{assertion_name}'")

    def _evaluate_no_unsupported_claims(self, testcase: VeritellTestCase, response: str) -> AssertionResult:
        prompt = self._build_no_unsupported_claims_prompt(testcase, response)
        payload = self._generate_json(prompt)
        unsupported_spans = payload.get("unsupported_spans")
        if not isinstance(unsupported_spans, list) or not all(isinstance(item, str) for item in unsupported_spans):
            raise LocalJudgeBackendError("local judge response must include an array of string unsupported_spans")

        analyses = payload.get("unsupported_span_analyses")
        if isinstance(analyses, list):
            unsupported_span_analyses = [analysis for analysis in analyses if isinstance(analysis, dict)]
        else:
            reasoning = payload.get("reasoning") if isinstance(payload.get("reasoning"), str) else None
            unsupported_span_analyses = [
                {
                    "span": span,
                    "claim": response,
                    "rationale": reasoning or "flagged by local judge",
                    "matched_context": "",
                    "matched_context_source": "local_judge",
                }
                for span in unsupported_spans
            ]

        supported_spans = payload.get("supported_spans")
        if not isinstance(supported_spans, list) or not all(isinstance(item, str) for item in supported_spans):
            supported_spans = [] if unsupported_spans else [response.strip()] if response.strip() else []

        confidence = _clamp_confidence(payload.get("confidence"), default=0.7)
        reasoning = payload.get("reasoning") if isinstance(payload.get("reasoning"), str) else None
        passed = not unsupported_spans
        return AssertionResult(
            assertion="no_unsupported_claims",
            status="pass" if passed else "fail",
            method="local",
            confidence=confidence,
            details={
                "unsupported_spans": unsupported_spans,
                "unsupported_span_analyses": unsupported_span_analyses,
                "supported_spans": supported_spans,
                "reasoning": reasoning,
                "model": self.settings.model,
            },
        )

    def _evaluate_should_abstain(self, testcase: VeritellTestCase, response: str) -> AssertionResult:
        prompt = self._build_should_abstain_prompt(testcase, response)
        payload = self._generate_json(prompt)
        return self._binary_result("should_abstain", payload)

    def _evaluate_should_answer(self, testcase: VeritellTestCase, response: str) -> AssertionResult:
        prompt = self._build_should_answer_prompt(testcase, response)
        payload = self._generate_json(prompt)
        return self._binary_result("should_answer", payload)

    def _binary_result(self, assertion_name: str, payload: dict[str, Any]) -> AssertionResult:
        passed = payload.get("passed")
        if not isinstance(passed, bool):
            raise LocalJudgeBackendError(f"local judge response for {assertion_name!r} must include boolean passed")
        confidence = _clamp_confidence(payload.get("confidence"), default=0.7)
        reasoning = payload.get("reasoning") if isinstance(payload.get("reasoning"), str) else None
        return AssertionResult(
            assertion=assertion_name,
            status="pass" if passed else "fail",
            method="local",
            confidence=confidence,
            details={"reasoning": reasoning, "model": self.settings.model},
        )

    def _generate_json(self, prompt: str) -> dict[str, Any]:
        endpoint = f"{self.settings.base_url.rstrip('/')}/api/generate"
        body = {
            "model": self.settings.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        data = json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = request.Request(endpoint, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.settings.timeout_seconds) as response_obj:
                payload = json.loads(response_obj.read().decode("utf-8"))
        except error.URLError as exc:
            raise LocalJudgeBackendUnavailable(
                f"local judge unavailable at {self.settings.base_url}; ensure Ollama is running with model '{self.settings.model}'"
            ) from exc
        except json.JSONDecodeError as exc:
            raise LocalJudgeBackendError(f"local judge returned invalid JSON envelope: {exc}") from exc

        text = payload.get("response")
        if not isinstance(text, str) or not text.strip():
            raise LocalJudgeBackendError("local judge response was empty")
        candidate = _extract_json_object(text)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise LocalJudgeBackendError(f"local judge returned invalid JSON payload: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LocalJudgeBackendError("local judge payload must be a JSON object")
        return parsed

    def _build_no_unsupported_claims_prompt(self, testcase: VeritellTestCase, response: str) -> str:
        context = _judge_context_text(testcase)
        return (
            "You are checking whether an answer contains unsupported claims compared with the provided context. "
            "Return JSON only with keys unsupported_spans (array of strings), unsupported_span_analyses (array of objects with span and rationale), supported_spans (array of strings), confidence (0 to 1), and reasoning (string). "
            "If all claims are supported, unsupported_spans must be [].\n\n"
            f"Question:\n{testcase.input.get('question', '')}\n\n"
            f"Context:\n{context}\n\n"
            f"Answer:\n{response}"
        )

    def _build_should_abstain_prompt(self, testcase: VeritellTestCase, response: str) -> str:
        context = _judge_context_text(testcase)
        return (
            "You are checking whether the answer correctly abstains based on the available context. "
            "Return JSON only with keys passed (boolean), confidence (0 to 1), and reasoning (string).\n\n"
            f"Question:\n{testcase.input.get('question', '')}\n\n"
            f"Context:\n{context}\n\n"
            f"Answer:\n{response}"
        )

    def _build_should_answer_prompt(self, testcase: VeritellTestCase, response: str) -> str:
        context = _judge_context_text(testcase)
        return (
            "You are checking whether the answer correctly answers the question based on the available context. "
            "Return JSON only with keys passed (boolean), confidence (0 to 1), and reasoning (string).\n\n"
            f"Question:\n{testcase.input.get('question', '')}\n\n"
            f"Context:\n{context}\n\n"
            f"Answer:\n{response}"
        )


def load_local_judge_settings(base_dir: Path | None = None) -> LocalJudgeSettings:
    """Load local judge settings from config files and environment variables."""

    base_path = Path.cwd() if base_dir is None else Path(base_dir)
    file_config = _load_local_judge_file_config(base_path)

    model = (
        os.getenv("VERITELL_LOCAL_JUDGE_MODEL")
        or os.getenv("VERITELL_JUDGE_MODEL")
        or os.getenv("OLLAMA_MODEL")
        or file_config.get("model")
        or _DEFAULT_LOCAL_JUDGE_MODEL
    )
    base_url = os.getenv("VERITELL_LOCAL_JUDGE_URL") or file_config.get("base_url") or _DEFAULT_LOCAL_JUDGE_URL
    timeout_raw = os.getenv("VERITELL_LOCAL_JUDGE_TIMEOUT") or file_config.get("timeout_seconds")
    timeout_seconds = float(timeout_raw) if timeout_raw is not None else _DEFAULT_LOCAL_JUDGE_TIMEOUT_SECONDS
    return LocalJudgeSettings(model=str(model), base_url=str(base_url), timeout_seconds=float(timeout_seconds))


def load_default_judge_backend(base_dir: Path | None = None) -> str:
    """Load the default backend for hybrid or judge-based assertions."""

    base_path = Path.cwd() if base_dir is None else Path(base_dir)
    file_config = _load_judge_file_config(base_path)
    backend = (
        os.getenv("VERITELL_DEFAULT_JUDGE")
        or os.getenv("VERITELL_JUDGE_BACKEND")
        or file_config.get("default_backend")
        or _DEFAULT_JUDGE_BACKEND
    )
    return _validate_backend_name(str(backend), setting_name="default judge backend")


def build_judge_context(
    preferred_backend: str | None,
    *,
    base_dir: Path | None = None,
    local_backend: LocalJudgeBackendProtocol | None = None,
) -> JudgeExecutionContext:
    """Resolve runtime judge configuration for a suite execution."""

    base_path = Path.cwd() if base_dir is None else Path(base_dir)
    cli_backend = None if preferred_backend is None else _validate_backend_name(preferred_backend, setting_name="judge backend")
    default_backend = load_default_judge_backend(base_path)

    effective_backend = cli_backend or default_backend
    should_prepare_local = effective_backend == "local" or local_backend is not None
    settings = load_local_judge_settings(base_path) if should_prepare_local else None
    resolved_local_backend = local_backend or (LocalJudgeBackend(settings) if settings is not None else None)

    return JudgeExecutionContext(
        preferred_backend=cli_backend,
        default_backend=default_backend,
        local_backend=resolved_local_backend,
        local_settings=settings,
    )


def _load_local_judge_file_config(base_dir: Path) -> dict[str, Any]:
    veritell_toml = base_dir / "veritell.toml"
    if veritell_toml.is_file():
        payload = _load_toml(veritell_toml)
        section = payload.get("local_judge")
        if isinstance(section, dict):
            return section

    pyproject = base_dir / "pyproject.toml"
    if pyproject.is_file():
        payload = _load_toml(pyproject)
        tool = payload.get("tool")
        if isinstance(tool, dict):
            veritell = tool.get("veritell")
            if isinstance(veritell, dict):
                section = veritell.get("local_judge")
                if isinstance(section, dict):
                    return section
    return {}


def _load_judge_file_config(base_dir: Path) -> dict[str, Any]:
    veritell_toml = base_dir / "veritell.toml"
    if veritell_toml.is_file():
        payload = _load_toml(veritell_toml)
        section = payload.get("judge")
        if isinstance(section, dict):
            return section

    pyproject = base_dir / "pyproject.toml"
    if pyproject.is_file():
        payload = _load_toml(pyproject)
        tool = payload.get("tool")
        if isinstance(tool, dict):
            veritell = tool.get("veritell")
            if isinstance(veritell, dict):
                section = veritell.get("judge")
                if isinstance(section, dict):
                    return section
    return {}


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    return payload if isinstance(payload, dict) else {}


def _extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return stripped
    return stripped[start : end + 1]


def _clamp_confidence(value: Any, *, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(0.0, min(1.0, numeric))


def _judge_context_text(testcase: VeritellTestCase) -> str:
    parts: list[str] = []
    retrieved_docs = testcase.context.get("retrieved_docs")
    if isinstance(retrieved_docs, list):
        parts.extend(str(item) for item in retrieved_docs)
    reference_answer = testcase.context.get("reference_answer")
    if isinstance(reference_answer, str) and reference_answer.strip():
        parts.append(reference_answer)
    return "\n".join(part for part in parts if part.strip())


def _validate_backend_name(value: str, *, setting_name: str) -> str:
    normalized = value.strip().lower()
    if normalized not in _SUPPORTED_JUDGE_BACKENDS:
        supported = ", ".join(sorted(_SUPPORTED_JUDGE_BACKENDS))
        raise ValueError(f"{setting_name} must be one of: {supported}")
    return normalized

