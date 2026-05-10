"""JSON and CBOR serialization helpers for Portable Agent Memory artifacts.

Portable Agent Memory is JSON-first: the primary serialization format is human-readable JSON.
CBOR is available as an optional compact format for bandwidth-sensitive transport.
"""

from __future__ import annotations

import json

import cbor2

from ..models.artifact import MemoryArtifact

MAX_PAYLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def pretty_json(artifact: MemoryArtifact) -> str:
    """Serialize a MemoryArtifact to human-readable JSON (2-space indent).

    This is the primary public-facing serialization format for Portable Agent Memory artifacts.
    """
    return json.dumps(
        artifact.model_dump(mode="json"),
        indent=2,
    )


def canonical_json(artifact: MemoryArtifact) -> str:
    """Serialize a MemoryArtifact to canonical JSON (sorted keys, no whitespace).

    Used internally for deterministic hashing. Not intended for human consumption.
    """
    return json.dumps(
        artifact.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


# Keep serialize_json as alias for canonical_json (backward compat)
serialize_json = canonical_json


def deserialize_json(data: str) -> MemoryArtifact:
    """Deserialize a MemoryArtifact from a JSON string (pretty or canonical)."""
    if len(data) > MAX_PAYLOAD_SIZE:
        raise ValueError(f"Payload size {len(data)} exceeds maximum {MAX_PAYLOAD_SIZE} bytes")
    return MemoryArtifact.model_validate_json(data)


def serialize_cbor(artifact: MemoryArtifact) -> bytes:
    """Serialize a MemoryArtifact to CBOR bytes.

    CBOR is an optional compact transport optimization. Use pretty_json() for
    the primary human-readable format.
    """
    return cbor2.dumps(artifact.model_dump(mode="json"))


def deserialize_cbor(data: bytes) -> MemoryArtifact:
    """Deserialize a MemoryArtifact from CBOR bytes."""
    if len(data) > MAX_PAYLOAD_SIZE:
        raise ValueError(f"Payload size {len(data)} exceeds maximum {MAX_PAYLOAD_SIZE} bytes")
    return MemoryArtifact.model_validate(cbor2.loads(data))
