"""Portable Agent Memory entry types."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field

from .base import BaseEntry


class EpisodicEntry(BaseEntry):
    """Records a specific event or interaction."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    timestamp: str = ""
    actor: str = ""
    observation: str = ""
    salience: float = Field(default=0.5, ge=0.0, le=1.0)
    event_type: Literal["interaction", "observation", "outcome", "reflection"] = (
        "observation"
    )


class SemanticEntry(BaseEntry):
    """A knowledge triple (subject-predicate-object) with confidence."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    subject: str = ""
    predicate: str = ""
    object: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_event_ids: list[str] = []


class ProceduralEntry(BaseEntry):
    """A reusable skill or procedure."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str = ""
    description: str = ""
    parameters: list[dict] = []
    body: str = ""
    language: Literal["natural", "python", "javascript", "typescript", "shell", "other"] = (
        "natural"
    )
    preconditions: list[str] = []
    usage_count: int = 0
    last_used: str | None = None


class WorkingEntry(BaseEntry):
    """Current working memory: goals, sub-goals, scratch-pad."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    goals: list[str] = []
    subgoals: list[dict] = []
    scratch: str = ""
    pending_actions: list[dict] = []


class IdentityEntry(BaseEntry):
    """Agent identity, preferences, and policies."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    preferences: dict = {}
    persona: str = ""
    language: str = "en"
    policies: list[str] = []
    custom_instructions: str = ""
