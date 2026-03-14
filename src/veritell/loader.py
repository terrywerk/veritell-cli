"""Load Veritell test cases from YAML and JSON files."""

from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml
from pydantic import ValidationError

from .models import VeritellTestCase

_SUPPORTED_SUFFIXES = {".yaml", ".yml", ".json"}
_RECOMMENDED_SEVERITIES = {"low", "medium", "high", "critical"}
_SUPPORTED_SCHEMA_VERSIONS = {"v1"}


class InvalidTestCaseError(ValueError):
    """Raised when a test definition file cannot be normalized into canonical models."""

    def __init__(self, message: str, *, file_path: Path, case_index: int | None = None) -> None:
        self.file_path = file_path
        self.case_index = case_index
        location = str(file_path)
        if case_index is not None:
            location = f"{location} (case #{case_index + 1})"
        super().__init__(f"{location}: {message}")


def discover_test_files(path: str | Path = Path("tests/ai")) -> list[Path]:
    """Discover supported test definition files from a file or directory path."""

    root = Path(path)
    if root.is_file():
        return [root] if _is_discoverable_test_file(root) else []
    if root.is_dir():
        return sorted(
            file_path
            for file_path in root.rglob("*")
            if file_path.is_file() and _is_discoverable_test_file(file_path)
        )
    return []


def load_test_suite(path: str | Path = Path("tests/ai")) -> list[VeritellTestCase]:
    """Discover and load all supported test cases from a file or directory path."""

    root = Path(path)
    file_paths = discover_test_files(root)
    if not file_paths:
        raise InvalidTestCaseError("no supported test files found", file_path=root)
    return load_test_cases(file_paths)


def load_test_case(file_path: str | Path) -> VeritellTestCase:
    """Load exactly one test case from a supported YAML or JSON file."""

    cases = load_test_cases([file_path])
    if len(cases) != 1:
        raise InvalidTestCaseError(
            f"expected exactly one test case, found {len(cases)}",
            file_path=Path(file_path),
        )
    return cases[0]


def load_test_cases(file_paths: Iterable[str | Path]) -> list[VeritellTestCase]:
    """Load one or more explicit test definition files into canonical models."""

    normalized: list[VeritellTestCase] = []
    seen_names: dict[str, Path] = {}

    for raw_path in file_paths:
        file_path = Path(raw_path)
        for index, payload in enumerate(_read_raw_cases(file_path)):
            testcase = _normalize_test_case(payload, file_path=file_path, case_index=index)
            previous = seen_names.get(testcase.name)
            if previous is not None:
                warnings.warn(
                    f"Duplicate test name '{testcase.name}' found in {file_path} and {previous}",
                    stacklevel=2,
                )
            else:
                seen_names[testcase.name] = file_path
            normalized.append(testcase)

    return normalized


