"""PAM-backed memory store.

Each incoming benchmark message is stored as a content-addressed
:class:`~pam.EpisodicEntry` inside a per-``user_id``
:class:`~pam.MemoryArtifact`. This gives every stored memory a BLAKE3
content hash (its ``id``) and lets us re-verify integrity before the memory is
ever returned to the platform answer model — the core Portable Agent Memory
guarantee, applied to leaderboard retrieval.

Retrieval isolation is strict: memories are only ever read back under the exact
``user_id`` they were stored with.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from pam import EpisodicEntry, MemoryArtifact, SourceAgent
from pam import __version__ as PAM_VERSION


@dataclass
class MemoryRecord:
    """A stored memory plus the metadata Search needs to rank and return it."""

    id: str
    user_id: str
    session_id: str
    role: str
    content: str
    created_at: str
    timestamp_ms: int | None


def _iso_from_ms(ms: int | None) -> str:
    if ms is None:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    """Thread-safe, per-user PAM artifact store."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._artifacts: dict[str, MemoryArtifact] = {}
        self._records: dict[str, dict[str, MemoryRecord]] = {}

    def _artifact(self, user_id: str) -> MemoryArtifact:
        art = self._artifacts.get(user_id)
        if art is None:
            art = MemoryArtifact(
                source_agent=SourceAgent(
                    name="pam-memory-server",
                    model_family="portable-agent-memory",
                    runtime="agent-memory-leaderboard-adapter",
                    version=PAM_VERSION,
                ),
                metadata={"user_id": user_id},
            )
            self._artifacts[user_id] = art
            self._records[user_id] = {}
        return art

    def add_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        timestamp_ms: int | None = None,
    ) -> MemoryRecord:
        """Persist one message as an episodic PAM entry. Idempotent by content hash."""
        with self._lock:
            art = self._artifact(user_id)
            entry = EpisodicEntry(
                actor=role or "user",
                observation=content,
                timestamp=_iso_from_ms(timestamp_ms),
                event_type="interaction",
                tags=[f"session:{session_id}"],
            )
            # entry.id is the BLAKE3 content hash, auto-computed on init.
            existing = self._records[user_id].get(entry.id)
            if existing is not None:
                return existing
            art.episodic.append(entry)
            rec = MemoryRecord(
                id=entry.id,
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content,
                created_at=entry.created_at,
                timestamp_ms=timestamp_ms,
            )
            self._records[user_id][entry.id] = rec
            return rec

    def verify_entry(self, user_id: str, entry_id: str) -> bool:
        """Re-verify a stored entry's BLAKE3 content hash matches its id."""
        with self._lock:
            art = self._artifacts.get(user_id)
            if art is None:
                return False
            for entry in art.episodic:
                if entry.id == entry_id:
                    return entry.compute_id() == entry.id
            return False

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {user: len(recs) for user, recs in self._records.items()}
