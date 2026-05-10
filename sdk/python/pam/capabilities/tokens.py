"""Capability tokens for access-controlled memory sharing."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from pydantic import BaseModel, ConfigDict

from ..models.base import BaseEntry


class CapabilityScope(BaseModel):
    """Defines what entries a capability token grants access to."""

    model_config = ConfigDict(populate_by_name=True)

    type: Literal["entry_ids", "component", "tag", "wildcard"]
    value: list[str] | str


class CapabilityToken(BaseModel):
    """A signed token granting scoped permissions over memory entries."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = ""
    scope: CapabilityScope
    permissions: list[
        Literal["read", "write", "derive", "redact", "export", "rehydrate"]
    ]
    issuer: str
    issuer_signature: str = ""
    audience: str | None = None
    issued_at: str = ""
    expires_at: str = ""
    binding_params: dict = {}

    def model_post_init(self, __context: object) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.issued_at:
            self.issued_at = datetime.now(timezone.utc).isoformat()

    def _signable_payload(self) -> bytes:
        """Canonical bytes used for signing (all fields except signature)."""
        data = self.model_dump(mode="json")
        data.pop("issuer_signature", None)
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def sign(self, private_key_bytes: bytes) -> None:
        """Sign the token with an Ed25519 private key (32-byte seed)."""
        private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        sig = private_key.sign(self._signable_payload())
        self.issuer_signature = sig.hex()

    def verify_signature(self, public_key_bytes: bytes) -> bool:
        """Verify the issuer signature with an Ed25519 public key."""
        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(
                bytes.fromhex(self.issuer_signature), self._signable_payload()
            )
            return True
        except Exception:
            return False

    def is_expired(self) -> bool:
        """Return True if the token has expired."""
        if not self.expires_at:
            return False
        expires = datetime.fromisoformat(self.expires_at)
        now = datetime.now(timezone.utc)
        if expires.tzinfo is None:
            from datetime import timezone as tz

            expires = expires.replace(tzinfo=tz.utc)
        return now > expires


class CapabilityValidator:
    """Validates capability tokens and filters entries by scope."""

    def validate_token(
        self,
        token: CapabilityToken,
        public_key: bytes,
        audience: str | None = None,
    ) -> bool:
        """Validate signature, expiration, and audience match.
        
        If the token specifies an audience, it is always enforced —
        the caller must provide a matching audience string.
        """
        if token.is_expired():
            return False
        if not token.verify_signature(public_key):
            return False
        # Enforce audience: if token has an audience, caller MUST match it
        if token.audience is not None:
            if audience is None or token.audience != audience:
                return False
        return True

    def filter_entries(
        self, entries: list[BaseEntry], token: CapabilityToken
    ) -> list[BaseEntry]:
        """Return only entries permitted by the token's scope."""
        if "read" not in token.permissions:
            return []
        scope = token.scope
        if scope.type == "wildcard":
            return list(entries)
        if scope.type == "entry_ids":
            allowed = set(scope.value) if isinstance(scope.value, list) else {scope.value}
            return [e for e in entries if e.id in allowed]
        if scope.type == "tag":
            tags = set(scope.value) if isinstance(scope.value, list) else {scope.value}
            return [e for e in entries if tags & set(e.tags)]
        if scope.type == "component":
            from ..models.entries import (
                EpisodicEntry,
                IdentityEntry,
                ProceduralEntry,
                SemanticEntry,
                WorkingEntry,
            )

            component_map: dict[str, type] = {
                "episodic": EpisodicEntry,
                "semantic": SemanticEntry,
                "procedural": ProceduralEntry,
                "working": WorkingEntry,
                "identity": IdentityEntry,
            }
            allowed_types: list[type] = []
            vals = scope.value if isinstance(scope.value, list) else [scope.value]
            for v in vals:
                if v in component_map:
                    allowed_types.append(component_map[v])
            return [e for e in entries if type(e) in allowed_types]
        return []
