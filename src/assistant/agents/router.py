"""
Agent Router -- resolves agent IDs to config objects.

Built-in agents (prompts.py) are checked first.
Custom agents (CustomAgentStore) are checked on miss.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from assistant.agents.custom_store import CustomAgent
from assistant.agents.prompts import AGENTS, AGENTS_ORDERED, AgentConfig
from assistant.logger import get_logger

if TYPE_CHECKING:
    from assistant.agents.custom_store import CustomAgentStore

log = get_logger(__name__)


class AgentRouter:
    """Resolves agent IDs to config-like objects (built-in + custom)."""

    def __init__(self, custom_store: "CustomAgentStore | None" = None) -> None:
        self._custom = custom_store

    def get(self, agent_id: str) -> "AgentConfig | CustomAgent":
        config = AGENTS.get(agent_id)
        if config is not None:
            return config
        if self._custom is not None:
            custom = self._custom.get(agent_id)
            if custom is not None:
                return custom
        valid = ", ".join(f'"{k}"' for k in AGENTS)
        raise KeyError(
            f"Unknown agent_id {agent_id!r}. "
            f"Built-in options: {valid}. "
            "Custom agents can be created via POST /custom-agents."
        )

    def list_all(self) -> "list[AgentConfig | CustomAgent]":
        agents: list = list(AGENTS_ORDERED)
        if self._custom is not None:
            agents.extend(self._custom.list_all())
        return agents

    def ids(self) -> list:
        return [a.id for a in self.list_all()]

    def __contains__(self, agent_id: str) -> bool:
        if agent_id in AGENTS:
            return True
        if self._custom is not None and agent_id in self._custom:
            return True
        return False

    def __len__(self) -> int:
        base = len(AGENTS)
        if self._custom is not None:
            base += len(self._custom)
        return base
