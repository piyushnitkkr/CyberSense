"""Unit tests for LLM clients and factory."""

from __future__ import annotations

import pytest

from cybersense.config import Settings
from cybersense.generation.llm import (
    FakeLLMClient,
    GroqClient,
    build_llm_client,
)


@pytest.mark.asyncio
async def test_fake_llm_client_generate():
    client = FakeLLMClient(response="Hello CyberSense [1]")
    res = await client.generate("test prompt")
    assert res == "Hello CyberSense [1]"


@pytest.mark.asyncio
async def test_fake_llm_client_stream():
    client = FakeLLMClient(response="Hello CyberSense [1]")
    tokens = []
    async for token in client.stream("test prompt"):
        tokens.append(token)
    assert "".join(tokens).strip() == "Hello CyberSense [1]"


def test_groq_client_requires_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY is not set"):
        GroqClient(api_key="")


def test_groq_client_init_with_key():
    client = GroqClient(api_key="gsk_test12345", model="llama-3.1-8b-instant")
    assert client.model == "llama-3.1-8b-instant"


def test_build_llm_client():
    settings = Settings()
    client = build_llm_client("fake", settings)
    assert isinstance(client, FakeLLMClient)

    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_llm_client("unsupported_provider", settings)