def _read_raw_cases(file_path: Path) -> list[Mapping[str, Any]]:
    if not file_path.exists():
        raise InvalidTestCaseError("file does not exist", file_path=file_path)
    if file_path.is_dir():
        raise InvalidTestCaseError("directory loading is not supported yet; pass explicit file paths", file_path=file_path)
    if file_path.suffix.lower() not in _SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(_SUPPORTED_SUFFIXES))
        raise InvalidTestCaseError(f"unsupported file extension; expected one of {supported}", file_path=file_path)

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InvalidTestCaseError(f"could not read file: {exc}", file_path=file_path) from exc

    try:
        if file_path.suffix.lower() == ".json":
            raw_data = json.loads(raw_text)
        else:
            raw_data = yaml.safe_load(raw_text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise InvalidTestCaseError(f"failed to parse file: {exc}", file_path=file_path) from exc

    if raw_data is None:
        raise InvalidTestCaseError("file is empty", file_path=file_path)
    if isinstance(raw_data, list):
        if not raw_data:
            raise InvalidTestCaseError("file must contain at least one test case", file_path=file_path)
        if not all(isinstance(item, Mapping) for item in raw_data):
            raise InvalidTestCaseError("top-level lists must contain only object test cases", file_path=file_path)
        return list(raw_data)
    if isinstance(raw_data, Mapping):
        return [raw_data]

    raise InvalidTestCaseError("top-level file content must be an object or list of objects", file_path=file_path)


def _normalize_test_case(raw_case: Mapping[str, Any], *, file_path: Path, case_index: int) -> VeritellTestCase:
    schema_version = raw_case.get("schema_version", "v1")
    if schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
        supported = ", ".join(sorted(_SUPPORTED_SCHEMA_VERSIONS))
        raise InvalidTestCaseError(
            f"unsupported schema_version {schema_version!r}; expected one of {supported}",
            file_path=file_path,
            case_index=case_index,
        )

    normalized_assertions = _normalize_assertions(raw_case.get("assertions"), file_path=file_path, case_index=case_index)
    normalized = {
        "id": raw_case.get("id") or _generate_case_id(file_path=file_path, raw_case=raw_case, assertions=normalized_assertions),
        "name": raw_case.get("name"),
        "description": raw_case.get("description"),
        "input": raw_case.get("input"),
        "context": _normalize_optional_object(raw_case.get("context"), field_name="context", file_path=file_path, case_index=case_index),
        "assertions": normalized_assertions,
        "metadata": _normalize_optional_object(raw_case.get("metadata"), field_name="metadata", file_path=file_path, case_index=case_index),
    }

    _emit_warnings(normalized, file_path=file_path, case_index=case_index)

    try:
        return VeritellTestCase.model_validate(normalized)
    except ValidationError as exc:
        details = "; ".join(error["msg"] for error in exc.errors())
        raise InvalidTestCaseError(details, file_path=file_path, case_index=case_index) from exc


def _normalize_assertions(
    raw_assertions: Any,
    *,
    file_path: Path,
    case_index: int,
) -> list[dict[str, Any]]:
    if raw_assertions is None:
        return []
    if not isinstance(raw_assertions, Sequence) or isinstance(raw_assertions, (str, bytes, bytearray)):
        raise InvalidTestCaseError("assertions must be an array", file_path=file_path, case_index=case_index)

    normalized: list[dict[str, Any]] = []
    for assertion in raw_assertions:
        if isinstance(assertion, str):
            normalized.append({"type": assertion})
            continue
        if not isinstance(assertion, Mapping):
            raise InvalidTestCaseError(
                "each assertion must be an object or string identifier",
                file_path=file_path,
                case_index=case_index,
            )
        normalized.append(dict(assertion))
    return normalized


def _normalize_optional_object(
    value: Any,
    *,
    field_name: str,
    file_path: Path,
    case_index: int,
) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise InvalidTestCaseError(f"{field_name} must be an object", file_path=file_path, case_index=case_index)
    return dict(value)


def _generate_case_id(*, file_path: Path, raw_case: Mapping[str, Any], assertions: list[dict[str, Any]]) -> str:
    seed = {
        "name": raw_case.get("name"),
        "input": raw_case.get("input"),
        "context": raw_case.get("context") or {},
        "assertions": assertions,
        "description": raw_case.get("description"),
    }
    digest = hashlib.sha256(json.dumps(seed, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    stem = raw_case.get("name") or file_path.stem
    return f"{stem}-{digest[:12]}"


def _emit_warnings(raw_case: Mapping[str, Any], *, file_path: Path, case_index: int) -> None:
    input_payload = raw_case.get("input")
    if isinstance(input_payload, Mapping) and "question" not in input_payload:
        warnings.warn(
            f"{file_path} (case #{case_index + 1}): input.question is recommended but missing",
            stacklevel=2,
        )

    metadata = raw_case.get("metadata")
    if isinstance(metadata, Mapping):
        severity = metadata.get("severity")
        if isinstance(severity, str) and severity not in _RECOMMENDED_SEVERITIES:
            warnings.warn(
                f"{file_path} (case #{case_index + 1}): metadata.severity '{severity}' is outside recommended values",
                stacklevel=2,
            )


def _is_discoverable_test_file(file_path: Path) -> bool:
    if file_path.suffix.lower() not in _SUPPORTED_SUFFIXES:
        return False
    return not file_path.name.endswith("_schema.json")

