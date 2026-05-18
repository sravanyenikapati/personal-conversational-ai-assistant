"""
Tests for Phase 4: Custom Agent Builder.

Coverage:
  - CustomAgentStore CRUD (create, list, get, update, delete)
  - system_prompt auto-generation
  - AgentRouter with custom agents (lookup, list_all, __contains__)
  - FastAPI endpoints via TestClient (full HTTP round-trip)
  - Persistence: agents survive store reload from the same file
  - 404 handling for unknown custom agent IDs
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assistant.agents.custom_store import CustomAgent, CustomAgentStore
from assistant.agents.router import AgentRouter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_store(tmp_path: Path) -> CustomAgentStore:
    """A CustomAgentStore backed by a temp file — isolated per test."""
    return CustomAgentStore(data_file=tmp_path / "custom_agents.json")


@pytest.fixture()
def sample_agent(tmp_store: CustomAgentStore) -> CustomAgent:
    """A single agent pre-created in the store."""
    return tmp_store.create(
        name="Chef Bot",
        emoji="🍳",
        description="Recipes and cooking tips",
        personality="Enthusiastic and encouraging",
        knowledge="Italian and Indian cuisine, vegetarian cooking",
    )


@pytest.fixture()
def api_client(tmp_path: Path):
    """
    FastAPI TestClient wired to a CustomAgentStore backed by a temp file.

    We patch the module-level _custom_store and _router in server.py so
    every request goes through a clean, isolated store.
    """
    import assistant.api.server as server_module
    from assistant.agents.router import AgentRouter

    tmp_store = CustomAgentStore(data_file=tmp_path / "api_custom_agents.json")
    original_store = server_module._custom_store
    original_router = server_module._router

    server_module._custom_store = tmp_store
    server_module._router = AgentRouter(custom_store=tmp_store)

    client = TestClient(server_module.app, raise_server_exceptions=True)
    yield client

    # Restore originals so other tests are not affected
    server_module._custom_store = original_store
    server_module._router = original_router


# ---------------------------------------------------------------------------
# CustomAgentStore unit tests
# ---------------------------------------------------------------------------


class TestCustomAgentStore:
    def test_create_returns_agent_with_generated_id(self, tmp_store):
        agent = tmp_store.create(
            name="Test Bot",
            emoji="🤖",
            description="A test agent",
            personality="Calm and factual",
            knowledge="General knowledge",
        )
        assert agent.id.startswith("custom_")
        assert agent.name == "Test Bot"
        assert agent.emoji == "🤖"

    def test_list_all_empty_on_fresh_store(self, tmp_store):
        assert tmp_store.list_all() == []

    def test_list_all_returns_agents_by_creation_order(self, tmp_store):
        a = tmp_store.create(
            name="Alpha", emoji="🅰️", description="First",
            personality="p", knowledge="k",
        )
        b = tmp_store.create(
            name="Beta", emoji="🅱️", description="Second",
            personality="p", knowledge="k",
        )
        agents = tmp_store.list_all()
        assert [ag.id for ag in agents] == [a.id, b.id]

    def test_get_existing_agent(self, tmp_store, sample_agent):
        found = tmp_store.get(sample_agent.id)
        assert found is not None
        assert found.name == "Chef Bot"

    def test_get_unknown_returns_none(self, tmp_store):
        assert tmp_store.get("custom_doesnotexist") is None

    def test_update_single_field(self, tmp_store, sample_agent):
        updated = tmp_store.update(sample_agent.id, name="Super Chef")
        assert updated is not None
        assert updated.name == "Super Chef"
        assert updated.emoji == "🍳"  # unchanged

    def test_update_multiple_fields(self, tmp_store, sample_agent):
        updated = tmp_store.update(
            sample_agent.id,
            name="Pro Chef",
            emoji="👨‍🍳",
            personality="Serious and precise",
        )
        assert updated.name == "Pro Chef"
        assert updated.emoji == "👨‍🍳"
        assert updated.personality == "Serious and precise"

    def test_update_unknown_returns_none(self, tmp_store):
        result = tmp_store.update("custom_ghost", name="Ghost")
        assert result is None

    def test_delete_existing_agent(self, tmp_store, sample_agent):
        deleted = tmp_store.delete(sample_agent.id)
        assert deleted is True
        assert tmp_store.get(sample_agent.id) is None
        assert len(tmp_store.list_all()) == 0

    def test_delete_unknown_returns_false(self, tmp_store):
        assert tmp_store.delete("custom_ghost") is False

    def test_contains_operator(self, tmp_store, sample_agent):
        assert sample_agent.id in tmp_store
        assert "custom_ghost" not in tmp_store

    def test_len(self, tmp_store, sample_agent):
        assert len(tmp_store) == 1
        tmp_store.create(
            name="Bot 2", emoji="🤖", description="Second bot",
            personality="p", knowledge="k",
        )
        assert len(tmp_store) == 2

    def test_persistence_across_reloads(self, tmp_path):
        """Agents written to disk survive a new store instance loading the same file."""
        file = tmp_path / "agents.json"
        store_a = CustomAgentStore(data_file=file)
        agent = store_a.create(
            name="Persistent Bot", emoji="💾", description="Survives restart",
            personality="Reliable", knowledge="Databases",
        )
        # Create a new store instance from the same file
        store_b = CustomAgentStore(data_file=file)
        found = store_b.get(agent.id)
        assert found is not None
        assert found.name == "Persistent Bot"

    def test_json_file_is_valid_json(self, tmp_path, tmp_store, sample_agent):
        file = tmp_path / "custom_agents.json"
        data = json.loads(file.read_text())
        assert isinstance(data, list)
        assert data[0]["id"] == sample_agent.id


# ---------------------------------------------------------------------------
# CustomAgent.system_prompt tests
# ---------------------------------------------------------------------------


class TestSystemPromptGeneration:
    def test_system_prompt_contains_name(self, sample_agent):
        assert "Chef Bot" in sample_agent.system_prompt

    def test_system_prompt_contains_personality(self, sample_agent):
        assert "Enthusiastic" in sample_agent.system_prompt

    def test_system_prompt_contains_knowledge(self, sample_agent):
        assert "Italian" in sample_agent.system_prompt

    def test_system_prompt_enforces_english_and_no_markdown(self, sample_agent):
        prompt = sample_agent.system_prompt
        assert "English only" in prompt
        assert "markdown" in prompt


# ---------------------------------------------------------------------------
# AgentRouter with custom agents
# ---------------------------------------------------------------------------


class TestAgentRouterWithCustom:
    def test_get_builtin_agent(self, tmp_store):
        router = AgentRouter(custom_store=tmp_store)
        config = router.get("general")
        assert config.id == "general"

    def test_get_custom_agent(self, tmp_store, sample_agent):
        router = AgentRouter(custom_store=tmp_store)
        found = router.get(sample_agent.id)
        assert found.id == sample_agent.id
        assert found.name == "Chef Bot"

    def test_get_unknown_raises_key_error(self, tmp_store):
        router = AgentRouter(custom_store=tmp_store)
        with pytest.raises(KeyError):
            router.get("custom_ghost")

    def test_list_all_includes_custom_after_builtins(self, tmp_store, sample_agent):
        router = AgentRouter(custom_store=tmp_store)
        all_ids = [a.id for a in router.list_all()]
        builtin_ids = ["general", "health", "finance", "legal", "career",
                       "tutor", "travel", "tech", "creative"]
        # Built-ins come first in order
        for i, bid in enumerate(builtin_ids):
            assert all_ids[i] == bid
        # Custom agent appended at the end
        assert sample_agent.id in all_ids
        assert all_ids.index(sample_agent.id) > all_ids.index("creative")

    def test_contains_custom_agent(self, tmp_store, sample_agent):
        router = AgentRouter(custom_store=tmp_store)
        assert sample_agent.id in router
        assert "custom_ghost" not in router

    def test_len_includes_custom(self, tmp_store, sample_agent):
        router = AgentRouter(custom_store=tmp_store)
        assert len(router) == 10  # 9 built-ins + 1 custom


# ---------------------------------------------------------------------------
# FastAPI endpoint tests
# ---------------------------------------------------------------------------


class TestCustomAgentEndpoints:
    def test_create_custom_agent(self, api_client):
        resp = api_client.post("/custom-agents", json={
            "name": "Study Buddy",
            "emoji": "📖",
            "description": "Helps with studying",
            "personality": "Patient and encouraging",
            "knowledge": "Mathematics and physics",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Study Buddy"
        assert data["emoji"] == "📖"
        assert data["is_custom"] is True
        assert data["id"].startswith("custom_")

    def test_list_custom_agents_empty(self, api_client):
        resp = api_client.get("/custom-agents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_custom_agents_after_create(self, api_client):
        api_client.post("/custom-agents", json={
            "name": "Bot A", "emoji": "🅰️", "description": "First",
            "personality": "p", "knowledge": "k",
        })
        api_client.post("/custom-agents", json={
            "name": "Bot B", "emoji": "🅱️", "description": "Second",
            "personality": "p", "knowledge": "k",
        })
        resp = api_client.get("/custom-agents")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_custom_agent(self, api_client):
        created = api_client.post("/custom-agents", json={
            "name": "Fetch Me", "emoji": "🔍", "description": "Fetchable",
            "personality": "p", "knowledge": "k",
        }).json()
        resp = api_client.get(f"/custom-agents/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Fetch Me"

    def test_get_custom_agent_not_found(self, api_client):
        resp = api_client.get("/custom-agents/custom_ghost")
        assert resp.status_code == 404

    def test_update_custom_agent(self, api_client):
        created = api_client.post("/custom-agents", json={
            "name": "Old Name", "emoji": "🔧", "description": "Will update",
            "personality": "p", "knowledge": "k",
        }).json()
        resp = api_client.put(f"/custom-agents/{created['id']}", json={
            "name": "New Name",
            "emoji": "✨",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["emoji"] == "✨"
        assert data["description"] == "Will update"  # unchanged

    def test_update_custom_agent_not_found(self, api_client):
        resp = api_client.put("/custom-agents/custom_ghost", json={"name": "Ghost"})
        assert resp.status_code == 404

    def test_delete_custom_agent(self, api_client):
        created = api_client.post("/custom-agents", json={
            "name": "Delete Me", "emoji": "🗑️", "description": "Gone soon",
            "personality": "p", "knowledge": "k",
        }).json()
        resp = api_client.delete(f"/custom-agents/{created['id']}")
        assert resp.status_code == 204
        # Confirm it's gone
        resp2 = api_client.get(f"/custom-agents/{created['id']}")
        assert resp2.status_code == 404

    def test_delete_custom_agent_not_found(self, api_client):
        resp = api_client.delete("/custom-agents/custom_ghost")
        assert resp.status_code == 404

    def test_agents_list_includes_custom(self, api_client):
        """GET /agents should return built-ins + custom agents."""
        api_client.post("/custom-agents", json={
            "name": "My Agent", "emoji": "⭐", "description": "Custom one",
            "personality": "Helpful", "knowledge": "Everything",
        })
        resp = api_client.get("/agents")
        assert resp.status_code == 200
        ids = [a["id"] for a in resp.json()]
        assert "general" in ids
        assert any(i.startswith("custom_") for i in ids)

    def test_health_includes_custom_agent_count(self, api_client):
        api_client.post("/custom-agents", json={
            "name": "Count Me", "emoji": "🔢", "description": "d",
            "personality": "p", "knowledge": "k",
        })
        resp = api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["custom_agent_count"] == 1
