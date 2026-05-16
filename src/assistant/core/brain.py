"""
AI Brain -- provider-agnostic abstraction layer.

Architecture:
    AIProviderProtocol              <- abstract interface (typing.Protocol)
    OpenAIProvider                  <- active (Phase 1 default)
    AnthropicProvider               <- active (Phase 2, set AI_PROVIDER=anthropic in .env)

    Brain                           <- single entry point used by UI, API, and ConversationStore
        brain.chat(user_message)    <- returns full assistant reply (blocking)
        brain.stream_chat(msg)      <- yields sentences as they arrive (low-latency voice)

Phase 2.5 additions (streaming):
    - Both providers implement stream_complete() for token-by-token streaming.
    - Brain.stream_chat() yields complete sentences via SentenceSplitter so TTS
      can start speaking after the first sentence (~0.5s) instead of waiting for
      the full response (3-8s). This is how ChatGPT Voice works.

Swapping providers still requires only changing AI_PROVIDER in .env.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from openai import OpenAI

from assistant.config import AIProvider, get_settings
from assistant.core.conversation import ConversationHistory
from assistant.core.streaming import SentenceSplitter
from assistant.logger import get_logger

log = get_logger(__name__)


# -- Provider Protocol ---------------------------------------------------------


@runtime_checkable
class AIProviderProtocol(Protocol):
    """
    Interface every AI provider must satisfy.

    complete()        -- blocking, returns full reply (used by REST API)
    stream_complete() -- streaming, yields text tokens (used by voice pipeline)
    """

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Send a message list and return the assistant's reply as a string."""
        ...

    def stream_complete(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """Stream the assistant's reply as text tokens (chunks)."""
        ...


# -- OpenAI Provider -----------------------------------------------------------


class OpenAIProvider:
    """Calls the OpenAI Chat Completions API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
        self._model = settings.openai_model
        log.info(f"OpenAI provider ready. Model: [bold]{self._model}[/bold]")

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Blocking call -- waits for the full response."""
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

    def stream_complete(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """
        Stream text tokens from OpenAI as they are generated.

        First token arrives in ~300ms instead of waiting for full response (~2-5s).
        """
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.7,
            max_tokens=1024,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# -- Anthropic (Claude) Provider -----------------------------------------------


class AnthropicProvider:
    """
    Calls the Anthropic Claude API.

    Active when AI_PROVIDER=anthropic in .env.
    Recommended fast model: claude-3-5-haiku-20251001
    """

    def __init__(self) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            ) from exc

        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())
        self._model = settings.anthropic_model
        log.info(f"Anthropic (Claude) provider ready. Model: [bold]{self._model}[/bold]")

    def complete(self, messages: list[dict[str, str]]) -> str:
        """Blocking call -- waits for the full response."""
        system_msg, chat_messages = self._split_messages(messages)
        response = self._client.messages.create(
            model=self._model,
            system=system_msg,
            messages=chat_messages,  # type: ignore[arg-type]
            max_tokens=1024,
        )
        content = response.content[0].text if response.content else ""
        log.debug(f"Anthropic response received. Stop reason: {response.stop_reason}")
        return content.strip()

    def stream_complete(self, messages: list[dict[str, str]]) -> Iterator[str]:
        """
        Stream text tokens from Anthropic Claude as they are generated.
        Sub-second time-to-first-token.
        """
        system_msg, chat_messages = self._split_messages(messages)
        with self._client.messages.stream(
            model=self._model,
            system=system_msg,
            messages=chat_messages,  # type: ignore[arg-type]
            max_tokens=1024,
        ) as stream:
            yield from stream.text_stream

    @staticmethod
    def _split_messages(
        messages: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]]]:
        """Separate the system message from the chat messages (Anthropic API format)."""
        system_msg = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)
        return system_msg, chat_messages


# -- Provider Factory ----------------------------------------------------------


def _build_provider() -> AIProviderProtocol:
    """Instantiate the correct provider based on the AI_PROVIDER setting."""
    settings = get_settings()
    if settings.ai_provider == AIProvider.OPENAI:
        return OpenAIProvider()
    elif settings.ai_provider == AIProvider.ANTHROPIC:
        return AnthropicProvider()
    else:
        raise ValueError(f"Unknown AI provider: {settings.ai_provider}")


# -- Brain ---------------------------------------------------------------------


class Brain:
    """
    The central AI controller.

    Owns a ConversationHistory and delegates completions to an AI provider.
    Used by the desktop UI, CLI, and ConversationStore.

    Args:
        system_prompt: Override the default system prompt from settings.
        provider:      Inject a pre-built provider (share one HTTP client).

    Usage -- blocking (REST API):
        brain = Brain()
        reply = brain.chat("What is the capital of France?")

    Usage -- streaming (voice pipeline):
        brain = Brain()
        for sentence in brain.stream_chat("Tell me about Mars."):
            tts.speak(sentence)   # plays while AI generates next sentence
    """

    def __init__(
        self,
        system_prompt: str | None = None,
        provider: AIProviderProtocol | None = None,
    ) -> None:
        settings = get_settings()

        if provider is not None:
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
        Process a user message and return the full assistant reply.

        Blocks until the complete response is received. Use stream_chat()
        for voice interactions where low latency matters.
        """
        if not user_message.strip():
            return ""

        self._history.add_user_message(user_message)

        try:
            reply = self._provider.complete(self._history.get_messages())
        except Exception as exc:
            log.error(f"AI provider error: {exc}", exc_info=True)
            self._history._messages.pop()
            reply = "Sorry, I ran into an issue generating a response. Please try again."

        self._history.add_assistant_message(reply)
        return reply

    def stream_chat(self, user_message: str) -> Iterator[str]:
        """
        Process a user message and stream back complete sentences.

        Uses the provider's streaming API and SentenceSplitter to yield one
        complete sentence at a time. The first sentence is available after
        ~300-500ms regardless of how long the full response takes.

        Args:
            user_message: The user's input.

        Yields:
            Complete sentences as strings, in order, as they become available.
        """
        if not user_message.strip():
            return

        self._history.add_user_message(user_message)
        full_reply = ""
        splitter = SentenceSplitter()

        try:
            for chunk in self._provider.stream_complete(self._history.get_messages()):
                full_reply += chunk
                for sentence in splitter.feed(chunk):
                    log.debug(f"Streaming sentence: {sentence[:50]!r}...")
                    yield sentence

            remainder = splitter.flush()
            if remainder:
                yield remainder

        except Exception as exc:
            log.error(f"AI streaming error: {exc}", exc_info=True)
            self._history._messages.pop()
            yield "Sorry, I ran into an issue generating a response. Please try again."
            return

        self._history.add_assistant_message(full_reply)
        log.info(f"Streaming complete. {len(full_reply)} chars.")

    def reset(self) -> None:
        """Clear the conversation history and start fresh."""
        self._history.clear()

    @property
    def history(self) -> ConversationHistory:
        """Read-only access to conversation history (for display in UI)."""
        return self._history
