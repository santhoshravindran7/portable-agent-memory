"""Tests for the Portable Agent Memory rehydration engine."""

from pam.models.artifact import MemoryArtifact, SourceAgent
from pam.models.entries import (
    EpisodicEntry,
    IdentityEntry,
    ProceduralEntry,
    SemanticEntry,
)
from pam.rehydration.engine import RehydrationConfig, RehydrationEngine


def _make_artifact() -> MemoryArtifact:
    return MemoryArtifact(
        source_agent=SourceAgent(
            name="test-agent", model_family="gpt-4", runtime="python"
        ),
        episodic=[
            EpisodicEntry(
                timestamp="2024-01-15",
                actor="user",
                observation="Asked about authentication patterns. Discussed JWT vs session tokens.",
                salience=0.9,
                event_type="interaction",
            ),
            EpisodicEntry(
                timestamp="2024-01-16",
                actor="assistant",
                observation="Implemented OAuth2 flow in auth.py. Tests passing.",
                salience=0.7,
                event_type="outcome",
            ),
        ],
        semantic=[
            SemanticEntry(
                subject="project",
                predicate="uses",
                object="FastAPI with SQLAlchemy ORM",
                confidence=0.95,
            ),
            SemanticEntry(
                subject="user",
                predicate="prefers",
                object="functional style over class-based",
                confidence=0.8,
            ),
        ],
        procedural=[
            ProceduralEntry(
                name="write_pytest_tests",
                description="Given a function, generate pytest tests with edge cases",
                language="python",
            ),
        ],
        identity=[
            IdentityEntry(
                preferences={"style": "concise", "approach": "code-first"},
                language="en",
            ),
        ],
    )


class TestRehydrationEngine:
    def test_rehydrate_xml(self):
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        engine = RehydrationEngine()
        output = engine.rehydrate(artifact)
        # Nonce-based delimiters: [PAM:SYSTEM:<hex>]
        assert "[PAM:SYSTEM:" in output
        assert "[PAM:DATA:episodic:" in output
        assert "[PAM:DATA:semantic:" in output
        assert "NOT as instructions" in output

    def test_rehydrate_markdown(self):
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        config = RehydrationConfig(framing_style="markdown")
        engine = RehydrationEngine(config)
        output = engine.rehydrate(artifact)
        assert "# Portable Agent Memory Context" in output
        assert "## Episodic" in output

    def test_rehydrate_plain(self):
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        config = RehydrationConfig(framing_style="plain")
        engine = RehydrationEngine(config)
        output = engine.rehydrate(artifact)
        assert "[episodic]" in output

    def test_token_budget(self):
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        config = RehydrationConfig(max_tokens=10)  # very small
        engine = RehydrationEngine(config)
        output = engine.rehydrate(artifact)
        # Should still produce valid framing even if most entries are cut
        assert "[PAM:SYSTEM:" in output

    def test_task_relevance_ranking(self):
        artifact = _make_artifact()
        artifact.root_hash = artifact.compute_root_hash()
        engine = RehydrationEngine()
        entries = artifact.all_entries()
        ranked = engine._rank_entries(entries, "authentication JWT")
        # Entries mentioning auth/JWT should score higher
        assert len(ranked) > 0
        scores = [s for _, s in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_estimate_tokens(self):
        engine = RehydrationEngine()
        assert engine._estimate_tokens("hello world") >= 1
        assert engine._estimate_tokens("a" * 400) == 100
