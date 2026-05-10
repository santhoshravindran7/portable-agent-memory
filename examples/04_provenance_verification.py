"""
04 — Tamper-Evident Memory with Merkle-DAG Provenance
======================================================
This example demonstrates Portable Agent Memory's provenance graph:
  1. Create entries with parent-child derivation relationships
  2. Build a Merkle-DAG and verify integrity
  3. Simulate tampering and detect it
  4. Export the graph as DOT for visualization

Scenario: An AI research assistant observes raw data, derives facts,
and then summarizes. Each derivation step is tracked in a Merkle-DAG
so any tampering is detectable.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sdk" / "python"))

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pam.models.entries import EpisodicEntry, SemanticEntry
from pam.provenance.graph import ProvenanceGraph


def main() -> None:
    print("=" * 60)
    print("Portable Agent Memory Example 04: Tamper-Evident Provenance Verification")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Create root entries (raw observations)
    # ------------------------------------------------------------------
    print("\n📄 Step 1: Creating root entries (raw observations)...")

    obs1 = EpisodicEntry(
        timestamp="2024-11-10T09:00:00Z",
        actor="research-agent",
        observation="Analyzed repository: 142 Python files, 3 Dockerfiles, CI/CD with GitHub Actions.",
        salience=0.8,
        event_type="observation",
        tags=["codebase-analysis"],
    )

    obs2 = EpisodicEntry(
        timestamp="2024-11-10T09:05:00Z",
        actor="research-agent",
        observation="Ran test suite: 847 tests, 12 failures in auth module, avg coverage 78%.",
        salience=0.9,
        event_type="observation",
        tags=["test-analysis"],
    )

    obs3 = EpisodicEntry(
        timestamp="2024-11-10T09:10:00Z",
        actor="research-agent",
        observation="Reviewed PR #312: adds rate limiting middleware, +450 lines, 3 approvals.",
        salience=0.7,
        event_type="observation",
        tags=["pr-review"],
    )

    graph = ProvenanceGraph([obs1, obs2, obs3])

    print(f"  Root 1: {obs1.observation[:60]}...")
    print(f"    ID: {obs1.id[:30]}...")
    print(f"  Root 2: {obs2.observation[:60]}...")
    print(f"    ID: {obs2.id[:30]}...")
    print(f"  Root 3: {obs3.observation[:60]}...")
    print(f"    ID: {obs3.id[:30]}...")
    print(f"  Graph roots: {len(graph.roots())}")

    # ------------------------------------------------------------------
    # Step 2: Derive facts from observations
    # ------------------------------------------------------------------
    print("\n🔗 Step 2: Deriving facts from observations...")

    # Derived from obs1 + obs2: a fact about project health
    fact1 = SemanticEntry(
        subject="project",
        predicate="health_status",
        object="Moderate — 78% coverage but 12 test failures in auth module need attention",
        confidence=0.85,
        tags=["derived-fact"],
    )
    fact1 = graph.derive([obs1.id, obs2.id], fact1)

    print(f"  Fact 1 (from obs1 + obs2): {fact1.subject} {fact1.predicate}")
    print(f"    → {fact1.object}")
    print(f"    Parents: {len(fact1.parent_ids)}")

    # Derived from obs2: a specific finding
    fact2 = SemanticEntry(
        subject="auth module",
        predicate="has_issue",
        object="12 failing tests — likely related to recent token rotation changes",
        confidence=0.8,
        tags=["derived-fact"],
    )
    fact2 = graph.derive([obs2.id], fact2)

    print(f"  Fact 2 (from obs2): {fact2.subject} {fact2.predicate}")
    print(f"    → {fact2.object}")

    # ------------------------------------------------------------------
    # Step 3: Derive a summary from the facts
    # ------------------------------------------------------------------
    print("\n📊 Step 3: Deriving summary from facts...")

    summary = SemanticEntry(
        subject="weekly-report",
        predicate="summary",
        object="Auth module needs immediate attention: 12 test failures, likely from token rotation. "
               "Overall coverage at 78%. PR #312 adds rate limiting (approved, ready to merge).",
        confidence=0.9,
        tags=["summary"],
    )
    summary = graph.derive([fact1.id, fact2.id, obs3.id], summary)

    print(f"  Summary derived from: fact1 + fact2 + obs3")
    print(f"  → {summary.object[:80]}...")
    print(f"  Ancestors of summary: {len(graph.get_ancestors(summary.id))}")

    # ------------------------------------------------------------------
    # Step 4: Verify integrity (should pass)
    # ------------------------------------------------------------------
    print("\n✅ Step 4: Verifying provenance integrity...")

    ok, invalid = graph.verify_all()
    print(f"  Full graph verification: {'PASS ✅' if ok else 'FAIL ❌'}")
    print(f"  Invalid entries: {len(invalid)}")

    # Verify individual chain from summary to roots
    chain_ok = graph.verify(summary.id)
    print(f"  Summary chain verification: {'PASS ✅' if chain_ok else 'FAIL ❌'}")

    # Show ancestry
    ancestors = graph.get_ancestors(summary.id)
    print(f"  Summary has {len(ancestors)} ancestors in its provenance chain")
    descendants = graph.get_descendants(obs2.id)
    print(f"  obs2 has {len(descendants)} descendants (fact1, fact2, summary)")

    # ------------------------------------------------------------------
    # Step 5: Simulate tampering
    # ------------------------------------------------------------------
    print("\n🔓 Step 5: Simulating tampering...")
    print("  Modifying obs2's observation text (simulating a malicious edit)...")

    original_observation = obs2.observation
    obs2.observation = "Ran test suite: 847 tests, 0 failures, avg coverage 99%."

    print(f"  Original: \"{original_observation[:50]}...\"")
    print(f"  Tampered: \"{obs2.observation[:50]}...\"")

    # ------------------------------------------------------------------
    # Step 6: Detect tampering
    # ------------------------------------------------------------------
    print("\n🚨 Step 6: Detecting tampering...")

    # The stored ID no longer matches the content hash
    recomputed_id = obs2.compute_id()
    id_mismatch = recomputed_id != obs2.id
    print(f"  Stored ID:     {obs2.id[:40]}...")
    print(f"  Recomputed ID: {recomputed_id[:40]}...")
    print(f"  ID mismatch:   {'YES — TAMPERED! 🚨' if id_mismatch else 'No'}")

    # Full graph verification now fails
    ok2, invalid2 = graph.verify_all()
    print(f"\n  Full graph verification: {'PASS ✅' if ok2 else 'FAIL ❌ — tampering detected!'}")
    print(f"  Invalid entries: {len(invalid2)}")
    for inv_id in invalid2:
        print(f"    🚨 Tampered: {inv_id[:40]}...")

    # Chain verification from summary also fails (obs2 is an ancestor)
    chain_ok2 = graph.verify(summary.id)
    print(f"\n  Summary chain verification: {'PASS ✅' if chain_ok2 else 'FAIL ❌ — ancestor tampered!'}")

    # Restore original for DOT export
    obs2.observation = original_observation

    # ------------------------------------------------------------------
    # Step 7: Export DOT graph
    # ------------------------------------------------------------------
    print("\n📈 Step 7: Exporting provenance graph as DOT...")

    dot_output = graph.to_dot()

    output_path = Path(__file__).resolve().parent / "output" / "provenance.dot"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dot_output, encoding="utf-8")

    print(f"  Saved to: {output_path.name}")
    print(f"\n  DOT graph:")
    for line in dot_output.split("\n"):
        print(f"    {line}")

    # ------------------------------------------------------------------
    # Step 8: Selective disclosure
    # ------------------------------------------------------------------
    print("\n🔒 Step 8: Selective disclosure (share only obs1's subtree)...")

    disclosed = graph.selective_disclose([obs1.id])
    all_ids = {obs1.id, obs2.id, obs3.id, fact1.id, fact2.id, summary.id}
    disclosed_ids = {e.id for e in disclosed}

    print(f"  Disclosing from root: obs1")
    print(f"  Entries shared: {len(disclosed)} / 6 total")
    print(f"  Shared entries:")
    for entry in disclosed:
        if isinstance(entry, EpisodicEntry):
            print(f"    • [episodic] {entry.observation[:50]}...")
        elif isinstance(entry, SemanticEntry):
            print(f"    • [semantic] {entry.subject} {entry.predicate}")
    hidden = all_ids - disclosed_ids
    print(f"  Hidden entries: {len(hidden)}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Provenance Verification Summary")
    print("=" * 60)
    print("  ✅ Content-addressable IDs detect any modification")
    print("  ✅ Merkle-DAG chains verify derived data back to sources")
    print("  ✅ Selective disclosure shares subgraphs without full exposure")
    print("  ✅ DOT export enables visual inspection of provenance")
    print()


if __name__ == "__main__":
    main()
