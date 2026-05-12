"""
AI Brain — provider-agnostic abstraction layer.

Architecture:
    AIProvider (Protocol)          ← abstract interface
    ├── OpenAIProvider             ← active (Phase 1)
    └── AnthropicProvider          ← ready (Phase 2, swap via .env)

    Brain                          ← single entry point used by the rest of the app
        brain.chat(user_message)   ← returns assistant reply string

Swapping providers requires only changing AI_PROVIDER in .env.
No code changes needed anywhere else.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from openai import OpenAI

from assistant.config import AIProvider, get_settings
from assistant.core.conversation import ConversationHistory
from assistant.logger import get_logger

log = get_logger(__name__)


# ── Provider Protocol ──────────────────────────────────────────────────────────

@runtime_checkable
class AIProviderProtocol(Protocol):
    """
    Interface every AI provider must satisfy.
    Any class with a `complete` method matching this signature is a valid provider.
    """

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Send messages and return the assistant's reply as a string."""
        ...


# ── OpenAI Provider ────────────────────────────────────────────────────────────

class OpenAIProvider:
    """Calls the OpenAI Chat Completions API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value()
        )
        self._model = settings.openai_model
        log.info(f"OpenAI provider ready. Model: [bold]{self._model}[/bold]")

    def complete(self, messages: list[dict[str, str]]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.7,
            max_tokens=1024,
        )
        content = response.choices[0].message.content or ""
        log.debug(
            f"OpenAI response received. "
            f"Tokens used: {response.usage.total_tokens if response.usage else 'unknown'}"
        )
        return content.strip()


# ── Anthropic (Claude) Provider — Phase 2 ─────────────────────────────────────

class AnthropicProvider:
    """
    Calls the Anthropic Claude API.

    Phase 2: Uncomment and install `anthropic` package.
    Switch AI_PROVIDER=anthropic in .env to activate.
    """

    def __init__(self) -> None:
        try:
            import anthropic  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc

        settings = get_settings()
        self._client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key.get_secret_value()
        )
        self._model = settings.anthropic_model
        log.info(f"Anthropic (Claude) provider ready. Model: [bold]{self._model}[/bold]")

    def complete(self, messages: list[dict[str, str]]) -> str:
        # Anthropic separates the system prompt from the messages list
        system_msg = ""
        chat_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        response = self._client.messages.create(
            model=self._model,
            system=system_msg,
            messages=chat_messages,  # type: ignore[arg-type]
            max_tokens=1024,
        )
        content = response.content[0].text if response.content else ""
        log.debug(f"Anthropic response received. Stop reason: {response.stop_reason}")
        return content.strip()


# ── Provider Factory ───────────────────────────────────────────────────────────

def _build_provider() -> AIProviderProtocol:
    """Instantiate the correct provider based on settings."""
    settings = get_settings()
    if settings.ai_provider == AIProvider.OPENAI:
        return OpenAIProvider()
    elif settings.ai_provider == AIProvider.ANTHROPIC:
        return AnthropicProvider()
    else:
        raise ValueError(f"Unknown AI provider: {settings.ai_provider}")


# ── Brain ──────────────────────────────────────────────────────────────────────

class Brain:
    """
    The central AI controller.

    Owns the conversation history and delegates completions to the active provider.
    This is the ONLY class the UI and API layers should talk to.

    Usage:
        brain = Brain()
        reply = brain.chat("What's the weather like on Mars?")
    """

    def __init__(self) -> None:
        settings = get_settings()
        settings.validate_provider()

        self._provider: AIProviderProtocol = _build_provider()
        self._history = ConversationHistory(
            system_prompt=settings.system_prompt,
            max_messages=settings.max_conversation_history,
        )
        log.info("Brain initialised. Ready to chat.")

    def chat(self, user_message: str) -> str:
        """
        Process a user message and return the assistant's reply.

        Automatically manages conversation history.

        Args:
            user_message: The user's input (from text or voice).

        Returns:
            The assistant's reply as a plain string.
        """
        if not user_message.strip():
            return ""

        self._history.add_user_message(user_message)

        try:
            reply = self._provider.complete(self._history.get_messages())
        except Exception as exc:
            log.error(f"AI provider error: {exc}", exc_info=True)
            reply = "Sorry, I ran into an issue generating a response. Please try again."

        self._history.add_assistant_message(reply)
        return reply

    def reset(self) -> None:
        """Clear the conversation history and start fresh."""
        self._history.clear()

    @property
    def history(self) -> ConversationHistory:
        """Read-only access to conversation history for display in UI."""
        return self._history
