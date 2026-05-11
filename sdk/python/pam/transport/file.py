"""Simple file-based transport for Portable Agent Memory artifacts.

Portable Agent Memory is JSON-first: ``.pam`` files are human-readable JSON by default.
CBOR is available via ``.pam.cbor`` for bandwidth-sensitive transport.
"""

from __future__ import annotations

import os
import tempfile
import warnings
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
MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB


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

        Automatically computes root_hash if not already set, ensuring
        that ``verify_integrity()`` passes on the loaded artifact.
        """
        if not artifact.root_hash:
            artifact.root_hash = artifact.compute_root_hash()
        p = Path(path)
        if p.is_symlink():
            raise ValueError(f"Refusing to write to symlink: {path}")
        p.parent.mkdir(parents=True, exist_ok=True)
        content = pretty_json(artifact)
        # Atomic write: temp file then rename
        fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(p))
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def save_compact(artifact: MemoryArtifact, path: str | Path) -> None:
        """Save an artifact as CBOR for compact transport optimization.

        Recommended extension: ``.pam.cbor``

        Automatically computes root_hash if not already set.
        """
        if not artifact.root_hash:
            artifact.root_hash = artifact.compute_root_hash()
        p = Path(path)
        if p.is_symlink():
            raise ValueError(f"Refusing to write to symlink: {path}")
        p.parent.mkdir(parents=True, exist_ok=True)
        data = serialize_cbor(artifact)
        # Atomic write: temp file then rename
        fd, tmp_path = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp_path, str(p))
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def load(path: str | Path) -> MemoryArtifact:
        """Load an artifact from disk with auto-detection.

        Detects format by file extension:
        - ``.pam.cbor`` or ``.cbor`` → CBOR
        - ``.pam`` or ``.pam.json`` → JSON
        - No extension → byte inspection fallback with warning
        """
        p = Path(path)
        if p.is_symlink():
            raise ValueError(f"Refusing to read from symlink: {path}")

        file_size = p.stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File size {file_size} exceeds maximum of {MAX_FILE_SIZE} bytes"
            )

        data = p.read_bytes()

        # Use file extension for format detection, not byte inspection
        if p.suffix == ".cbor" or str(p).endswith(".pam.cbor"):
            return deserialize_cbor(data)

        if p.suffix in (".pam", ".json") or str(p).endswith(".pam.json"):
            # Backward compat: old .pam files may contain CBOR
            if _looks_like_cbor(data):
                return deserialize_cbor(data)
            return deserialize_json(data.decode("utf-8"))

        # Fallback for extensionless files — warn and use byte inspection
        if not p.suffix:
            warnings.warn(
                "File has no extension — using byte inspection for format detection. "
                "Use .pam or .pam.cbor extensions.",
                stacklevel=2,
            )
            if _looks_like_cbor(data):
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
