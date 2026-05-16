"""
AI Brain — provider-agnostic abstraction layer.

Architecture:
    AIProviderProtocol              ← abstract interface (typing.Protocol)
    ├── OpenAIProvider              ← active (Phase 1 default)
    └── AnthropicProvider           ← active (Phase 2, set AI_PROVIDER=anthropic in .env)

    Brain                           ← single entry point used by UI, API, and ConversationStore
        brain.chat(user_message)    ← returns assistant reply string

Phase 2 additions:
    - Brain accepts an optional `system_prompt` override (for per-agent prompts).
    - Brain accepts an optional `provider` injection (so ConversationStore can share
      one HTTP client across all agent conversations — efficient and clean).

Swapping providers still requires only changing AI_PROVIDER in .env.
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
        """Send a message list and return the assistant's reply as a string."""
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


# ── Anthropic (Claude) Provider ────────────────────────────────────────────────

class AnthropicProvider:
    """
    Calls the Anthropic Claude API.

    Active in Phase 2. Set AI_PROVIDER=anthropic in your .env to use Claude.
    Requires ANTHROPIC_API_KEY to be set.
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
    """Instantiate the correct provider based on the AI_PROVIDER setting."""
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

    Owns a ConversationHistory and delegates completions to an AI provider.
    This is the entry point used by the desktop UI and CLI.

    For the multi-agent API (Phase 2), the ConversationStore manages Brain-like
    conversation logic directly — sharing one provider across all agent conversations.

    Args:
        system_prompt: Override the default system prompt from settings.
                       Used by the desktop UI when switching agents.
        provider:      Inject a pre-built provider. If omitted, one is built from
                       settings. Injection allows sharing a single HTTP client.

    Usage (single-agent, desktop UI):
        brain = Brain()
        reply = brain.chat("What's the weather on Mars?")

    Usage (per-agent, with shared provider):
        provider = _build_provider()
        health_brain = Brain(system_prompt=AGENTS["health"].system_prompt, provider=provider)
        finance_brain = Brain(system_prompt=AGENTS["finance"].system_prompt, provider=provider)
    """

    def __init__(
        self,
        system_prompt: str | None = None,
        provider: AIProviderProtocol | None = None,
    ) -> None:
        settings = get_settings()

        if provider is not None:
            # Injected — skip validation (caller is responsible)
            self._provider = provider
        else:
            settings.validate_provider()
            self._provider = _build_provider()

        self._history = ConversationHistory(
            system_prompt=system_prompt or settings.system_prompt,
            max_messages=settings.max_conversation_history,
        )
        log.info("Brain initialised. Ready to chat.")

    def chat(self, user_message: str) -> str:
        """
        Process a user message and return the assistant's reply.

        Automatically manages conversation history (rolling window).

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
            self._history._messages.pop()  # remove the user message to keep history clean
            reply = "Sorry, I ran into an issue generating a response. Please try again."

        self._history.add_assistant_message(reply)
        return reply

    def reset(self) -> None:
        """Clear the conversation history and start fresh."""
        self._history.clear()

    @property
    def history(self) -> ConversationHistory:
        """Read-only access to conversation history (for display in UI)."""
        return self._history
