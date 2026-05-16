"""
Tests for the AI Brain layer.

All OpenAI API calls are mocked — these tests run offline with no API key needed.
"""

from unittest.mock import MagicMock, patch

from assistant.core.brain import Brain, OpenAIProvider


class TestOpenAIProvider:
    @patch("assistant.core.brain.OpenAI")
    def test_complete_returns_string(self, mock_openai_cls):
        """Provider.complete() should return the assistant message content."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Hello, world!"
        mock_response.usage.total_tokens = 18
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider()
        result = provider.complete([{"role": "user", "content": "Hi"}])

        assert result == "Hello, world!"

    @patch("assistant.core.brain.OpenAI")
    def test_complete_strips_whitespace(self, mock_openai_cls):
        """Provider.complete() should strip leading/trailing whitespace."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "   spaced response   "
        mock_response.usage = None
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider()
        result = provider.complete([{"role": "user", "content": "Hi"}])
        assert result == "spaced response"

    @patch("assistant.core.brain.OpenAI")
    def test_complete_handles_none_content(self, mock_openai_cls):
        """Provider.complete() should handle None content gracefully."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = None
        mock_response.usage = None
        mock_client.chat.completions.create.return_value = mock_response

        provider = OpenAIProvider()
        result = provider.complete([])
        assert result == ""


class TestBrain:
    @patch("assistant.core.brain.OpenAI")
    def test_chat_returns_reply(self, mock_openai_cls):
        """Brain.chat() should return the AI reply."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "I'm doing great!"
        mock_response.usage.total_tokens = 20
        mock_client.chat.completions.create.return_value = mock_response

        brain = Brain()
        reply = brain.chat("How are you?")
        assert reply == "I'm doing great!"

    @patch("assistant.core.brain.OpenAI")
    def test_chat_empty_input_returns_empty(self, mock_openai_cls):
        """Brain.chat() with empty input should return '' without calling the API."""
        mock_openai_cls.return_value = MagicMock()
        brain = Brain()
        result = brain.chat("   ")
        assert result == ""
        mock_openai_cls.return_value.chat.completions.create.assert_not_called()

    @patch("assistant.core.brain.OpenAI")
    def test_chat_updates_history(self, mock_openai_cls):
        """Brain.chat() should add both user and assistant messages to history."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Sure!"
        mock_response.usage.total_tokens = 10
        mock_client.chat.completions.create.return_value = mock_response

        brain = Brain()
        assert len(brain.history) == 0
        brain.chat("Can you help me?")
        assert len(brain.history) == 2  # user + assistant

    @patch("assistant.core.brain.OpenAI")
    def test_reset_clears_history(self, mock_openai_cls):
        """Brain.reset() should clear all conversation history."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Yes!"
        mock_response.usage.total_tokens = 5
        mock_client.chat.completions.create.return_value = mock_response

        brain = Brain()
        brain.chat("Hello")
        assert len(brain.history) > 0
        brain.reset()
        assert len(brain.history) == 0

    @patch("assistant.core.brain.OpenAI")
    def test_chat_handles_provider_exception(self, mock_openai_cls):
        """Brain.chat() should return a friendly error message on API failure."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API timeout")

        brain = Brain()
        reply = brain.chat("Tell me something")
        assert "sorry" in reply.lower() or "issue" in reply.lower()
