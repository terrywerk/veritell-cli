"""Tests for judge backend settings and context resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from veritell.backends import JudgeExecutionContext, build_judge_context, load_default_judge_backend, load_local_judge_settings



def test_load_local_judge_settings_reads_veritell_toml(tmp_path: Path) -> None:
    (tmp_path / "veritell.toml").write_text(
        "[local_judge]\nmodel = 'mistral-local'\nbase_url = 'http://127.0.0.1:11435'\ntimeout_seconds = 12\n",
        encoding="utf-8",
    )

    settings = load_local_judge_settings(tmp_path)

    assert settings.model == "mistral-local"
    assert settings.base_url == "http://127.0.0.1:11435"
    assert settings.timeout_seconds == 12.0



def test_load_local_judge_settings_env_overrides_config(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "veritell.toml").write_text(
        "[local_judge]\nmodel = 'config-model'\nbase_url = 'http://127.0.0.1:11435'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("VERITELL_LOCAL_JUDGE_MODEL", "env-model")
    monkeypatch.setenv("VERITELL_LOCAL_JUDGE_URL", "http://127.0.0.1:22434")
    monkeypatch.setenv("VERITELL_LOCAL_JUDGE_TIMEOUT", "7")

    settings = load_local_judge_settings(tmp_path)

    assert settings.model == "env-model"
    assert settings.base_url == "http://127.0.0.1:22434"
    assert settings.timeout_seconds == 7.0



def test_load_default_judge_backend_reads_veritell_toml(tmp_path: Path) -> None:
    (tmp_path / "veritell.toml").write_text(
        "[judge]\ndefault_backend = 'local'\n",
        encoding="utf-8",
    )

    backend = load_default_judge_backend(tmp_path)

    assert backend == "local"



def test_load_default_judge_backend_env_overrides_config(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "veritell.toml").write_text(
        "[judge]\ndefault_backend = 'local'\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("VERITELL_DEFAULT_JUDGE", "cloud")

    backend = load_default_judge_backend(tmp_path)

    assert backend == "cloud"



def test_build_judge_context_accepts_cloud_preference() -> None:
    context = build_judge_context("cloud")

    assert context.preferred_backend == "cloud"
    assert context.default_backend == "heuristic"



def test_build_judge_context_rejects_invalid_backend() -> None:
    with pytest.raises(ValueError, match="must be one of"):
        build_judge_context("bogus")



def test_build_judge_context_uses_configured_default_backend(tmp_path: Path) -> None:
    (tmp_path / "veritell.toml").write_text(
        "[judge]\ndefault_backend = 'local'\n[local_judge]\nmodel = 'mistral-local'\n",
        encoding="utf-8",
    )

    context = build_judge_context(None, base_dir=tmp_path)

    assert context.preferred_backend is None
    assert context.default_backend == "local"
    assert context.local_backend is not None



def test_build_judge_context_returns_default_heuristic_without_preference() -> None:
    context = build_judge_context(None)

    assert context == JudgeExecutionContext(default_backend="heuristic")
