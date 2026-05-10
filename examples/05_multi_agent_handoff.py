"""
05 — Agent Team Collaboration with Scoped Handoffs
====================================================
This example demonstrates a multi-agent workflow:
  1. Research Agent gathers data and builds episodic/semantic memory
  2. Exports a scoped artifact to Writing Agent (only facts + skills)
  3. Writing Agent adds its own working state
  4. Exports full artifact to Review Agent with complete provenance

Scenario: A content team uses three specialized AI agents to produce
a technical blog post. Memory flows between agents with scoping.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sdk" / "python"))

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pam.capabilities.tokens import (
    CapabilityScope,
    CapabilityToken,
    CapabilityValidator,
)
from pam.models.artifact import MemoryArtifact, SourceAgent
from pam.models.entries import (
    EpisodicEntry,
    IdentityEntry,
    ProceduralEntry,
    SemanticEntry,
    WorkingEntry,
)
from pam.rehydration.engine import RehydrationConfig, RehydrationEngine
from pam.transport.file import FileTransport


def main() -> None:
    print("=" * 60)
    print("Portable Agent Memory Example 05: Multi-Agent Handoff with Scoped Memory")
    print("=" * 60)

    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Shared key pair for signing across the team
    team_key = Ed25519PrivateKey.generate()
    team_seed = team_key.private_bytes_raw()
    team_pub = team_key.public_key().public_bytes_raw()

    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    # ══════════════════════════════════════════════════════════════
    # Agent 1: Research Agent
    # ══════════════════════════════════════════════════════════════
    print("\n🔬 Agent 1: Research Agent")
    print("=" * 60)
    print("  Task: Research WebAssembly adoption for a blog post")

    research_episodes = [
        EpisodicEntry(
            timestamp="2024-11-12T09:00:00Z",
            actor="research-agent",
            observation="Surveyed 15 recent articles on WebAssembly adoption in production. Key trend: WASM moving beyond browsers into server-side and edge computing.",
            salience=0.9,
            event_type="observation",
            tags=["research", "wasm"],
        ),
        EpisodicEntry(
            timestamp="2024-11-12T09:30:00Z",
            actor="research-agent",
            observation="Analyzed GitHub data: WASM repos grew 47% YoY. Rust is the most popular source language (34%), followed by C++ (28%) and Go (15%).",
            salience=0.85,
            event_type="observation",
            tags=["research", "statistics"],
        ),
        EpisodicEntry(
            timestamp="2024-11-12T10:00:00Z",
            actor="research-agent",
            observation="Interviewed notes: Figma uses WASM for their design tool renderer. Cloudflare Workers supports WASM modules. Docker now has WASM runtime support.",
            salience=0.95,
            event_type="observation",
            tags=["research", "case-studies"],
        ),
    ]

    research_facts = [
        SemanticEntry(
            subject="WebAssembly",
            predicate="adoption_trend",
            object="Moving from browser-only to universal runtime: server-side, edge, IoT, and plugin systems",
            confidence=0.9,
            tags=["fact", "wasm"],
        ),
        SemanticEntry(
            subject="WebAssembly",
            predicate="key_advantage",
            object="Near-native performance with sandboxed execution and language-agnostic compilation target",
            confidence=0.95,
            tags=["fact", "wasm"],
        ),
        SemanticEntry(
            subject="WebAssembly ecosystem",
            predicate="top_languages",
            object="Rust (34%), C++ (28%), Go (15%), AssemblyScript (12%)",
            confidence=0.85,
            tags=["fact", "statistics"],
        ),
        SemanticEntry(
            subject="WebAssembly",
            predicate="notable_adopters",
            object="Figma (renderer), Cloudflare (edge workers), Docker (WASM runtime), Shopify (plugin system)",
            confidence=0.9,
            tags=["fact", "case-studies"],
        ),
    ]

    research_artifact = MemoryArtifact(
        source_agent=SourceAgent(
            name="research-agent", model_family="claude-3.5-sonnet", runtime="python"
        ),
        episodic=research_episodes,
        semantic=research_facts,
    )
    research_artifact.sign(team_seed)

    # Save full research artifact
    research_path = output_dir / "01_research.pam"
    FileTransport.save(research_artifact, research_path)

    print(f"  Episodic entries: {len(research_episodes)}")
    print(f"  Semantic entries: {len(research_facts)}")
    print(f"  Total: {len(research_artifact.all_entries())} entries")
    print(f"  Saved: {research_path.name}")

    # ══════════════════════════════════════════════════════════════
    # Handoff 1: Research → Writing (scoped to facts + case studies)
    # ══════════════════════════════════════════════════════════════
    print("\n📤 Handoff 1: Research Agent → Writing Agent")
    print("-" * 60)
    print("  Scoping: Only semantic facts (no raw research episodes)")

    # Create a capability token that limits to semantic entries only
    writing_token = CapabilityToken(
        scope=CapabilityScope(type="component", value=["semantic"]),
        permissions=["read"],
        issuer="research-agent",
        audience="writing-agent",
        expires_at=expires,
    )
    writing_token.sign(team_seed)

    validator = CapabilityValidator()
    all_research_entries = research_artifact.all_entries()
    writing_entries = validator.filter_entries(all_research_entries, writing_token)

    print(f"  Full artifact:   {len(all_research_entries)} entries")
    print(f"  Scoped for writer: {len(writing_entries)} entries")
    print(f"  Filtered out:    {len(all_research_entries) - len(writing_entries)} entries (raw research logs)")

    # ══════════════════════════════════════════════════════════════
    # Agent 2: Writing Agent
    # ══════════════════════════════════════════════════════════════
    print("\n✍️  Agent 2: Writing Agent")
    print("=" * 60)
    print("  Task: Draft blog post from research facts")

    # Writing agent re-hydrates the scoped memory
    engine = RehydrationEngine(RehydrationConfig(framing_style="markdown"))
    writer_context = engine.rehydrate(
        research_artifact,
        task="Write a technical blog post about WebAssembly adoption trends",
        capability_token=writing_token,
        public_key=team_pub,
    )

    print("  Re-hydrated context (first 10 lines):")
    for line in writer_context.split("\n")[:10]:
        print(f"    │ {line}")
    print("    │ ...")

    # Writing agent adds its own entries
    writing_skills = [
        ProceduralEntry(
            name="technical_blog_structure",
            description="Structure: Hook → Context → 3 Key Points with examples → Practical takeaway → CTA",
            language="natural",
            usage_count=12,
            tags=["writing", "blog"],
        ),
    ]

    writing_state = [
        WorkingEntry(
            goals=["Draft 1,500-word blog post on WASM adoption"],
            scratch="Outline: 1) WASM beyond the browser, 2) Production case studies (Figma, Cloudflare, Docker), 3) Getting started with WASM + Rust",
            pending_actions=[
                {"action": "Write introduction hook", "status": "done"},
                {"action": "Write section on production adopters", "status": "done"},
                {"action": "Write getting-started guide", "status": "in_progress"},
                {"action": "Add code examples", "status": "pending"},
            ],
            tags=["writing", "draft"],
        ),
    ]

    # Build combined artifact with research facts + writing additions
    # The semantic entries from research carry forward
    writing_artifact = MemoryArtifact(
        source_agent=SourceAgent(
            name="writing-agent", model_family="gpt-4-turbo", runtime="python"
        ),
        semantic=[e for e in writing_entries if isinstance(e, SemanticEntry)],
        procedural=writing_skills,
        working=writing_state,
        metadata={"upstream_agent": "research-agent", "upstream_root_hash": research_artifact.root_hash},
    )
    writing_artifact.sign(team_seed)

    writing_path = output_dir / "02_writing.pam"
    FileTransport.save(writing_artifact, writing_path)

    print(f"\n  Inherited semantic: {len(writing_artifact.semantic)} entries")
    print(f"  New procedural:    {len(writing_artifact.procedural)} entries")
    print(f"  New working:       {len(writing_artifact.working)} entries")
    print(f"  Total: {len(writing_artifact.all_entries())} entries")
    print(f"  Saved: {writing_path.name}")

    # ══════════════════════════════════════════════════════════════
    # Handoff 2: Writing → Review (full access for quality review)
    # ══════════════════════════════════════════════════════════════
    print("\n📤 Handoff 2: Writing Agent → Review Agent")
    print("-" * 60)
    print("  Scoping: Full access (reviewer needs complete context)")

    review_token = CapabilityToken(
        scope=CapabilityScope(type="wildcard", value="*"),
        permissions=["read"],
        issuer="writing-agent",
        audience="review-agent",
        expires_at=expires,
    )
    review_token.sign(team_seed)

    # ══════════════════════════════════════════════════════════════
    # Agent 3: Review Agent
    # ══════════════════════════════════════════════════════════════
    print("\n📝 Agent 3: Review Agent")
    print("=" * 60)
    print("  Task: Review the blog post draft for accuracy and quality")

    # Review agent loads and verifies the writing artifact
    loaded_writing = FileTransport.load(writing_path)
    integrity_ok = loaded_writing.verify_integrity()
    sig_ok = loaded_writing.verify_signature(team_pub)

    print(f"  Integrity: {'✅ PASS' if integrity_ok else '❌ FAIL'}")
    print(f"  Signature: {'✅ PASS' if sig_ok else '❌ FAIL'}")

    # Re-hydrate with review task
    review_engine = RehydrationEngine(RehydrationConfig(framing_style="xml"))
    review_context = review_engine.rehydrate(
        loaded_writing,
        task="Review blog post for technical accuracy and completeness",
        capability_token=review_token,
        public_key=team_pub,
    )

    print(f"\n  Re-hydrated context for reviewer ({len(review_context)} chars):")
    for line in review_context.split("\n")[:12]:
        print(f"    │ {line}")
    print("    │ ...")

    # Review agent can see the full provenance chain
    print(f"\n  Upstream agent: {loaded_writing.metadata.get('upstream_agent', 'N/A')}")
    print(f"  Upstream hash:  {loaded_writing.metadata.get('upstream_root_hash', 'N/A')[:40]}...")

    # Verify upstream artifact integrity too
    loaded_research = FileTransport.load(research_path)
    upstream_ok = loaded_research.verify_integrity()
    upstream_sig = loaded_research.verify_signature(team_pub)
    print(f"  Upstream integrity: {'✅ PASS' if upstream_ok else '❌ FAIL'}")
    print(f"  Upstream signature: {'✅ PASS' if upstream_sig else '❌ FAIL'}")

    # ══════════════════════════════════════════════════════════════
    # End-to-End Summary
    # ══════════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("End-to-End Multi-Agent Handoff Summary")
    print("=" * 60)
    print()
    print("  Pipeline: Research → Writing → Review")
    print()
    print("  ┌─────────────────────┐")
    print("  │   Research Agent    │  3 episodic + 4 semantic = 7 entries")
    print("  │  (claude-3.5-sonnet)│")
    print("  └────────┬────────────┘")
    print("           │ scoped: semantic only (4 entries)")
    print("  ┌────────▼────────────┐")
    print("  │   Writing Agent     │  4 semantic + 1 procedural + 1 working = 6 entries")
    print("  │   (gpt-4-turbo)     │")
    print("  └────────┬────────────┘")
    print("           │ full access (6 entries)")
    print("  ┌────────▼────────────┐")
    print("  │   Review Agent      │  Verifies integrity + provenance chain")
    print("  │   (any model)       │")
    print("  └─────────────────────┘")
    print()
    print("  Artifacts generated:")
    print(f"    • {research_path.name} ({research_path.stat().st_size:,} bytes)")
    print(f"    • {writing_path.name} ({writing_path.stat().st_size:,} bytes)")
    print()
    print("  Security properties preserved:")
    print("    ✅ All artifacts signed with Ed25519")
    print("    ✅ Content-addressable entry IDs (BLAKE3)")
    print("    ✅ Scoped handoffs via capability tokens")
    print("    ✅ Provenance chain traceable to source")
    print("    ✅ Cross-model transfer (Claude → GPT → any)")
    print()


if __name__ == "__main__":
    main()
