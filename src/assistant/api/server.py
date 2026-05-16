"""
FastAPI Backend -- Phase 2.5: Multi-Agent API with Streaming.

Run locally:
    uvicorn assistant.api.server:app --reload --port 8000

Endpoints:
    GET  /health          -- liveness check
    GET  /agents          -- list all available agents
    GET  /agents/{id}     -- get one agent's details
    POST /chat            -- send a message (blocking, full reply)
    POST /chat/stream     -- send a message (Server-Sent Events streaming)
    DELETE /chat          -- clear one agent's conversation history
    DELETE /session       -- clear ALL agent histories for a session
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from assistant.agents import AgentRouter, ConversationStore
from assistant.agents.prompts import AgentConfig
from assistant.config import get_settings
from assistant.core.brain import _build_provider
from assistant.logger import configure_root_logger, get_logger

# -- Startup -------------------------------------------------------------------

settings = get_settings()
configure_root_logger(settings.log_level)
log = get_logger(__name__)

settings.validate_provider()

_provider = _build_provider()
_router = AgentRouter()
_store = ConversationStore(provider=_provider)

# -- FastAPI App ---------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description=(
        "Personal AI Assistant -- multi-agent REST API. "
        "Nine specialist agents, isolated conversation memory per session."
    ),
    version="0.2.5",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- Pydantic Models -----------------------------------------------------------


class AgentInfo(BaseModel):
    id: str
    name: str
    emoji: str
    description: str
    has_disclaimer: bool
    disclaimer: str | None = None

    @classmethod
    def from_config(cls, config: AgentConfig) -> AgentInfo:
        return cls(
            id=config.id,
            name=config.name,
            emoji=config.emoji,
            description=config.description,
            has_disclaimer=config.disclaimer is not None,
            disclaimer=config.disclaimer,
        )


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    agent_id: str = Field(default="general")
    session_id: str | None = Field(default=None)


class ChatResponse(BaseModel):
    reply: str
    agent_id: str
    session_id: str
    message_count: int
    disclaimer: str | None = None


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


# -- Routes --------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
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


@app.get("/agents", response_model=list[AgentInfo], tags=["agents"])
async def list_agents() -> list[AgentInfo]:
    return [AgentInfo.from_config(c) for c in _router.list_all()]


@app.get("/agents/{agent_id}", response_model=AgentInfo, tags=["agents"])
async def get_agent(agent_id: str) -> AgentInfo:
    try:
        config = _router.get(agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AgentInfo.from_config(config)


@app.post("/chat", response_model=ChatResponse, tags=["conversation"])
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a message and receive the complete reply (blocking)."""
    try:
        config = _router.get(request.agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    session_id = request.session_id or str(uuid.uuid4())
    log.info(f"[POST /chat] session={session_id[:8]} agent={request.agent_id}")

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


@app.post("/chat/stream", tags=["conversation"])
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """
    Send a message and receive the reply as a Server-Sent Events stream.

    Each SSE event is a JSON object:
      {"type": "session", "session_id": "...", "agent_id": "..."}
      {"type": "token",   "text": "Hello"}
      {"type": "done",    "disclaimer": null}

    The Flutter app accumulates tokens into the chat bubble in real time
    and feeds complete sentences to TTS -- eliminating the waiting feeling.
    Returns 400 if agent_id is unknown.
    """
    try:
        config = _router.get(request.agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    session_id = request.session_id or str(uuid.uuid4())
    log.info(f"[POST /chat/stream] session={session_id[:8]} agent={request.agent_id}")

    async def event_generator() -> AsyncIterator[str]:
        yield _sse({"type": "session", "session_id": session_id, "agent_id": request.agent_id})

        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        loop = asyncio.get_event_loop()

        def _run_sync_stream():
            return list(
                _store.stream_chat(
                    session_id=session_id,
                    agent_id=request.agent_id,
                    system_prompt=config.system_prompt,
                    message=request.message,
                )
            )

        with ThreadPoolExecutor(max_workers=1) as pool:
            tokens = await loop.run_in_executor(pool, _run_sync_stream)

        for token in tokens:
            yield _sse({"type": "token", "text": token})

        yield _sse({"type": "done", "disclaimer": config.disclaimer})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.delete("/chat", response_model=ClearResponse, tags=["conversation"])
async def clear_chat(
    session_id: str = Query(...),
    agent_id: str = Query(default="general"),
) -> ClearResponse:
    _store.clear(session_id=session_id, agent_id=agent_id)
    log.info(f"[DELETE /chat] session={session_id[:8]} agent={agent_id} cleared.")
    return ClearResponse(cleared=True, agent_id=agent_id, session_id=session_id)


@app.delete("/session", status_code=status.HTTP_204_NO_CONTENT, tags=["conversation"])
async def clear_session(session_id: str = Query(...)) -> None:
    _store.clear_session(session_id=session_id)
    log.info(f"[DELETE /session] session={session_id[:8]} fully cleared.")
