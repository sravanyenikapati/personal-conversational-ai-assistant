"""
FastAPI Backend — Phase 2: Multi-Agent API.

Exposes the multi-agent AI system over HTTP so the Flutter mobile app can call it.
One shared AI provider, isolated conversation memory per (session_id, agent_id) pair.

Run locally:
    uvicorn assistant.api.server:app --reload --port 8000

Interactive docs:
    http://localhost:8000/docs

Endpoints:
    GET  /agents                  — list all available agents
    GET  /agents/{agent_id}       — get details for one agent
    POST /chat                    — send a message to a specific agent
    DELETE /chat                  — clear one agent's conversation history
    DELETE /session               — clear ALL agent histories for a session
    GET  /health                  — liveness check
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from assistant.agents import AgentRouter, ConversationStore
from assistant.agents.prompts import AgentConfig
from assistant.config import get_settings
from assistant.core.brain import _build_provider
from assistant.logger import configure_root_logger, get_logger

# ── Startup ───────────────────────────────────────────────────────────────────

settings = get_settings()
configure_root_logger(settings.log_level)
log = get_logger(__name__)

settings.validate_provider()

# One shared provider — one HTTP client for all conversations.
# One router — knows all 9 agents.
# One store — manages isolated conversation histories.
_provider = _build_provider()
_router = AgentRouter()
_store = ConversationStore(provider=_provider)

# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    description=(
        "Personal AI Assistant — multi-agent REST API. "
        "Nine specialist agents, isolated conversation memory per session."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten to your Flutter app domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Models ───────────────────────────────────────────────────────────

class AgentInfo(BaseModel):
    """Metadata about an agent — returned by GET /agents."""

    id: str = Field(..., description="URL-safe agent identifier, e.g. 'health'")
    name: str = Field(..., description="Display name, e.g. 'Health & Wellness'")
    emoji: str = Field(..., description="Single emoji for the agent selector UI")
    description: str = Field(..., description="One-sentence description")
    has_disclaimer: bool = Field(..., description="True if agent shows a legal/safety disclaimer")
    disclaimer: str | None = Field(None, description="Short disclaimer text for the UI, if any")

    @classmethod
    def from_config(cls, config: AgentConfig) -> "AgentInfo":
        return cls(
            id=config.id,
            name=config.name,
            emoji=config.emoji,
            description=config.description,
            has_disclaimer=config.disclaimer is not None,
            disclaimer=config.disclaimer,
        )


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    message: str = Field(
        ..., min_length=1, max_length=4096, description="User's message"
    )
    agent_id: str = Field(
        default="general",
        description="Which agent to talk to. Defaults to 'general'.",
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Client session identifier. If omitted, a new UUID is generated "
            "and returned — the Flutter app must store this and pass it on "
            "subsequent requests to maintain conversation context."
        ),
    )


class ChatResponse(BaseModel):
    """Response body for POST /chat."""

    reply: str = Field(..., description="The agent's reply")
    agent_id: str = Field(..., description="The agent that replied")
    session_id: str = Field(..., description="Session ID — store this on the client")
    message_count: int = Field(
        ..., description="Total messages in this agent's conversation so far"
    )
    disclaimer: str | None = Field(
        None,
        description="Short legal/safety note to display in the UI (Health, Finance, Legal agents only)",
    )


class HealthResponse(BaseModel):
    status: str = "ok"
    provider: str
    model: str
    active_conversations: int
    agent_count: int


class ClearResponse(BaseModel):
    cleared: bool = True
    agent_id: str
    session_id: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Liveness check",
)
async def health() -> HealthResponse:
    """Returns server status, active provider, and conversation stats."""
    return HealthResponse(
        status="ok",
        provider=settings.ai_provider.value,
        model=(
            settings.openai_model
            if settings.ai_provider.value == "openai"
            else settings.anthropic_model
        ),
        active_conversations=_store.session_count(),
        agent_count=len(_router),
    )


@app.get(
    "/agents",
    response_model=list[AgentInfo],
    tags=["agents"],
    summary="List all available agents",
)
async def list_agents() -> list[AgentInfo]:
    """
    Returns all 9 agents in display order.
    The Flutter agent selector screen calls this on startup.
    """
    return [AgentInfo.from_config(c) for c in _router.list_all()]


@app.get(
    "/agents/{agent_id}",
    response_model=AgentInfo,
    tags=["agents"],
    summary="Get one agent's details",
)
async def get_agent(agent_id: str) -> AgentInfo:
    """Returns metadata for a single agent. Returns 404 if agent_id is unknown."""
    try:
        config = _router.get(agent_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return AgentInfo.from_config(config)


@app.post(
    "/chat",
    response_model=ChatResponse,
    tags=["conversation"],
    summary="Send a message to an agent",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a user message to a specific agent and receive its reply.

    - If `session_id` is not supplied, a new UUID is generated.
      Store it on the client and send it with every subsequent request.
    - Each (session_id, agent_id) pair has isolated conversation memory.
      Switching agents does not share context.
    - Returns 400 if `agent_id` is not one of the 9 known agents.
    """
    # Resolve the agent
    try:
        config = _router.get(request.agent_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # Generate session ID if client didn't provide one
    session_id = request.session_id or str(uuid.uuid4())

    log.info(
        f"[POST /chat] session={session_id[:8]} agent={request.agent_id} "
        f"message={request.message[:60]!r}"
    )

    # Route to the correct agent's conversation history
    reply, message_count = _store.chat(
        session_id=session_id,
        agent_id=request.agent_id,
        system_prompt=config.system_prompt,
        message=request.message,
    )

    return ChatResponse(
        reply=reply,
        agent_id=request.agent_id,
        session_id=session_id,
        message_count=message_count,
        disclaimer=config.disclaimer,
    )


@app.delete(
    "/chat",
    response_model=ClearResponse,
    tags=["conversation"],
    summary="Clear one agent's conversation history",
)
async def clear_chat(
    session_id: str = Query(..., description="The session ID"),
    agent_id: str = Query(default="general", description="Which agent's history to clear"),
) -> ClearResponse:
    """
    Clears the conversation history for one specific agent within a session.
    Other agents in the same session are not affected.
    """
    _store.clear(session_id=session_id, agent_id=agent_id)
    log.info(f"[DELETE /chat] session={session_id[:8]} agent={agent_id} cleared.")
    return ClearResponse(cleared=True, agent_id=agent_id, session_id=session_id)


@app.delete(
    "/session",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["conversation"],
    summary="Clear ALL agent histories for a session",
)
async def clear_session(
    session_id: str = Query(..., description="The session ID to fully clear"),
) -> None:
    """
    Clears ALL conversation histories for a session.
    Use this when the user logs out or explicitly resets the app.
    """
    _store.clear_session(session_id=session_id)
    log.info(f"[DELETE /session] session={session_id[:8]} fully cleared.")
