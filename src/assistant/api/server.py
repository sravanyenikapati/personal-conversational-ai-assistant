"""
FastAPI Backend — Phase 2.

This server exposes the AI brain over HTTP so the mobile app
(Flutter) can call it. The same Brain class used by the desktop
UI is reused here — zero duplication.

Run locally:
    uvicorn assistant.api.server:app --reload --port 8000

Endpoints:
    POST /chat       — send a message, get a reply
    DELETE /chat     — clear conversation history
    GET  /health     — liveness check
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from assistant.config import get_settings
from assistant.core.brain import Brain
from assistant.logger import configure_root_logger, get_logger

# ── Setup ─────────────────────────────────────────────────────────────────────
settings = get_settings()
configure_root_logger(settings.log_level)
log = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Personal AI Assistant REST API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# One brain instance per server process (conversation state is in-memory)
_brain = Brain()


# ── Request / Response Models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096, description="User message")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Assistant reply")
    message_count: int = Field(..., description="Total messages in current conversation")


class HealthResponse(BaseModel):
    status: str = "ok"
    provider: str
    model: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Liveness check. Returns provider info."""
    return HealthResponse(
        status="ok",
        provider=settings.ai_provider.value,
        model=settings.openai_model
        if settings.ai_provider.value == "openai"
        else settings.anthropic_model,
    )


@app.post("/chat", response_model=ChatResponse, tags=["conversation"])
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a user message and receive the assistant's reply."""
    try:
        reply = _brain.chat(request.message)
    except Exception as exc:
        log.error(f"Brain error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate a response. Please try again.",
        ) from exc

    return ChatResponse(
        reply=reply,
        message_count=len(_brain.history),
    )


@app.delete("/chat", status_code=status.HTTP_204_NO_CONTENT, tags=["conversation"])
async def clear_conversation() -> None:
    """Clear the conversation history."""
    _brain.reset()
    log.info("Conversation reset via API.")
