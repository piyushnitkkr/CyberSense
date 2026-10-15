"""LLMClient abstract interface + Anthropic, Groq, Ollama, and Fake implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMClient(ABC):
    """Provider-agnostic LLM interface."""

    @abstractmethod
    async def generate(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.1) -> str:
        """Return the complete generated text."""
        ...

    @abstractmethod
    async def stream(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.1) -> AsyncIterator[str]:
        """Yield text tokens as they are generated."""
        ...


# ── Groq ──────────────────────────────────────────────────────────────────────

class GroqClient(LLMClient):
    """Groq Cloud LLM client — free tier, ultra-fast inference."""

    def __init__(self, api_key: str = "", model: str = "llama-3.1-8b-instant") -> None:
        import os
        key = api_key or os.environ.get("GROQ_API_KEY", "")
        if not key:
            raise ValueError(
                "GROQ_API_KEY is not set. Please set GROQ_API_KEY in your .env file "
                "or pass api_key directly (get a free key at https://console.groq.com)."
            )
        from groq import AsyncGroq
        self._client = AsyncGroq(api_key=key)
        self.model = model

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.1) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    async def stream(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.1) -> AsyncIterator[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token


# ── Anthropic ─────────────────────────────────────────────────────────────────

class AnthropicClient(LLMClient):
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022") -> None:
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.1) -> str:
        msg = await self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "You are CyberSense, a cybersecurity assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    async def stream(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.1) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "You are CyberSense, a cybersecurity assistant.",
            messages=[{"role": "user", "content": prompt}],
        ) as s:
            async for text in s.text_stream:
                yield text


# ── Ollama ────────────────────────────────────────────────────────────────────

class OllamaClient(LLMClient):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3") -> None:
        import ollama
        self._client = ollama.AsyncClient(host=base_url)
        self.model = model

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.1) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = await self._client.chat(model=self.model, messages=messages)
        return response["message"]["content"]

    async def stream(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.1) -> AsyncIterator[str]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        async for chunk in await self._client.chat(model=self.model, messages=messages, stream=True):
            if token := chunk.get("message", {}).get("content", ""):
                yield token


# ── Fake (deterministic, for tests) ─────────────────────────────────────────

class FakeLLMClient(LLMClient):
    """Deterministic fake LLM for unit tests — needs no API key."""

    def __init__(self, response: str = "This is a test response [1].") -> None:
        self.response = response

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.1) -> str:
        return self.response

    async def stream(self, prompt: str, system: str = "", max_tokens: int = 1024, temperature: float = 0.1) -> AsyncIterator[str]:
        for word in self.response.split():
            yield word + " "


def build_llm_client(provider: str, settings) -> LLMClient:
    """Factory that builds the appropriate LLM client from settings."""
    if provider == "groq":
        return GroqClient(api_key=settings.groq_api_key, model=settings.generation.model)
    if provider == "anthropic":
        return AnthropicClient(api_key=settings.anthropic_api_key, model=settings.generation.model)
    if provider == "ollama":
        return OllamaClient(base_url=settings.ollama_base_url, model=settings.generation.model)
    if provider == "fake":
        return FakeLLMClient()
    raise ValueError(f"Unknown LLM provider: {provider!r}. Use 'groq', 'anthropic', 'ollama', or 'fake'.")
