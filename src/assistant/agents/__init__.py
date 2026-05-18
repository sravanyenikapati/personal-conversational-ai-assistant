"""
Multi-agent system.

Exports:
    AgentRouter       -- look up an agent config by ID (built-ins + custom)
    ConversationStore -- manage isolated conversation histories per session + agent
    CustomAgentStore  -- CRUD persistence for user-created agents
"""

from assistant.agents.custom_store import CustomAgentStore
from assistant.agents.router import AgentRouter
from assistant.agents.store import ConversationStore

__all__ = ["AgentRouter", "ConversationStore", "CustomAgentStore"]
