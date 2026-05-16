"""
Multi-agent system.

Exports the two things the rest of the app needs:
    AgentRouter  — look up an agent config by ID
    ConversationStore — manage isolated conversation histories per session + agent
"""

from assistant.agents.router import AgentRouter
from assistant.agents.store import ConversationStore

__all__ = ["AgentRouter", "ConversationStore"]
