"""
Configuration management.

Loads all settings from environment variables (.env file).
Validated via Pydantic — the app will fail fast with a clear error
if a required variable is missing or has the wrong type.
"""

from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class STTEngine(str, Enum):
    WHISPER_API = "whisper-api"       # Uses OpenAI API — needs key, fastest
    WHISPER_LOCAL = "whisper-local"   # Runs locally — no key, slower


class Settings(BaseSettings):
    """All app settings, loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = Field(default="Personal AI Assistant")
    log_level: str = Field(default="INFO")

    # ── AI Provider ───────────────────────────────────────────────────────────
    ai_provider: AIProvider = Field(default=AIProvider.OPENAI)

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    openai_model: str = Field(default="gpt-4o")

    # ── Anthropic (Claude) — Phase 2 ─────────────────────────────────────────
    anthropic_api_key: SecretStr = Field(default=SecretStr(""))
    anthropic_model: str = Field(default="claude-sonnet-4-6")

    # ── Text-to-Speech ────────────────────────────────────────────────────────
    tts_voice: str = Field(default="en-US-AriaNeural")

    # ── Speech-to-Text ────────────────────────────────────────────────────────
    stt_engine: STTEngine = Field(default=STTEngine.WHISPER_API)
    whisper_model: str = Field(default="whisper-1")

    # ── Conversation ──────────────────────────────────────────────────────────
    max_conversation_history: int = Field(default=20, ge=1, le=200)

    # ── System Prompt ─────────────────────────────────────────────────────────
    system_prompt: str = Field(
        default=(
            "You are a helpful, friendly, and conversational personal AI assistant. "
            "Keep responses concise and natural — you are speaking to the user directly. "
            "When responding to voice input, avoid using bullet points, markdown, or "
            "special formatting. Speak as a person would speak."
        )
    )

    def validate_provider(self) -> None:
        """Raise a clear error if the chosen provider has no API key."""
        if self.ai_provider == AIProvider.OPENAI:
            key = self.openai_api_key.get_secret_value()
            if not key or key.startswith("sk-..."):
                raise ValueError(
                    "OPENAI_API_KEY is not set. "
                    "Add it to your .env file and try again."
                )
        elif self.ai_provider == AIProvider.ANTHROPIC:
            key = self.anthropic_api_key.get_secret_value()
            if not key or key.startswith("sk-ant-..."):
                raise ValueError(
                    "ANTHROPIC_API_KEY is not set. "
                    "Add it to your .env file and try again."
                )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
