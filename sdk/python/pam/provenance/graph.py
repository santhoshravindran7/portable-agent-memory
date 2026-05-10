"""Merkle-DAG provenance graph for Portable Agent Memory entries."""

from __future__ import annotations

from collections import defaultdict

from ..models.base import BaseEntry


class ProvenanceGraph:
    """Merkle-DAG provenance graph for memory entries.

    Tracks parent/child relationships and supports verification,
    derivation, and selective disclosure.
    """

    def __init__(self, entries: list[BaseEntry] | None = None) -> None:
        self._entries: dict[str, BaseEntry] = {}
        self._children: dict[str, list[str]] = defaultdict(list)
        self._parents: dict[str, list[str]] = defaultdict(list)
        if entries:
            for entry in entries:
                self.add(entry)

    def add(self, entry: BaseEntry) -> None:
        """Add an entry to the graph. Raises ValueError if it would create a cycle."""
        # Cycle detection: check if any parent is a descendant of this entry
        if entry.id in self._entries:
            for pid in entry.parent_ids:
                if pid == entry.id or entry.id in self._get_ancestors_set(pid):
                    raise ValueError(
                        f"Adding entry {entry.id[:16]}... with parent {pid[:16]}... would create a cycle"
                    )
        self._entries[entry.id] = entry
        self._parents[entry.id] = list(entry.parent_ids)
        for pid in entry.parent_ids:
            self._children[pid].append(entry.id)

    def _get_ancestors_set(self, entry_id: str) -> set[str]:
        """Internal: get ancestor set for cycle detection."""
        visited: set[str] = set()
        stack = list(self._parents.get(entry_id, []))
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self._parents.get(current, []))
        return visited

    def verify(self, entry_id: str) -> bool:
        """Verify hash chain from entry to roots (iterative, cycle-safe)."""
        visited: set[str] = set()
        stack = [entry_id]
        while stack:
            eid = stack.pop()
            if eid in visited:
                continue
            visited.add(eid)
            entry = self._entries.get(eid)
            if entry is None:
                return False
            if entry.compute_id() != entry.id:
                return False
            stack.extend(entry.parent_ids)
        return True

    def verify_all(self) -> tuple[bool, list[str]]:
        """Verify all entries. Return ``(ok, list_of_invalid_ids)``."""
        invalid: list[str] = []
        for eid, entry in self._entries.items():
            if entry.compute_id() != eid:
                invalid.append(eid)
        return (len(invalid) == 0, invalid)

    def derive(self, parent_ids: list[str], new_entry: BaseEntry) -> BaseEntry:
        """Create a new entry derived from the given parents.

        Sets ``parent_ids`` on the entry, recomputes its ID, and adds
        it to the graph.
        """
        new_entry.parent_ids = list(parent_ids)
        new_entry.id = ""  # reset so post-init recomputes
        new_entry.id = new_entry.compute_id()
        self.add(new_entry)
        return new_entry

    def get_ancestors(self, entry_id: str) -> list[str]:
        """Get all ancestor entry IDs (transitive parents)."""
        visited: set[str] = set()
        stack = list(self._parents.get(entry_id, []))
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self._parents.get(current, []))
        return sorted(visited)

    def get_descendants(self, entry_id: str) -> list[str]:
        """Get all descendant entry IDs (transitive children)."""
        visited: set[str] = set()
        stack = list(self._children.get(entry_id, []))
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self._children.get(current, []))
        return sorted(visited)

    def selective_disclose(self, root_ids: list[str]) -> list[BaseEntry]:
        """Return entries reachable from given root IDs (including roots)."""
        visited: set[str] = set()
        stack = list(root_ids)
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self._children.get(current, []))
        return [self._entries[eid] for eid in sorted(visited) if eid in self._entries]

    def roots(self) -> list[str]:
        """Return entry IDs that have no parents."""
        return sorted(
            eid for eid, entry in self._entries.items() if not entry.parent_ids
        )

    def to_dot(self) -> str:
        """Export the graph as Graphviz DOT."""
        lines = ["digraph provenance {"]
        for eid in sorted(self._entries):
            label = eid[:16]
            lines.append(f'  "{eid}" [label="{label}"];')
        for eid, entry in sorted(self._entries.items()):
            for pid in entry.parent_ids:
                lines.append(f'  "{pid}" -> "{eid}";')
        lines.append("}")
        return "\n".join(lines)
