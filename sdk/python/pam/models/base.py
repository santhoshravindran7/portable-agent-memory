"""Base entry model for Portable Agent Memory entries."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import blake3
from pydantic import BaseModel, ConfigDict, model_validator


class BaseEntry(BaseModel):
    """Base class for all Portable Agent Memory entries.

    Each entry is content-addressable: its ``id`` is a BLAKE3 hash
    computed from the canonical JSON representation of all fields
    except ``id`` itself.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    id: str = ""
    parent_ids: list[str] = []
    created_at: str = ""
    tags: list[str] = []
    schema_version: str = "1.0"

    @model_validator(mode="before")
    @classmethod
    def _set_created_at(cls, values: dict) -> dict:
        if isinstance(values, dict) and not values.get("created_at"):
            values["created_at"] = datetime.now(timezone.utc).isoformat()
        return values

    def compute_id(self) -> str:
        """Compute content-addressable BLAKE3 hash of canonical JSON (excluding 'id' field)."""
        data = self.model_dump(mode="json")
        data.pop("id", None)
        canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
        digest = blake3.blake3(canonical.encode("utf-8")).hexdigest()
        return f"blake3:{digest}"

    def model_post_init(self, __context: object) -> None:
        if not self.id:
            self.id = self.compute_id()
