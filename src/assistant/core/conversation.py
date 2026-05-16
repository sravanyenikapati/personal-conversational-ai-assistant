"""
Conversation history manager.

Maintains a rolling window of messages for the AI to use as context.
Each message is a dict compatible with the OpenAI and Anthropic message formats.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TypedDict

from assistant.logger import get_logger

log = get_logger(__name__)


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(TypedDict):
    role: str
    content: str


@dataclass
class ConversationHistory:
    """
    Manages a rolling window of conversation messages.

    The system prompt is always kept as the first message.
    Older messages are dropped when the history exceeds max_messages.
    """

    system_prompt: str
    max_messages: int = 20  # excludes system prompt
    _messages: list[Message] = field(default_factory=list, init=False, repr=False)
    _created_at: datetime = field(default_factory=datetime.now, init=False, repr=False)

    def add_user_message(self, content: str) -> None:
        """Append a user turn to the history."""
        self._messages.append(Message(role=Role.USER, content=content))
        self._trim()
        log.debug(f"User message added. History length: {len(self._messages)}")

    def add_assistant_message(self, content: str) -> None:
        """Append an assistant turn to the history."""
        self._messages.append(Message(role=Role.ASSISTANT, content=content))
        self._trim()
        log.debug(f"Assistant message added. History length: {len(self._messages)}")

    def get_messages(self, include_system: bool = True) -> list[Message]:
        """
        Return the full message list ready to pass to the AI provider.

        Args:
            include_system: If True, prepend the system prompt message.
        """
        if include_system:
            system_msg = Message(role=Role.SYSTEM, content=self.system_prompt)
            return [system_msg, *list(self._messages)]
        return list(self._messages)

    def clear(self) -> None:
        """Reset the conversation (keeps system prompt)."""
        self._messages.clear()
        log.info("Conversation history cleared.")

    def __len__(self) -> int:
        return len(self._messages)

    def __repr__(self) -> str:
        return (
            f"ConversationHistory("
            f"messages={len(self._messages)}, "
            f"max={self.max_messages}, "
            f"started={self._created_at.strftime('%H:%M:%S')})"
        )

    def _trim(self) -> None:
        """Drop the oldest user/assistant pairs if we exceed max_messages."""
        if len(self._messages) > self.max_messages:
            overflow = len(self._messages) - self.max_messages
            self._messages = self._messages[overflow:]
            log.debug(f"Trimmed {overflow} old messages from history.")
