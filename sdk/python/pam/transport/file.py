"""Simple file-based transport for Portable Agent Memory artifacts.

Portable Agent Memory is JSON-first: ``.pam`` files are human-readable JSON by default.
CBOR is available via ``.pam.cbor`` for bandwidth-sensitive transport.
"""

from __future__ import annotations

from pathlib import Path

from ..models.artifact import MemoryArtifact
from ..serialization.codec import (
    deserialize_cbor,
    deserialize_json,
    pretty_json,
    serialize_cbor,
    serialize_json,
)

# CBOR magic: first byte of CBOR-encoded maps/arrays is typically 0xa/0xb range
_CBOR_MAP_MARKERS = (0xA0, 0xB0, 0xBF)


def _looks_like_cbor(data: bytes) -> bool:
    """Heuristic: CBOR maps start with specific byte patterns."""
    if not data:
        return False
    # CBOR maps start with 0xa0-0xbf (map with 0-31 items) or 0xbf (indefinite map)
    first = data[0]
    return (0xA0 <= first <= 0xBF)


class FileTransport:
    """Save and load Portable Agent Memory artifacts.

    ``.pam`` files are human-readable JSON (pretty-printed).
    ``.pam.cbor`` files are the compact binary CBOR format.
    """

    @staticmethod
    def save(artifact: MemoryArtifact, path: str | Path) -> None:
        """Save an artifact as pretty-printed JSON.

        This is the primary save method. Files are saved as human-readable
        JSON regardless of extension (recommended: ``.pam``).
        """
        p = Path(path)
        p.write_text(pretty_json(artifact), encoding="utf-8")

    @staticmethod
    def save_compact(artifact: MemoryArtifact, path: str | Path) -> None:
        """Save an artifact as CBOR for compact transport optimization.

        Recommended extension: ``.pam.cbor``
        """
        p = Path(path)
        p.write_bytes(serialize_cbor(artifact))

    @staticmethod
    def load(path: str | Path) -> MemoryArtifact:
        """Load an artifact from disk with auto-detection.

        Detects format by extension and content:
        - ``.pam.cbor`` → CBOR
        - ``.pam`` → JSON (with backward-compat: if content starts with CBOR
          magic bytes, parses as CBOR for old files)
        - ``.pam.json`` → JSON (legacy extension, still supported)
        """
        p = Path(path)

        # Explicit CBOR extension
        if p.name.endswith(".pam.cbor"):
            return deserialize_cbor(p.read_bytes())

        # JSON extensions (.pam or .pam.json) with CBOR backward compat
        data = p.read_bytes()
        if _looks_like_cbor(data):
            # Backward compat: old .pam files were CBOR
            return deserialize_cbor(data)
        return deserialize_json(data.decode("utf-8"))

    # ------------------------------------------------------------------
    # Backward-compatible aliases (deprecated — use save/load instead)
    # ------------------------------------------------------------------

    @staticmethod
    def save_json(artifact: MemoryArtifact, path: str | Path) -> None:
        """Save as JSON. Deprecated: use ``save()`` instead."""
        FileTransport.save(artifact, path)

    @staticmethod
    def save_cbor(artifact: MemoryArtifact, path: str | Path) -> None:
        """Save as CBOR. Deprecated: use ``save_compact()`` instead."""
        FileTransport.save_compact(artifact, path)

    @staticmethod
    def load_json(path: str | Path) -> MemoryArtifact:
        """Load from JSON. Deprecated: use ``load()`` instead."""
        p = Path(path)
        return deserialize_json(p.read_text(encoding="utf-8"))

    @staticmethod
    def load_cbor(path: str | Path) -> MemoryArtifact:
        """Load from CBOR. Deprecated: use ``load()`` instead."""
        p = Path(path)
        return deserialize_cbor(p.read_bytes())
