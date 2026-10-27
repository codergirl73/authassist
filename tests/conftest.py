"""Test fixtures. Tests never call real APIs: the Token Factory transport
(llm._call_once) and the Tavily client are replaced with fakes."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from authassist import config, llm, policy

TEST_MODELS = {
    "vision": {"model": "test/vision", "temperature": 0.0, "max_tokens": 100},
    "fast": {"model": "test/fast", "temperature": 0.0, "max_tokens": 100},
    "reasoning": {"model": "test/reasoning", "temperature": 0.0, "max_tokens": 100},
    "fallbacks": {"reasoning": "test/reasoning-fallback"},
}


class FakeLLM:
    """Routes each call to a handler by a marker string found in the messages."""

    def __init__(self) -> None:
        self.handlers: list[tuple[str, object]] = []
        self.calls: list[dict] = []

    def on(self, marker: str, reply) -> None:
        """reply: str, dict (JSON-encoded), Exception, or callable(messages, model) -> any of those."""
        self.handlers.append((marker, reply))

    def __call__(self, model, settings, messages):
        flat = json.dumps(messages)
        self.calls.append({"model": model, "messages": messages})
        for marker, reply in self.handlers:
            if marker in flat:
                if callable(reply) and not isinstance(reply, type):
                    reply = reply(messages, model)
                if isinstance(reply, Exception):
                    raise reply
                text = reply if isinstance(reply, str) else json.dumps(reply)
                return text, SimpleNamespace(prompt_tokens=10, completion_tokens=5)
        raise AssertionError(f"FakeLLM: no handler for call to {model}")


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "models_config", lambda: TEST_MODELS)
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(llm, "_backoff", lambda attempt: None)
    monkeypatch.setattr(policy, "SNAPSHOT_DIR", Path(__file__).parent / "fixtures" / "snapshots")
    monkeypatch.setattr(llm, "client", lambda: object())  # transport is faked via _call_once

    def no_tavily():
        raise RuntimeError("Tavily disabled in tests")

    monkeypatch.setattr(policy, "_tavily", no_tavily)


@pytest.fixture
def fake_llm(monkeypatch) -> FakeLLM:
    fake = FakeLLM()
    monkeypatch.setattr(llm, "_call_once", fake)
    return fake
