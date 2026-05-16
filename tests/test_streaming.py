"""
Tests for the Phase 2.5 streaming pipeline.

Covers:
  - SentenceSplitter: feed, flush, edge cases
  - Brain.stream_chat: yields sentences, handles errors, updates history
  - ConversationStore.stream_chat: yields tokens, stores history
  - POST /chat/stream SSE endpoint: 200, correct content-type, 400 on bad agent
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from assistant.core.streaming import SentenceSplitter

# ── SentenceSplitter Tests ────────────────────────────────────────────────────


class TestSentenceSplitter:
    def test_single_sentence_returned_on_period(self):
        s = SentenceSplitter()
        result = s.feed("Hello there. ")
        assert result == ["Hello there."]

    def test_no_yield_before_sentence_end(self):
        s = SentenceSplitter()
        result = s.feed("Hello")
        assert result == []

    def test_multiple_sentences_in_one_feed(self):
        s = SentenceSplitter()
        result = s.feed("Hello there. How are you? I am fine. ")
        assert len(result) == 3
        assert result[0] == "Hello there."
        assert result[1] == "How are you?"
        assert result[2] == "I am fine."

    def test_flush_returns_remaining_text(self):
        s = SentenceSplitter()
        s.feed("This has no period")
        remainder = s.flush()
        assert remainder == "This has no period"

    def test_flush_empty_after_full_sentence(self):
        s = SentenceSplitter()
        s.feed("Done. ")
        s.flush()
        assert s.flush() == ""

    def test_exclamation_and_question_marks(self):
        s = SentenceSplitter()
        result = s.feed("Wow! Really? Yes. ")
        assert len(result) == 3
        assert result[0] == "Wow!"
        assert result[1] == "Really?"
        assert result[2] == "Yes."

    def test_tokens_accumulate_across_calls(self):
        s = SentenceSplitter()
        tokens = list("Hello world. ")
        sentences = []
        for token in tokens:
            sentences.extend(s.feed(token))
        assert sentences == ["Hello world."]

    def test_reset_clears_buffer(self):
        s = SentenceSplitter()
        s.feed("Incomplete")
        s.reset()
        assert s.flush() == ""

    def test_short_sentences_are_yielded(self):
        s = SentenceSplitter()
        result = s.feed("OK. Got it. ")
        assert len(result) == 2
        assert result[0] == "OK."
        assert result[1] == "Got it."


# ── Brain.stream_chat Tests ───────────────────────────────────────────────────


class TestBrainStreamChat:
    def _mock_provider(self, chunks):
        provider = MagicMock()
        provider.complete.return_value = "".join(chunks)
        provider.stream_complete.return_value = iter(chunks)
        return provider

    def test_stream_chat_yields_sentences(self):
        from assistant.core.brain import Brain

        provider = self._mock_provider(["Hello there. ", "How can I help you today? "])
        brain = Brain(system_prompt="You are helpful.", provider=provider)
        sentences = list(brain.stream_chat("Hi"))
        assert len(sentences) >= 1
        combined = " ".join(sentences)
        assert "Hello" in combined

    def test_stream_chat_empty_input_yields_nothing(self):
        from assistant.core.brain import Brain

        provider = self._mock_provider([])
        brain = Brain(system_prompt="You are helpful.", provider=provider)
        result = list(brain.stream_chat("   "))
        assert result == []
        provider.stream_complete.assert_not_called()

    def test_stream_chat_stores_full_reply_in_history(self):
        from assistant.core.brain import Brain

        provider = self._mock_provider(["Hello. ", "I am here. "])
        brain = Brain(system_prompt="You are helpful.", provider=provider)
        list(brain.stream_chat("Hi"))
        messages = brain.history.get_messages()
        assert any(m["role"] == "assistant" for m in messages)
        assistant_msg = next(m for m in messages if m["role"] == "assistant")
        assert "Hello" in assistant_msg["content"]

    def test_stream_chat_error_yields_friendly_message(self):
        from assistant.core.brain import Brain

        provider = MagicMock()
        provider.stream_complete.side_effect = Exception("Network error")
        brain = Brain(system_prompt="You are helpful.", provider=provider)
        result = list(brain.stream_chat("Hi"))
        assert len(result) == 1
        assert "sorry" in result[0].lower() or "issue" in result[0].lower()

    def test_stream_chat_error_removes_user_message_from_history(self):
        from assistant.core.brain import Brain

        provider = MagicMock()
        provider.stream_complete.side_effect = Exception("Timeout")
        brain = Brain(system_prompt="You are helpful.", provider=provider)
        list(brain.stream_chat("Hi"))
        messages = brain.history.get_messages()
        user_messages = [m for m in messages if m["role"] == "user"]
        assert len(user_messages) == 0


# ── ConversationStore.stream_chat Tests ──────────────────────────────────────


class TestConversationStoreStreamChat:
    def _mock_provider(self, chunks):
        provider = MagicMock()
        provider.complete.return_value = "".join(chunks)
        provider.stream_complete.return_value = iter(chunks)
        return provider

    def test_stream_chat_yields_tokens(self):
        from assistant.agents.store import ConversationStore

        provider = self._mock_provider(["Hello ", "world."])
        store = ConversationStore(provider=provider)
        tokens = list(
            store.stream_chat(
                session_id="s1",
                agent_id="general",
                system_prompt="Prompt.",
                message="Hi",
            )
        )
        assert tokens == ["Hello ", "world."]

    def test_stream_chat_empty_message_yields_nothing(self):
        from assistant.agents.store import ConversationStore

        provider = self._mock_provider([])
        store = ConversationStore(provider=provider)
        tokens = list(
            store.stream_chat(
                session_id="s1",
                agent_id="general",
                system_prompt="Prompt.",
                message="   ",
            )
        )
        assert tokens == []
        provider.stream_complete.assert_not_called()

    def test_stream_chat_stores_full_reply(self):
        from assistant.agents.store import ConversationStore

        provider = self._mock_provider(["Hello ", "there."])
        store = ConversationStore(provider=provider)
        list(
            store.stream_chat(
                session_id="s1",
                agent_id="general",
                system_prompt="Prompt.",
                message="Hi",
            )
        )
        assert store.message_count(session_id="s1", agent_id="general") == 2

    def test_stream_chat_agents_isolated(self):
        from assistant.agents.store import ConversationStore

        provider = self._mock_provider(["Reply."])
        store = ConversationStore(provider=provider)
        list(
            store.stream_chat(
                session_id="s1",
                agent_id="general",
                system_prompt="Prompt.",
                message="Hi",
            )
        )
        assert store.message_count(session_id="s1", agent_id="health") == 0


# ── POST /chat/stream SSE Endpoint Tests ──────────────────────────────────────


@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient

    import assistant.api.server as srv

    mock_store = MagicMock()
    mock_store.session_count.return_value = 0
    with patch("assistant.api.server._store", mock_store):
        yield TestClient(srv.app), mock_store


class TestChatStreamEndpoint:
    def test_stream_returns_200(self, api_client):
        tc, mock_store = api_client
        mock_store.stream_chat.return_value = iter(["Hello ", "there."])
        resp = tc.post("/chat/stream", json={"message": "Hi", "agent_id": "general"})
        assert resp.status_code == 200

    def test_stream_content_type_is_event_stream(self, api_client):
        tc, mock_store = api_client
        mock_store.stream_chat.return_value = iter([])
        resp = tc.post("/chat/stream", json={"message": "Hi", "agent_id": "general"})
        assert "text/event-stream" in resp.headers["content-type"]

    def test_stream_invalid_agent_returns_400(self, api_client):
        tc, _ = api_client
        resp = tc.post("/chat/stream", json={"message": "Hi", "agent_id": "fake_bot"})
        assert resp.status_code == 400

    def test_stream_response_contains_session_event(self, api_client):
        tc, mock_store = api_client
        mock_store.stream_chat.return_value = iter(["Hi."])
        resp = tc.post("/chat/stream", json={"message": "Hello", "agent_id": "general"})
        events = _parse_sse(resp.text)
        session_events = [e for e in events if e.get("type") == "session"]
        assert len(session_events) == 1
        assert session_events[0]["agent_id"] == "general"
        assert "session_id" in session_events[0]

    def test_stream_response_contains_done_event(self, api_client):
        tc, mock_store = api_client
        mock_store.stream_chat.return_value = iter(["Hi."])
        resp = tc.post("/chat/stream", json={"message": "Hello", "agent_id": "general"})
        events = _parse_sse(resp.text)
        done_events = [e for e in events if e.get("type") == "done"]
        assert len(done_events) == 1

    def test_stream_health_agent_done_event_has_disclaimer(self, api_client):
        tc, mock_store = api_client
        mock_store.stream_chat.return_value = iter(["Drink water."])
        resp = tc.post("/chat/stream", json={"message": "Tips?", "agent_id": "health"})
        events = _parse_sse(resp.text)
        done_event = next(e for e in events if e.get("type") == "done")
        assert done_event["disclaimer"] is not None

    def test_stream_general_agent_done_event_has_no_disclaimer(self, api_client):
        tc, mock_store = api_client
        mock_store.stream_chat.return_value = iter(["Sure!"])
        resp = tc.post("/chat/stream", json={"message": "Hi", "agent_id": "general"})
        events = _parse_sse(resp.text)
        done_event = next(e for e in events if e.get("type") == "done")
        assert done_event["disclaimer"] is None


def _parse_sse(body):
    import json as _json

    events = []
    for line in body.splitlines():
        if line.startswith("data: "):
            try:
                events.append(_json.loads(line[6:]))
            except _json.JSONDecodeError:
                pass
    return events
