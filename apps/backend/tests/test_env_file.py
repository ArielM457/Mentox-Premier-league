"""El .env del backend completa el entorno sin pisar lo que ya está definido."""

import os

import pytest

from match_intelligence.env_file import load_env_file, parse_env_file


def test_parse_handles_comments_export_quotes_and_equals_in_values() -> None:
    text = "\n".join([
        "# comentario",
        "",
        "NARRATIVE_PROVIDER=azure",
        "export ANALYTICS_ENGINE = persona2",
        "AZURE_OPENAI_API_VERSION='2024-10-21'",
        'SUPABASE_DB_URL="postgresql://u:p@host:5432/db?sslmode=require"',
        "linea sin igual",
        "1INVALIDO=x",
    ])
    assert parse_env_file(text) == {
        "NARRATIVE_PROVIDER": "azure",
        "ANALYTICS_ENGINE": "persona2",
        "AZURE_OPENAI_API_VERSION": "2024-10-21",
        "SUPABASE_DB_URL": "postgresql://u:p@host:5432/db?sslmode=require",
    }


def test_load_fills_missing_variables_without_overriding(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / ".env"
    env.write_text("﻿PM_TEST_NEW=desde-archivo\nPM_TEST_SET=desde-archivo\n", encoding="utf-8")
    monkeypatch.delenv("PM_TEST_NEW", raising=False)
    monkeypatch.setenv("PM_TEST_SET", "desde-terminal")
    try:
        assert load_env_file(env) == ["PM_TEST_NEW"]
        assert os.environ["PM_TEST_NEW"] == "desde-archivo"
        assert os.environ["PM_TEST_SET"] == "desde-terminal"
    finally:
        os.environ.pop("PM_TEST_NEW", None)


def test_missing_file_and_disabled_loading_do_nothing(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert load_env_file(tmp_path / "no-existe.env") == []
    env = tmp_path / ".env"
    env.write_text("PM_TEST_DISABLED=1\n", encoding="utf-8")
    monkeypatch.setenv("MATCH_INTELLIGENCE_ENV_FILE", "")
    assert load_env_file() == []
    monkeypatch.setenv("MATCH_INTELLIGENCE_ENV_FILE", str(env))
    monkeypatch.delenv("PM_TEST_DISABLED", raising=False)
    try:
        assert load_env_file() == ["PM_TEST_DISABLED"]
    finally:
        os.environ.pop("PM_TEST_DISABLED", None)
