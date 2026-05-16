"""
Tests for the Phase 2 multi-agent system.

Covers:
  - Agent registry completeness and correctness
  - AgentRouter get / list / contains
  - ConversationStore chat, clear, isolation between agents
  - FastAPI endpoints: GET /agents, GET /agents/{id}, POST /chat, DELETE /chat
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ── Agent Registry Tests ───────────────────────────────────────────────────────


class TestAgentPrompts:
    def test_all_nine_agents_present(self):
        from assistant.agents.prompts import AGENTS

        expected_ids = {
            "general",
            "health",
            "finance",
            "legal",
            "career",
            "tutor",
            "travel",
            "tech",
            "creative",
        }
        assert set(AGENTS.keys()) == expected_ids

    def test_every_agent_has_non_empty_system_prompt(self):
        from assistant.agents.prompts import AGENTS

        for agent_id, config in AGENTS.items():
            assert config.system_prompt.strip(), f"Agent '{agent_id}' has an empty system prompt."

    def test_every_agent_has_required_fields(self):
        from assistant.agents.prompts import AGENTS

        for agent_id, config in AGENTS.items():
            assert config.id == agent_id
            assert config.name
            assert config.emoji
            assert config.description
            assert len(config.emoji) >= 1

    def test_disclaimer_agents_have_disclaimer(self):
        """Health, Finance, and Legal agents must have disclaimers."""
        from assistant.agents.prompts import AGENTS

        for agent_id in ("health", "finance", "legal"):
            assert AGENTS[agent_id].disclaimer, f"Agent '{agent_id}' must have a disclaimer."

    def test_general_and_career_agents_have_no_disclaimer(self):
        """General-purpose agents should not have disclaimers."""
        from assistant.agents.prompts import AGENTS

        for agent_id in ("general", "career", "tutor", "travel", "tech", "creative"):
            assert AGENTS[agent_id].disclaimer is None, (
                f"Agent '{agent_id}' should not have a disclaimer."
            )

    def test_ordered_list_matches_registry(self):
        from assistant.agents.prompts import AGENTS, AGENTS_ORDERED

        assert len(AGENTS_ORDERED) == len(AGENTS)
        for config in AGENTS_ORDERED:
            assert config.id in AGENTS


# ── AgentRouter Tests ─────────────────────────────────────────────────────────


class TestAgentRouter:
    def test_get_known_agent(self):
        from assistant.agents.router import AgentRouter

        router = AgentRouter()
        config = router.get("general")
        assert config.id == "general"
        assert config.name == "General Assistant"

    def test_get_all_nine_agents(self):
        from assistant.agents.router import AgentRouter

        router = AgentRouter()
        for agent_id in (
            "general",
            "health",
            "finance",
            "legal",
            "career",
            "tutor",
            "travel",
            "tech",
            "creative",
        ):
            config = router.get(agent_id)
            assert config.id == agent_id

    def test_get_unknown_agent_raises_key_error(self):
        from assistant.agents.router import AgentRouter

        router = AgentRouter()
        with pytest.raises(KeyError, match="unknown_agent"):
            router.get("unknown_agent")

    def test_list_all_returns_nine_agents(self):
        from assistant.agents.router import AgentRouter

        router = AgentRouter()
        agents = router.list_all()
        assert len(agents) == 9

    def test_list_all_first_is_general(self):
        """General agent should be first in display order."""
        from assistant.agents.router import AgentRouter

        router = AgentRouter()
        assert router.list_all()[0].id == "general"

    def test_ids_returns_list_of_strings(self):
        from assistant.agents.router import AgentRouter

        router = AgentRouter()
        ids = router.ids()
        assert isinstance(ids, list)
        assert all(isinstance(i, str) for i in ids)
        assert len(ids) == 9

    def test_contains_known_agent(self):
        from assistant.agents.router import AgentRouter

        router = AgentRouter()
        assert "health" in router

    def test_not_contains_unknown_agent(self):
        from assistant.agents.router import AgentRouter

        router = AgentRouter()
        assert "nonexistent" not in router

    def test_len_is_nine(self):
        from assistant.agents.router import AgentRouter

        router = AgentRouter()
        assert len(router) == 9


# ── ConversationStore Tests ───────────────────────────────────────────────────


class TestConversationStore:
    def _mock_provider(self, reply: str = "Test reply") -> MagicMock:
        provider = MagicMock()
        provider.complete.return_value = reply
        return provider

    def test_chat_returns_reply(self):
        from assistant.agents.store import ConversationStore

        store = ConversationStore(provider=self._mock_provider("Hello!"))
        reply, count = store.chat(
            session_id="sess-1",
            agent_id="general",
            system_prompt="You are a helpful assistant.",
            message="Hi there",
        )
        assert reply == "Hello!"
        assert count == 2  # user + assistant

    def test_empty_message_returns_empty(self):
        from assistant.agents.store import ConversationStore

        provider = self._mock_provider()
        store = ConversationStore(provider=provider)
        reply, count = store.chat(
            session_id="sess-1",
            agent_id="general",
            system_prompt="You are helpful.",
            message="   ",
        )
        assert reply == ""
        assert count == 0
        provider.complete.assert_not_called()

    def test_agents_have_isolated_histories(self):
        """Switching agents within the same session must NOT share context."""
        from assistant.agents.store import ConversationStore

        provider = self._mock_provider("Reply")
        store = ConversationStore(provider=provider)

        # Chat with general agent
        store.chat(
            session_id="sess-1",
            agent_id="general",
            system_prompt="General prompt.",
            message="Hello general",
        )
        store.chat(
            session_id="sess-1",
            agent_id="general",
            system_prompt="General prompt.",
            message="How are you?",
        )

        # Health agent in same session should start fresh
        health_count = store.message_count(session_id="sess-1", agent_id="health")
        assert health_count == 0

        store.chat(
            session_id="sess-1",
            agent_id="health",
            system_prompt="Health prompt.",
            message="Tell me about sleep",
        )
        health_count = store.message_count(session_id="sess-1", agent_id="health")
        assert health_count == 2  # just the one exchange

        general_count = store.message_count(session_id="sess-1", agent_id="general")
        assert general_count == 4  # two exchanges, general is unaffected

    def test_sessions_have_isolated_histories(self):
        """Different session IDs must have completely separate histories."""
        from assistant.agents.store import ConversationStore

        provider = self._mock_provider("Reply")
        store = ConversationStore(provider=provider)

        store.chat(
            session_id="sess-A",
            agent_id="general",
            system_prompt="Prompt.",
            message="Message from session A",
        )

        count_b = store.message_count(session_id="sess-B", agent_id="general")
        assert count_b == 0

    def test_clear_resets_one_agent(self):
        from assistant.agents.store import ConversationStore

        provider = self._mock_provider("Reply")
        store = ConversationStore(provider=provider)

        store.chat(
            session_id="sess-1", agent_id="general", system_prompt="Prompt.", message="Hello"
        )
        store.chat(session_id="sess-1", agent_id="health", system_prompt="Health.", message="Hi")

        store.clear(session_id="sess-1", agent_id="general")

        assert store.message_count(session_id="sess-1", agent_id="general") == 0
        # Health agent is unaffected
        assert store.message_count(session_id="sess-1", agent_id="health") == 2

    def test_clear_session_removes_all_agents(self):
        from assistant.agents.store import ConversationStore

        provider = self._mock_provider("Reply")
        store = ConversationStore(provider=provider)

        store.chat(session_id="sess-1", agent_id="general", system_prompt="General.", message="Hi")
        store.chat(
            session_id="sess-1", agent_id="finance", system_prompt="Finance.", message="Budget help"
        )

        store.clear_session(session_id="sess-1")

        assert store.message_count(session_id="sess-1", agent_id="general") == 0
        assert store.message_count(session_id="sess-1", agent_id="finance") == 0

    def test_provider_error_returns_friendly_message(self):
        from assistant.agents.store import ConversationStore

        provider = MagicMock()
        provider.complete.side_effect = Exception("API timeout")
        store = ConversationStore(provider=provider)

        reply, _ = store.chat(
            session_id="sess-1",
            agent_id="general",
            system_prompt="Prompt.",
            message="Hello",
        )
        assert "sorry" in reply.lower() or "issue" in reply.lower()

    def test_session_count_tracks_active_pairs(self):
        from assistant.agents.store import ConversationStore

        provider = self._mock_provider("Reply")
        store = ConversationStore(provider=provider)

        assert store.session_count() == 0
        store.chat(session_id="s1", agent_id="general", system_prompt="P.", message="Hi")
        assert store.session_count() == 1
        store.chat(session_id="s1", agent_id="health", system_prompt="H.", message="Hi")
        assert store.session_count() == 2


# ── FastAPI Endpoint Tests ────────────────────────────────────────────────────


@pytest.fixture
def client():
    """TestClient with all AI provider calls mocked out."""
    with patch("assistant.api.server._build_provider") as mock_build:
        mock_provider = MagicMock()
        mock_provider.complete.return_value = "Mocked reply from the AI."
        mock_build.return_value = mock_provider

        # Re-import to pick up the mocked provider
        import importlib

        import assistant.api.server as server_module

        importlib.reload(server_module)

        from fastapi.testclient import TestClient

        yield TestClient(server_module.app)


@pytest.fixture(autouse=False)
def api_client():
    """FastAPI TestClient with a mocked store — no real AI calls."""
    from fastapi.testclient import TestClient

    import assistant.api.server as srv

    mock_store = MagicMock()
    mock_store.session_count.return_value = 0
    with patch("assistant.api.server._store", mock_store):
        yield TestClient(srv.app), mock_store


class TestHealthEndpoint:
    def test_health_returns_ok(self, api_client):
        tc, _ = api_client
        resp = tc.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "provider" in data
        assert "agent_count" in data
        assert data["agent_count"] == 9


class TestAgentsEndpoint:
    def test_list_agents_returns_nine(self, api_client):
        tc, _ = api_client
        resp = tc.get("/agents")
        assert resp.status_code == 200
        assert len(resp.json()) == 9

    def test_list_agents_first_is_general(self, api_client):
        tc, _ = api_client
        resp = tc.get("/agents")
        assert resp.json()[0]["id"] == "general"

    def test_get_agent_health(self, api_client):
        tc, _ = api_client
        resp = tc.get("/agents/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "health"
        assert data["has_disclaimer"] is True
        assert data["disclaimer"] is not None

    def test_get_unknown_agent_returns_404(self, api_client):
        tc, _ = api_client
        resp = tc.get("/agents/nonexistent")
        assert resp.status_code == 404


class TestChatEndpoint:
    def test_chat_returns_reply_and_session_id(self, api_client):
        tc, mock_store = api_client
        mock_store.chat.return_value = ("Hi! How can I help?", 2)
        resp = tc.post("/chat", json={"message": "Hello", "agent_id": "general"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] == "Hi! How can I help?"
        assert data["agent_id"] == "general"
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_chat_reuses_provided_session_id(self, api_client):
        tc, mock_store = api_client
        mock_store.chat.return_value = ("Reply", 2)
        session_id = "my-fixed-session-id"
        resp = tc.post(
            "/chat", json={"message": "Hello", "agent_id": "general", "session_id": session_id}
        )
        assert resp.json()["session_id"] == session_id

    def test_chat_invalid_agent_id_returns_400(self, api_client):
        tc, _ = api_client
        resp = tc.post("/chat", json={"message": "Hello", "agent_id": "fake_agent"})
        assert resp.status_code == 400

    def test_chat_default_agent_is_general(self, api_client):
        tc, mock_store = api_client
        mock_store.chat.return_value = ("Reply", 2)
        resp = tc.post("/chat", json={"message": "Hello"})
        assert resp.json()["agent_id"] == "general"

    def test_chat_health_agent_returns_disclaimer(self, api_client):
        tc, mock_store = api_client
        mock_store.chat.return_value = ("Drink water.", 2)
        resp = tc.post("/chat", json={"message": "Tips for back pain?", "agent_id": "health"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["disclaimer"] is not None
        assert len(data["disclaimer"]) > 0

    def test_chat_general_agent_has_no_disclaimer(self, api_client):
        tc, mock_store = api_client
        mock_store.chat.return_value = ("Sure!", 2)
        resp = tc.post("/chat", json={"message": "Hello", "agent_id": "general"})
        assert resp.json()["disclaimer"] is None

    def test_chat_conversation_history_grows(self, api_client):
        tc, mock_store = api_client
        mock_store.chat.side_effect = [("Reply 1", 2), ("Reply 2", 4)]
        session_id = "history-test-session"
        resp1 = tc.post(
            "/chat", json={"message": "Hello", "agent_id": "general", "session_id": session_id}
        )
        resp2 = tc.post(
            "/chat",
            json={"message": "How are you?", "agent_id": "general", "session_id": session_id},
        )
        assert resp2.json()["message_count"] > resp1.json()["message_count"]

    def test_clear_chat_resets_history(self, api_client):
        tc, mock_store = api_client
        mock_store.chat.side_effect = [("Hello reply", 4), ("Fresh reply", 2)]
        session_id = "clear-test-session"
        tc.post("/chat", json={"message": "Hello", "agent_id": "general", "session_id": session_id})
        del_resp = tc.delete(f"/chat?session_id={session_id}&agent_id=general")
        assert del_resp.status_code == 200
        assert del_resp.json()["cleared"] is True
        resp = tc.post(
            "/chat",
            json={"message": "Fresh start", "agent_id": "general", "session_id": session_id},
        )
        assert resp.json()["message_count"] == 2
