"""
Conversation Store — isolated conversation memory per session and agent.

Key design:
  - Each (session_id, agent_id) pair gets its own ConversationHistory.
  - A shared AI provider is injected at construction — one HTTP client for all conversations.
  - Thread-safe: the FastAPI server handles concurrent requests.

Usage:
    provider = _build_provider()
    store = ConversationStore(provider=provider)

    reply, count = store.chat(
        session_id="abc-123",
        agent_id="health",
        system_prompt="...",
        message="What are some good stretches for back pain?",
    )
    store.clear(session_id="abc-123", agent_id="health")
"""

from __future__ import annotations

import threading

from assistant.config import get_settings
from assistant.core.brain import AIProviderProtocol
from assistant.core.conversation import ConversationHistory
from assistant.logger import get_logger

log = get_logger(__name__)


class ConversationStore:
    """
    Manages isolated ConversationHistory objects, keyed by (session_id, agent_id).

    Switching from one agent to another within the same session does NOT share
    conversation context — each agent remembers only its own exchanges.

    A single AI provider is shared across all conversations for efficiency.
    """

    def __init__(self, provider: AIProviderProtocol) -> None:
        self._provider = provider
        self._store: dict[tuple[str, str], ConversationHistory] = {}
        self._lock = threading.Lock()
        settings = get_settings()
        self._max_messages = settings.max_conversation_history
        log.info("ConversationStore initialised.")

    # ── Public API ────────────────────────────────────────────────────────────

    def chat(
        self,
        *,
        session_id: str,
        agent_id: str,
        system_prompt: str,
        message: str,
    ) -> tuple[str, int]:
        """
        Send a user message to a specific agent within a session.

        Creates the conversation history for this (session_id, agent_id) pair
        on first use. Returns (reply, message_count).

        Args:
            session_id:    Client-supplied session identifier (e.g. UUID).
            agent_id:      Which agent to talk to (e.g. "health").
            system_prompt: The agent's system prompt — defines its personality.
            message:       The user's message.

        Returns:
            (reply_string, total_message_count_in_this_conversation)
        """
        if not message.strip():
            return "", 0

        history = self._get_or_create(session_id, agent_id, system_prompt)

        history.add_user_message(message)

        try:
            reply = self._provider.complete(history.get_messages())
        except Exception as exc:
            log.error(f"Provider error [{agent_id}]: {exc}", exc_info=True)
            # Remove the user message we just added so history stays consistent
            history._messages.pop()
            reply = (
                "Sorry, I ran into an issue generating a response. Please try again."
            )

        history.add_assistant_message(reply)
        log.info(
            f"[session={session_id[:8]}] [{agent_id}] "
            f"history={len(history)} messages"
        )
        return reply, len(history)

    def clear(self, *, session_id: str, agent_id: str) -> None:
        """Clear the conversation history for one agent in a session."""
        key = (session_id, agent_id)
        with self._lock:
            if key in self._store:
                self._store[key].clear()
                log.info(f"Cleared [{agent_id}] for session {session_id[:8]}.")

    def clear_session(self, *, session_id: str) -> None:
        """Clear ALL agent histories for an entire session."""
        with self._lock:
            keys_to_remove = [k for k in self._store if k[0] == session_id]
            for key in keys_to_remove:
                del self._store[key]
            log.info(
                f"Cleared session {session_id[:8]} "
                f"({len(keys_to_remove)} agent histories removed)."
            )

    def message_count(self, *, session_id: str, agent_id: str) -> int:
        """Return the number of messages in a specific conversation (0 if not started)."""
        with self._lock:
            history = self._store.get((session_id, agent_id))
            return len(history) if history else 0

    def session_count(self) -> int:
        """Total number of active (session, agent) conversation pairs."""
        with self._lock:
            return len(self._store)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_create(
        self,
        session_id: str,
        agent_id: str,
        system_prompt: str,
    ) -> ConversationHistory:
        key = (session_id, agent_id)
        with self._lock:
            if key not in self._store:
                self._store[key] = ConversationHistory(
                    system_prompt=system_prompt,
                    max_messages=self._max_messages,
                )
                log.debug(
                    f"Created new conversation for "
                    f"[session={session_id[:8]}, agent={agent_id}]."
                )
            return self._store[key]
