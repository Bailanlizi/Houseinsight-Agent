"""Pytest fixtures shared across tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def mock_llm_env(monkeypatch):
    monkeypatch.setenv("HI_MOCK_LLM", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from server.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_llm_nodes(monkeypatch):
    """Force graph nodes to use mock LLM path (matches many integration tests)."""
    monkeypatch.setattr("server.agent.nodes._use_mock_llm", lambda: True)
