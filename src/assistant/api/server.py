"""
FastAPI Backend -- Phase 4: Multi-Agent API with Streaming + Custom Agents.

Run locally:
    uvicorn assistant.api.server:app --reload --port 8000

Endpoints:
    GET  /health                -- liveness check
    GET  /agents                -- list all agents (built-in + custom)
    GET  /agents/{id}           -- get one agent
    POST /chat                  -- blocking chat
    POST /chat/stream           -- SSE streaming chat
    DELETE /chat                -- clear one agent history
    DELETE /session             -- clear all agent histories

    GET    /custom-agents       -- list user-created agents
    POST   /custom-agents       -- create custom agent
    GET    /custom-agents/{id}  -- get one custom agent
    PUT    /custom-agents/{id}  -- edit custom agent
    DELETE /custom-agents/{id}  -- delete custom agent
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from assistant.agents import AgentRouter, ConversationStore, CustomAgentStore
from assistant.agents.custom_store import CustomAgent
from assistant.config import get_settings
from assistant.core.brain import _build_provider
from assistant.logger import configure_root_logger, get_logger

# -- Startup -------------------------------------------------------------------

settings = get_settings()
configure_root_logger(settings.log_level)
log = get_logger(__name__)

settings.validate_provider()

_provider = _build_provider()
_custom_store = CustomAgentStore()
_router = AgentRouter(custom_store=_custom_store)
_store = ConversationStore(provider=_provider)

# -- FastAPI App ---------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description="Personal AI Assistant -- multi-agent REST API with custom agents.",
    version="0.4.0",
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
    is_custom: bool = False

    @classmethod
    def from_config(cls, config) -> AgentInfo:
        is_custom = isinstance(config, CustomAgent)
        return cls(
            id=config.id,
            name=config.name,
            emoji=config.emoji,
            description=config.description,
            has_disclaimer=config.disclaimer is not None,
            disclaimer=config.disclaimer,
            is_custom=is_custom,
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
    custom_agent_count: int


class ClearResponse(BaseModel):
    cleared: bool = True
    agent_id: str
    session_id: str


class CreateCustomAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    emoji: str = Field(default="\U0001f916", max_length=8)
    description: str = Field(..., min_length=1, max_length=200)
    personality: str = Field(..., min_length=1, max_length=1000)
    knowledge: str = Field(..., min_length=1, max_length=2000)
    disclaimer: str | None = Field(default=None, max_length=300)


class UpdateCustomAgentRequest(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    emoji: str | None = Field(default=None, max_length=8)
    description: str | None = Field(default=None, max_length=200)
    personality: str | None = Field(default=None, max_length=1000)
    knowledge: str | None = Field(default=None, max_length=2000)
    disclaimer: str | None = Field(default=None, max_length=300)


class CustomAgentResponse(BaseModel):
    id: str
    name: str
    emoji: str
    description: str
    personality: str
    knowledge: str
    disclaimer: str | None
    created_at: str
    updated_at: str
    is_custom: bool = True

    @classmethod
    def from_agent(cls, agent: CustomAgent) -> CustomAgentResponse:
        return cls(
            id=agent.id,
            name=agent.name,
            emoji=agent.emoji,
            description=agent.description,
            personality=agent.personality,
            knowledge=agent.knowledge,
            disclaimer=agent.disclaimer,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )


# -- Routes: System ------------------------------------------------------------


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
        custom_agent_count=len(_custom_store),
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
    return ClearResponse(cleared=True, agent_id=agent_id, session_id=session_id)


@app.delete("/session", status_code=status.HTTP_204_NO_CONTENT, tags=["conversation"])
async def clear_session(session_id: str = Query(...)) -> None:
    _store.clear_session(session_id=session_id)


# -- Routes: Custom Agents (Phase 4) ------------------------------------------


@app.get("/custom-agents", response_model=list[CustomAgentResponse], tags=["custom-agents"])
async def list_custom_agents() -> list[CustomAgentResponse]:
    return [CustomAgentResponse.from_agent(a) for a in _custom_store.list_all()]


@app.post(
    "/custom-agents",
    response_model=CustomAgentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["custom-agents"],
)
async def create_custom_agent(request: CreateCustomAgentRequest) -> CustomAgentResponse:
    agent = _custom_store.create(
        name=request.name,
        emoji=request.emoji,
        description=request.description,
        personality=request.personality,
        knowledge=request.knowledge,
        disclaimer=request.disclaimer,
    )
    log.info(f"[POST /custom-agents] Created {agent.name!r} [{agent.id}]")
    return CustomAgentResponse.from_agent(agent)


@app.get("/custom-agents/{agent_id}", response_model=CustomAgentResponse, tags=["custom-agents"])
async def get_custom_agent(agent_id: str) -> CustomAgentResponse:
    agent = _custom_store.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Custom agent {agent_id!r} not found.")
    return CustomAgentResponse.from_agent(agent)


@app.put("/custom-agents/{agent_id}", response_model=CustomAgentResponse, tags=["custom-agents"])
async def update_custom_agent(
    agent_id: str, request: UpdateCustomAgentRequest
) -> CustomAgentResponse:
    agent = _custom_store.update(
        agent_id,
        name=request.name,
        emoji=request.emoji,
        description=request.description,
        personality=request.personality,
        knowledge=request.knowledge,
        disclaimer=request.disclaimer,
    )
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Custom agent {agent_id!r} not found.")
    log.info(f"[PUT /custom-agents/{agent_id}] Updated {agent.name!r}")
    return CustomAgentResponse.from_agent(agent)


@app.delete(
    "/custom-agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["custom-agents"]
)
async def delete_custom_agent(agent_id: str) -> None:
    deleted = _custom_store.delete(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Custom agent {agent_id!r} not found.")
    log.info(f"[DELETE /custom-agents/{agent_id}]")
