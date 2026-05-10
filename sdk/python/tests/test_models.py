"""Tests for Portable Agent Memory data models."""

import json

from pam.models.base import BaseEntry
from pam.models.entries import (
    EpisodicEntry,
    IdentityEntry,
    ProceduralEntry,
    SemanticEntry,
    WorkingEntry,
)


class TestBaseEntry:
    def test_auto_id(self):
        entry = BaseEntry(tags=["test"])
        assert entry.id.startswith("blake3:")

    def test_deterministic_id(self):
        a = BaseEntry(created_at="2024-01-01T00:00:00+00:00", tags=["x"])
        b = BaseEntry(created_at="2024-01-01T00:00:00+00:00", tags=["x"])
        assert a.id == b.id

    def test_different_content_different_id(self):
        a = BaseEntry(created_at="2024-01-01T00:00:00+00:00", tags=["x"])
        b = BaseEntry(created_at="2024-01-01T00:00:00+00:00", tags=["y"])
        assert a.id != b.id

    def test_compute_id_excludes_id_field(self):
        entry = BaseEntry(created_at="2024-01-01T00:00:00+00:00", tags=["a"])
        original_id = entry.id
        assert entry.compute_id() == original_id

    def test_modified_content_changes_hash(self):
        entry = BaseEntry(created_at="2024-01-01T00:00:00+00:00", tags=["a"])
        original_id = entry.id
        entry.tags = ["b"]
        assert entry.compute_id() != original_id


class TestEpisodicEntry:
    def test_create(self):
        entry = EpisodicEntry(
            timestamp="2024-01-15T10:00:00Z",
            actor="user",
            observation="Asked about auth patterns",
            salience=0.8,
            event_type="interaction",
        )
        assert entry.id.startswith("blake3:")
        assert entry.salience == 0.8
        assert entry.event_type == "interaction"

    def test_default_values(self):
        entry = EpisodicEntry()
        assert entry.event_type == "observation"
        assert entry.salience == 0.5


class TestSemanticEntry:
    def test_create(self):
        entry = SemanticEntry(
            subject="project",
            predicate="uses",
            object="FastAPI",
            confidence=0.95,
        )
        assert entry.confidence == 0.95
        assert entry.subject == "project"


class TestProceduralEntry:
    def test_create(self):
        entry = ProceduralEntry(
            name="write_pytest_tests",
            description="Generate pytest tests with edge cases",
            body="def test_func(): ...",
            language="python",
        )
        assert entry.language == "python"
        assert entry.usage_count == 0


class TestWorkingEntry:
    def test_create(self):
        entry = WorkingEntry(
            goals=["Implement auth module"],
            scratch="Need to check JWT library",
        )
        assert len(entry.goals) == 1


class TestIdentityEntry:
    def test_create(self):
        entry = IdentityEntry(
            preferences={"style": "concise"},
            persona="helpful assistant",
            language="en",
            policies=["no PII"],
        )
        assert entry.persona == "helpful assistant"


class TestEntrySerialization:
    def test_json_round_trip(self):
        entry = EpisodicEntry(
            timestamp="2024-01-15T10:00:00Z",
            actor="user",
            observation="test",
            salience=0.7,
            event_type="interaction",
        )
        data = entry.model_dump(mode="json")
        restored = EpisodicEntry.model_validate(data)
        assert restored.id == entry.id
        assert restored.observation == entry.observation
