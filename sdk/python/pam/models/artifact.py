"""MemoryArtifact — the top-level container for Portable Agent Memory."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import blake3
import cbor2
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from pydantic import BaseModel, ConfigDict, field_validator

from .base import BaseEntry
from .entries import (
    EpisodicEntry,
    IdentityEntry,
    ProceduralEntry,
    SemanticEntry,
    WorkingEntry,
)

if TYPE_CHECKING:
    from ..capabilities.tokens import CapabilityToken

# Spec-defined entry count limits
_MAX_EPISODIC = 100_000
_MAX_SEMANTIC = 50_000
_MAX_PROCEDURAL = 10_000
_MAX_WORKING = 1_000
_MAX_IDENTITY = 100


class SourceAgent(BaseModel):
    """Describes the agent that created this artifact."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str
    model_family: str
    runtime: str
    version: str = ""


class MemoryArtifact(BaseModel):
    """Top-level Portable Agent Memory container with provenance and cryptographic integrity."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    pam_version: str = "1.0"
    schema_version: str = "1.0"
    created_at: str = ""
    source_agent: SourceAgent
    root_hash: str = ""
    signature: str = ""
    capability_tokens: list = []  # list[CapabilityToken] — kept generic to avoid circular import
    episodic: list[EpisodicEntry] = []
    semantic: list[SemanticEntry] = []
    procedural: list[ProceduralEntry] = []
    working: list[WorkingEntry] = []
    identity: list[IdentityEntry] = []
    metadata: dict = {}

    @field_validator("episodic")
    @classmethod
    def validate_episodic_count(cls, v: list) -> list:
        if len(v) > _MAX_EPISODIC:
            raise ValueError(f"Episodic entries exceed maximum of {_MAX_EPISODIC}")
        return v

    @field_validator("semantic")
    @classmethod
    def validate_semantic_count(cls, v: list) -> list:
        if len(v) > _MAX_SEMANTIC:
            raise ValueError(f"Semantic entries exceed maximum of {_MAX_SEMANTIC}")
        return v

    @field_validator("procedural")
    @classmethod
    def validate_procedural_count(cls, v: list) -> list:
        if len(v) > _MAX_PROCEDURAL:
            raise ValueError(f"Procedural entries exceed maximum of {_MAX_PROCEDURAL}")
        return v

    @field_validator("working")
    @classmethod
    def validate_working_count(cls, v: list) -> list:
        if len(v) > _MAX_WORKING:
            raise ValueError(f"Working entries exceed maximum of {_MAX_WORKING}")
        return v

    @field_validator("identity")
    @classmethod
    def validate_identity_count(cls, v: list) -> list:
        if len(v) > _MAX_IDENTITY:
            raise ValueError(f"Identity entries exceed maximum of {_MAX_IDENTITY}")
        return v

    def model_post_init(self, __context: object) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def all_entries(self) -> list[BaseEntry]:
        """Return all entries across all memory components."""
        entries: list[BaseEntry] = []
        entries.extend(self.episodic)
        entries.extend(self.semantic)
        entries.extend(self.procedural)
        entries.extend(self.working)
        entries.extend(self.identity)
        return entries

    def compute_root_hash(self) -> str:
        """Compute BLAKE3 hash over all entry IDs in deterministic order."""
        ids = sorted(e.id for e in self.all_entries())
        payload = json.dumps(ids, sort_keys=True, separators=(",", ":"))
        digest = blake3.blake3(payload.encode("utf-8")).hexdigest()
        return f"blake3:{digest}"

    def verify_integrity(self) -> bool:
        """Verify every entry's content hash and the root hash."""
        for entry in self.all_entries():
            if entry.compute_id() != entry.id:
                return False
        if self.compute_root_hash() != self.root_hash:
            return False
        return True

    def verify(self, public_key_bytes: bytes | None = None) -> bool:
        """Full verification: integrity + signature (if signed).

        If public_key_bytes is provided, also verify the cryptographic signature.
        If the artifact is signed but no public key is provided, signature
        verification is skipped (integrity-only check).
        Returns False if a public key is provided but no signature is present.
        """
        if not self.verify_integrity():
            return False
        if public_key_bytes and self.signature:
            return self.verify_signature(public_key_bytes)
        if public_key_bytes and not self.signature:
            return False  # Expected signature but none present
        return True  # No key provided, integrity passed

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------

    def sign(self, private_key_bytes: bytes) -> str:
        """Sign root_hash with an Ed25519 private key (raw 32-byte seed).

        Also sets ``self.root_hash`` and ``self.signature``.
        """
        self.root_hash = self.compute_root_hash()
        private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        sig = private_key.sign(self.root_hash.encode("utf-8"))
        self.signature = sig.hex()
        return self.signature

    def verify_signature(self, public_key_bytes: bytes) -> bool:
        """Verify Ed25519 signature against root_hash."""
        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(
                bytes.fromhex(self.signature),
                self.root_hash.encode("utf-8"),
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_json(self, pretty: bool = True) -> str:
        """Serialize to JSON.

        Args:
            pretty: If True (default), produce human-readable JSON with 2-space
                indent. If False, produce canonical JSON (sorted keys, no
                whitespace) suitable for hashing.
        """
        if pretty:
            return json.dumps(self.model_dump(mode="json"), indent=2)
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )

    def to_cbor(self) -> bytes:
        """Serialize to CBOR (compact transport optimization)."""
        return cbor2.dumps(self.model_dump(mode="json"))

    MAX_JSON_SIZE: ClassVar[int] = 50 * 1024 * 1024  # 50MB

    @classmethod
    def from_json(cls, data: str | bytes) -> MemoryArtifact:
        """Deserialize from JSON string (pretty or canonical)."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        if len(data) > cls.MAX_JSON_SIZE:
            raise ValueError(
                f"JSON data size ({len(data)} bytes) exceeds maximum of"
                f" {cls.MAX_JSON_SIZE} bytes"
            )
        return cls.model_validate_json(data)

    @classmethod
    def from_cbor(cls, data: bytes) -> MemoryArtifact:
        """Deserialize from CBOR bytes."""
        return cls.model_validate(cbor2.loads(data))
