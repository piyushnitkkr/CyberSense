"""Unit tests for configuration loading and validation."""

from __future__ import annotations

import os
import pytest

from cybersense.config import Settings, get_settings


def test_default_settings():
    settings = Settings()
    assert settings.app_name == "CyberSense"
    assert settings.database_url.startswith("sqlite")
    assert settings.embedding.dimension == 384
    assert settings.generation.provider in ["groq", "anthropic", "ollama", "fake"]
    assert settings.retrieval.top_k_retrieve > 0


def test_env_override(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("QDRANT_URL", "http://qdrant-host:6333")

    # Clear cached settings
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_env == "production"
    assert settings.log_level == "DEBUG"
    assert settings.qdrant_url == "http://qdrant-host:6333"

    # Reset cache
    get_settings.cache_clear()
