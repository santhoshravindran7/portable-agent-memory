"""Tests for Portable Agent Memory capability tokens."""

from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pam.capabilities.tokens import (
    CapabilityScope,
    CapabilityToken,
    CapabilityValidator,
)
from pam.models.entries import EpisodicEntry, SemanticEntry


def _generate_keys() -> tuple[bytes, bytes]:
    """Return (private_seed, public_bytes) for Ed25519."""
    private_key = Ed25519PrivateKey.generate()
    seed = private_key.private_bytes_raw()
    pub = private_key.public_key().public_bytes_raw()
    return seed, pub


class TestCapabilityToken:
    def test_create(self):
        token = CapabilityToken(
            scope=CapabilityScope(type="wildcard", value="*"),
            permissions=["read"],
            issuer="agent-1",
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        )
        assert token.id  # UUID assigned
        assert token.issued_at

    def test_sign_and_verify(self):
        seed, pub = _generate_keys()
        token = CapabilityToken(
            scope=CapabilityScope(type="wildcard", value="*"),
            permissions=["read"],
            issuer="agent-1",
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        )
        token.sign(seed)
        assert token.issuer_signature
        assert token.verify_signature(pub)

    def test_verify_wrong_key(self):
        seed, _ = _generate_keys()
        _, other_pub = _generate_keys()
        token = CapabilityToken(
            scope=CapabilityScope(type="wildcard", value="*"),
            permissions=["read"],
            issuer="agent-1",
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        )
        token.sign(seed)
        assert not token.verify_signature(other_pub)

    def test_is_expired(self):
        token = CapabilityToken(
            scope=CapabilityScope(type="wildcard", value="*"),
            permissions=["read"],
            issuer="agent-1",
            expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        )
        assert token.is_expired()

    def test_not_expired(self):
        token = CapabilityToken(
            scope=CapabilityScope(type="wildcard", value="*"),
            permissions=["read"],
            issuer="agent-1",
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        )
        assert not token.is_expired()


class TestCapabilityValidator:
    def test_validate_valid_token(self):
        seed, pub = _generate_keys()
        token = CapabilityToken(
            scope=CapabilityScope(type="wildcard", value="*"),
            permissions=["read"],
            issuer="agent-1",
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        )
        token.sign(seed)
        validator = CapabilityValidator()
        assert validator.validate_token(token, pub)

    def test_validate_expired_token(self):
        seed, pub = _generate_keys()
        token = CapabilityToken(
            scope=CapabilityScope(type="wildcard", value="*"),
            permissions=["read"],
            issuer="agent-1",
            expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        )
        token.sign(seed)
        validator = CapabilityValidator()
        assert not validator.validate_token(token, pub)

    def test_filter_wildcard(self):
        entries = [
            EpisodicEntry(observation="a"),
            SemanticEntry(subject="b", predicate="is", object="c"),
        ]
        token = CapabilityToken(
            scope=CapabilityScope(type="wildcard", value="*"),
            permissions=["read"],
            issuer="agent-1",
        )
        validator = CapabilityValidator()
        filtered = validator.filter_entries(entries, token)
        assert len(filtered) == 2

    def test_filter_by_entry_ids(self):
        e1 = EpisodicEntry(observation="a")
        e2 = EpisodicEntry(observation="b")
        token = CapabilityToken(
            scope=CapabilityScope(type="entry_ids", value=[e1.id]),
            permissions=["read"],
            issuer="agent-1",
        )
        validator = CapabilityValidator()
        filtered = validator.filter_entries([e1, e2], token)
        assert len(filtered) == 1
        assert filtered[0].id == e1.id

    def test_filter_by_component(self):
        e1 = EpisodicEntry(observation="a")
        e2 = SemanticEntry(subject="b", predicate="is", object="c")
        token = CapabilityToken(
            scope=CapabilityScope(type="component", value=["episodic"]),
            permissions=["read"],
            issuer="agent-1",
        )
        validator = CapabilityValidator()
        filtered = validator.filter_entries([e1, e2], token)
        assert len(filtered) == 1
        assert isinstance(filtered[0], EpisodicEntry)

    def test_filter_by_tag(self):
        e1 = EpisodicEntry(observation="a", tags=["important"])
        e2 = EpisodicEntry(observation="b", tags=["debug"])
        token = CapabilityToken(
            scope=CapabilityScope(type="tag", value=["important"]),
            permissions=["read"],
            issuer="agent-1",
        )
        validator = CapabilityValidator()
        filtered = validator.filter_entries([e1, e2], token)
        assert len(filtered) == 1
        assert "important" in filtered[0].tags

    def test_no_read_permission(self):
        entries = [EpisodicEntry(observation="a")]
        token = CapabilityToken(
            scope=CapabilityScope(type="wildcard", value="*"),
            permissions=["write"],
            issuer="agent-1",
        )
        validator = CapabilityValidator()
        filtered = validator.filter_entries(entries, token)
        assert len(filtered) == 0
