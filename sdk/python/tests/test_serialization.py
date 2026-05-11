"""Tests for Portable Agent Memory JSON/CBOR serialization round-trips."""

import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pam.models.artifact import MemoryArtifact, SourceAgent
from pam.models.entries import EpisodicEntry, SemanticEntry
from pam.serialization.codec import (
    canonical_json,
    deserialize_cbor,
    deserialize_json,
    pretty_json,
    serialize_cbor,
    serialize_json,
)
from pam.transport.file import FileTransport


def _make_artifact() -> MemoryArtifact:
    return MemoryArtifact(
        source_agent=SourceAgent(
            name="test-agent", model_family="gpt-4", runtime="python"
        ),
        episodic=[
            EpisodicEntry(
                timestamp="2024-01-15T10:00:00Z",
                actor="user",
                observation="Test observation",
                salience=0.8,
                event_type="interaction",
            ),
        ],
        semantic=[
            SemanticEntry(
                subject="project",
                predicate="uses",
                object="FastAPI",
                confidence=0.95,
            ),
        ],
    )


class TestJSONSerialization:
    def test_round_trip(self):
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        json_str = serialize_json(artifact)
        restored = deserialize_json(json_str)
        assert restored.source_agent.name == "test-agent"
        assert len(restored.episodic) == 1
        assert restored.episodic[0].observation == "Test observation"
        assert restored.root_hash == artifact.root_hash

    def test_artifact_to_json_method(self):
        artifact = _make_artifact()
        json_str = artifact.to_json()
        restored = MemoryArtifact.from_json(json_str)
        assert restored.source_agent.name == artifact.source_agent.name

    def test_artifact_to_json_pretty_default(self):
        artifact = _make_artifact()
        json_str = artifact.to_json()
        # Pretty JSON has newlines and indentation
        assert "\n" in json_str
        parsed = json.loads(json_str)
        assert parsed["source_agent"]["name"] == "test-agent"

    def test_artifact_to_json_canonical(self):
        artifact = _make_artifact()
        json_str = artifact.to_json(pretty=False)
        # Canonical JSON has no newlines or indentation
        assert "\n" not in json_str
        # Verify it's compact (no ": " or ", " formatting separators)
        assert '": ' not in json_str
        assert '", ' not in json_str

    def test_canonical_json_deterministic(self):
        # Build two artifacts with identical fixed timestamps
        def make():
            return MemoryArtifact(
                created_at="2024-01-01T00:00:00+00:00",
                source_agent=SourceAgent(
                    name="test-agent", model_family="gpt-4", runtime="python"
                ),
                episodic=[
                    EpisodicEntry(
                        created_at="2024-01-01T00:00:00+00:00",
                        timestamp="2024-01-15T10:00:00Z",
                        actor="user",
                        observation="Test observation",
                        salience=0.8,
                        event_type="interaction",
                    ),
                ],
            )

        assert serialize_json(make()) == serialize_json(make())
        assert canonical_json(make()) == canonical_json(make())

    def test_pretty_json_is_readable(self):
        artifact = _make_artifact()
        output = pretty_json(artifact)
        # Should be indented and parseable
        assert "\n" in output
        parsed = json.loads(output)
        assert parsed["source_agent"]["name"] == "test-agent"

    def test_pretty_json_round_trip(self):
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        output = pretty_json(artifact)
        restored = deserialize_json(output)
        assert restored.root_hash == artifact.root_hash
        assert restored.source_agent.name == "test-agent"


class TestCBORSerialization:
    def test_round_trip(self):
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        cbor_bytes = serialize_cbor(artifact)
        restored = deserialize_cbor(cbor_bytes)
        assert restored.source_agent.name == "test-agent"
        assert len(restored.semantic) == 1
        assert restored.root_hash == artifact.root_hash

    def test_artifact_cbor_methods(self):
        artifact = _make_artifact()
        cbor_bytes = artifact.to_cbor()
        restored = MemoryArtifact.from_cbor(cbor_bytes)
        assert restored.source_agent.runtime == "python"


class TestFileTransport:
    def test_pam_file_saves_as_json(self, tmp_path):
        """A .pam file is now JSON (human-readable)."""
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        path = tmp_path / "test.pam"
        FileTransport.save(artifact, path)

        # Verify it's valid JSON text
        content = path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert parsed["source_agent"]["name"] == "test-agent"

        # Verify round-trip
        restored = FileTransport.load(path)
        assert restored.source_agent.name == "test-agent"
        assert restored.root_hash == artifact.root_hash

    def test_pam_cbor_file_round_trip(self, tmp_path):
        """A .pam.cbor file is compact CBOR."""
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        path = tmp_path / "test.pam.cbor"
        FileTransport.save_compact(artifact, path)
        restored = FileTransport.load(path)
        assert restored.source_agent.name == "test-agent"
        assert restored.root_hash == artifact.root_hash

    def test_pam_json_legacy_extension(self, tmp_path):
        """Legacy .pam.json files still work."""
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        path = tmp_path / "test.pam.json"
        FileTransport.save(artifact, path)
        restored = FileTransport.load(path)
        assert restored.source_agent.name == "test-agent"
        assert restored.root_hash == artifact.root_hash

    def test_auto_detect_cbor_in_pam_file(self, tmp_path):
        """CBOR files should use .pam.cbor extension; .pam files are JSON-only (SEC-009)."""
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        path = tmp_path / "legacy.pam.cbor"
        # Write raw CBOR bytes to a .pam.cbor file
        path.write_bytes(serialize_cbor(artifact))
        # load() should detect CBOR via extension
        restored = FileTransport.load(path)
        assert restored.source_agent.name == "test-agent"
        assert restored.root_hash == artifact.root_hash

    def test_backward_compat_aliases(self, tmp_path):
        """Deprecated aliases still work."""
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()

        # save_json / load_json
        json_path = tmp_path / "compat.pam.json"
        FileTransport.save_json(artifact, json_path)
        restored = FileTransport.load_json(json_path)
        assert restored.root_hash == artifact.root_hash

        # save_cbor / load_cbor
        cbor_path = tmp_path / "compat.pam.cbor"
        FileTransport.save_cbor(artifact, cbor_path)
        restored = FileTransport.load_cbor(cbor_path)
        assert restored.root_hash == artifact.root_hash


class TestSignedArtifactRoundTrip:
    def test_sign_serialize_verify(self):
        artifact = _make_artifact()
        private_key = Ed25519PrivateKey.generate()
        seed = private_key.private_bytes_raw()
        pub = private_key.public_key().public_bytes_raw()

        artifact.sign(seed)
        json_str = serialize_json(artifact)
        restored = deserialize_json(json_str)
        assert restored.verify_signature(pub)
        assert restored.verify_integrity()

    def test_sign_pretty_json_verify(self):
        """Pretty JSON round-trip preserves signatures."""
        artifact = _make_artifact()
        private_key = Ed25519PrivateKey.generate()
        seed = private_key.private_bytes_raw()
        pub = private_key.public_key().public_bytes_raw()

        artifact.sign(seed)
        json_str = pretty_json(artifact)
        restored = deserialize_json(json_str)
        assert restored.verify_signature(pub)
        assert restored.verify_integrity()
