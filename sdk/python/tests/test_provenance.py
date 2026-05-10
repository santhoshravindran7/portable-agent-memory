"""Tests for Portable Agent Memory provenance graph."""

from pam.models.entries import EpisodicEntry, SemanticEntry
from pam.provenance.graph import ProvenanceGraph


def _make_episode(observation: str, **kwargs) -> EpisodicEntry:
    return EpisodicEntry(
        timestamp="2024-01-15T10:00:00Z",
        actor="user",
        observation=observation,
        salience=0.8,
        event_type="observation",
        **kwargs,
    )


class TestProvenanceGraph:
    def test_roots(self):
        e1 = _make_episode("first")
        e2 = _make_episode("second")
        graph = ProvenanceGraph([e1, e2])
        assert set(graph.roots()) == {e1.id, e2.id}

    def test_derive(self):
        e1 = _make_episode("first")
        graph = ProvenanceGraph([e1])
        child = _make_episode("derived")
        derived = graph.derive([e1.id], child)
        assert e1.id in derived.parent_ids
        assert derived.id != e1.id
        assert set(graph.roots()) == {e1.id}

    def test_verify_valid(self):
        e1 = _make_episode("first")
        graph = ProvenanceGraph([e1])
        assert graph.verify(e1.id)

    def test_verify_all(self):
        e1 = _make_episode("first")
        e2 = _make_episode("second")
        graph = ProvenanceGraph([e1, e2])
        ok, invalid = graph.verify_all()
        assert ok
        assert invalid == []

    def test_get_ancestors(self):
        e1 = _make_episode("root")
        graph = ProvenanceGraph([e1])
        e2 = _make_episode("child")
        e2 = graph.derive([e1.id], e2)
        e3 = _make_episode("grandchild")
        e3 = graph.derive([e2.id], e3)
        ancestors = graph.get_ancestors(e3.id)
        assert e1.id in ancestors
        assert e2.id in ancestors

    def test_get_descendants(self):
        e1 = _make_episode("root")
        graph = ProvenanceGraph([e1])
        e2 = _make_episode("child")
        e2 = graph.derive([e1.id], e2)
        descendants = graph.get_descendants(e1.id)
        assert e2.id in descendants

    def test_selective_disclose(self):
        e1 = _make_episode("root1")
        e2 = _make_episode("root2")
        graph = ProvenanceGraph([e1, e2])
        e3 = _make_episode("child of root1")
        e3 = graph.derive([e1.id], e3)
        disclosed = graph.selective_disclose([e1.id])
        disclosed_ids = {e.id for e in disclosed}
        assert e1.id in disclosed_ids
        assert e3.id in disclosed_ids
        assert e2.id not in disclosed_ids

    def test_to_dot(self):
        e1 = _make_episode("root")
        graph = ProvenanceGraph([e1])
        e2 = _make_episode("child")
        graph.derive([e1.id], e2)
        dot = graph.to_dot()
        assert "digraph provenance" in dot
        assert "->" in dot
