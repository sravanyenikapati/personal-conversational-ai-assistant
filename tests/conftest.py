"""
Pytest shared fixtures.

These fixtures are available in all test files automatically.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """
    Set dummy environment variables for all tests.
    Prevents tests from accidentally using real API keys.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-key-for-testing-only")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake-key-for-testing-only")
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")  # keep test output clean
    yield


@pytest.fixture
def fake_openai_response():
    """A typical OpenAI chat completion response dict for mocking."""
    return {
        "id": "chatcmpl-test",
        "choices": [
            {
                "message": {"role": "assistant", "content": "This is a test response."},
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
    }
