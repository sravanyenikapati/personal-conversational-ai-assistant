"""
Agent Router — look up agent configurations by ID.

The router is the single source of truth for which agents exist.
Both the API layer and the desktop UI use it to resolve agent IDs.

Usage:
    router = AgentRouter()
    config = router.get("health")       # raises KeyError if unknown
    all_agents = router.list_all()      # ordered list for the UI selector
"""

from __future__ import annotations

from assistant.agents.prompts import AGENTS, AGENTS_ORDERED, AgentConfig
from assistant.logger import get_logger

log = get_logger(__name__)


class AgentRouter:
    """
    Resolves agent IDs to AgentConfig objects.

    Lightweight — no state, just a wrapper around the AGENTS registry.
    Safe to instantiate once at startup and share across the application.
    """

    def get(self, agent_id: str) -> AgentConfig:
        """
        Return the AgentConfig for the given agent_id.

        Raises:
            KeyError: if agent_id is not registered.
        """
        config = AGENTS.get(agent_id)
        if config is None:
            valid = ", ".join(f'"{k}"' for k in AGENTS)
            raise KeyError(f"Unknown agent_id {agent_id!r}. Valid options are: {valid}.")
        return config

    def list_all(self) -> list[AgentConfig]:
        """Return all agents in display order (for the Flutter agent selector)."""
        return list(AGENTS_ORDERED)

    def ids(self) -> list[str]:
        """Return all valid agent IDs."""
        return [a.id for a in AGENTS_ORDERED]

    def __contains__(self, agent_id: str) -> bool:
        return agent_id in AGENTS

    def __len__(self) -> int:
        return len(AGENTS)
