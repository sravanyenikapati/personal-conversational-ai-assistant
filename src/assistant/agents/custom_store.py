"""
Custom Agent Store — persistent CRUD for user-defined agents.

Custom agents are stored as JSON at:
    ~/.personal_ai/custom_agents.json   (default)

Each entry has the same fields as AgentConfig plus metadata:
    id, name, emoji, description, personality, knowledge,
    disclaimer, created_at, updated_at

The system_prompt is auto-built from (personality + knowledge) so the
user never has to write raw prompts.

Thread-safety: a threading.Lock guards all read/write operations.
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from assistant.logger import get_logger

log = get_logger(__name__)

_DEFAULT_DATA_DIR = Path.home() / ".personal_ai"
_DEFAULT_FILE = _DEFAULT_DATA_DIR / "custom_agents.json"

# ID prefix that makes custom agents easy to distinguish from built-ins
_ID_PREFIX = "custom_"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CustomAgent:
    """A user-created agent — mutable counterpart to AgentConfig."""

    id: str
    name: str
    emoji: str
    description: str
    personality: str  # how it talks / its tone
    knowledge: str  # what domain / topics it specialises in
    disclaimer: str | None = None
    created_at: str = field(default_factory=lambda: _now_iso())
    updated_at: str = field(default_factory=lambda: _now_iso())

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def system_prompt(self) -> str:
        """Auto-build a system prompt from personality + knowledge."""
        parts = [
            f"You are {self.name}, a personal AI assistant.",
        ]
        if self.personality.strip():
            parts.append(f"Personality and tone: {self.personality.strip()}")
        if self.knowledge.strip():
            parts.append(f"Your area of expertise: {self.knowledge.strip()}")
        parts += [
            "Always respond in English only, in natural spoken sentences.",
            "Never use markdown, bullet points, numbered lists, or special formatting.",
            "Keep replies concise and direct unless the user clearly wants more depth.",
        ]
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CustomAgent:
        return cls(
            id=data["id"],
            name=data["name"],
            emoji=data["emoji"],
            description=data["description"],
            personality=data["personality"],
            knowledge=data["knowledge"],
            disclaimer=data.get("disclaimer"),
            created_at=data.get("created_at", _now_iso()),
            updated_at=data.get("updated_at", _now_iso()),
        )


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class CustomAgentStore:
    """
    Thread-safe CRUD store for custom agents, backed by a JSON file.

    Instantiate once at server startup and share the instance.
    """

    def __init__(self, data_file: Path = _DEFAULT_FILE) -> None:
        self._file = data_file
        self._lock = threading.Lock()
        self._agents: dict[str, CustomAgent] = {}
        self._load()
        log.info(f"CustomAgentStore loaded {len(self._agents)} custom agents from {self._file}")

    # ------------------------------------------------------------------
    # Public CRUD API
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        name: str,
        emoji: str,
        description: str,
        personality: str,
        knowledge: str,
        disclaimer: str | None = None,
    ) -> CustomAgent:
        """Create and persist a new custom agent. Returns the new agent."""
        agent_id = _ID_PREFIX + uuid.uuid4().hex[:8]
        agent = CustomAgent(
            id=agent_id,
            name=name.strip(),
            emoji=emoji.strip() or "🤖",
            description=description.strip(),
            personality=personality.strip(),
            knowledge=knowledge.strip(),
            disclaimer=disclaimer.strip() if disclaimer else None,
        )
        with self._lock:
            self._agents[agent_id] = agent
            self._save_locked()
        log.info(f"Created custom agent [{agent_id}] '{agent.name}'")
        return agent

    def list_all(self) -> list[CustomAgent]:
        """Return all custom agents ordered by creation time (oldest first)."""
        with self._lock:
            return sorted(self._agents.values(), key=lambda a: a.created_at)

    def get(self, agent_id: str) -> CustomAgent | None:
        """Return the agent with the given ID, or None if not found."""
        with self._lock:
            return self._agents.get(agent_id)

    def update(
        self,
        agent_id: str,
        *,
        name: str | None = None,
        emoji: str | None = None,
        description: str | None = None,
        personality: str | None = None,
        knowledge: str | None = None,
        disclaimer: str | None = None,
    ) -> CustomAgent | None:
        """
        Update one or more fields on an existing custom agent.

        Returns the updated agent, or None if agent_id is not found.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return None

            if name is not None:
                agent.name = name.strip()
            if emoji is not None:
                agent.emoji = emoji.strip() or agent.emoji
            if description is not None:
                agent.description = description.strip()
            if personality is not None:
                agent.personality = personality.strip()
            if knowledge is not None:
                agent.knowledge = knowledge.strip()
            if disclaimer is not None:
                agent.disclaimer = disclaimer.strip() or None
            agent.updated_at = _now_iso()

            self._save_locked()
        log.info(f"Updated custom agent [{agent_id}]")
        return agent

    def delete(self, agent_id: str) -> bool:
        """Delete a custom agent. Returns True if deleted, False if not found."""
        with self._lock:
            if agent_id not in self._agents:
                return False
            del self._agents[agent_id]
            self._save_locked()
        log.info(f"Deleted custom agent [{agent_id}]")
        return True

    def __contains__(self, agent_id: str) -> bool:
        with self._lock:
            return agent_id in self._agents

    def __len__(self) -> int:
        with self._lock:
            return len(self._agents)

    # ------------------------------------------------------------------
    # Internal I/O (always called while holding self._lock)
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load agents from the JSON file. Safe to call if file doesn't exist yet."""
        try:
            if self._file.exists():
                raw = json.loads(self._file.read_text(encoding="utf-8"))
                self._agents = {entry["id"]: CustomAgent.from_dict(entry) for entry in raw}
        except Exception as exc:
            log.error(f"Failed to load custom agents from {self._file}: {exc}")
            self._agents = {}

    def _save_locked(self) -> None:
        """Persist agents to disk. Must be called while holding self._lock."""
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            data = [a.to_dict() for a in self._agents.values()]
            self._file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            log.error(f"Failed to save custom agents to {self._file}: {exc}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
