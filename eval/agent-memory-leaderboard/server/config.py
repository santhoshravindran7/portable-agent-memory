"""Runtime configuration, sourced entirely from environment variables.

No secrets are baked into the image. The optional ``MEMORY_API_KEY`` enables
authentication; when unset, the endpoints accept unauthenticated calls so a
maintainer can run the public smoke flow without key binding.
"""

from __future__ import annotations

import os


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "off", "")


class Settings:
    """Adapter settings resolved from the environment at startup."""

    def __init__(self) -> None:
        # Optional shared secret. Accepted via X-Api-Key, Bearer, or Token schemes.
        self.api_key: str | None = os.getenv("MEMORY_API_KEY") or None

        # Retrieval configuration.
        self.use_embeddings: bool = _as_bool(os.getenv("USE_EMBEDDINGS"), True)
        self.embedding_model: str = os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
        # Blend weight: final = alpha * dense + (1 - alpha) * lexical.
        self.hybrid_alpha: float = float(os.getenv("HYBRID_ALPHA", "0.6"))

        # When true, every returned memory has its BLAKE3 content hash
        # re-verified before it is handed back to the platform answer model.
        self.verify_on_search: bool = _as_bool(os.getenv("VERIFY_ON_SEARCH"), True)
