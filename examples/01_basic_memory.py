"""
01 — Create Your First Portable Agent Memory Artifact
====================================
This example shows how to:
  1. Create different types of memory entries (episodic, semantic, procedural, identity)
  2. Bundle them into a signed MemoryArtifact
  3. Save to a .pam file (human-readable JSON) and verify integrity

Scenario: A coding assistant has been helping a developer build a FastAPI project.
We capture the assistant's accumulated memory and export it as a portable artifact.
"""

import sys
from pathlib import Path

# Ensure the SDK is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sdk" / "python"))

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pam.models.artifact import MemoryArtifact, SourceAgent
from pam.models.entries import (
    EpisodicEntry,
    IdentityEntry,
    ProceduralEntry,
    SemanticEntry,
)
from pam.transport.file import FileTransport


def main() -> None:
    print("=" * 60)
    print("Portable Agent Memory Example 01: Create Your First Portable Agent Memory Artifact")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Create episodic entries (conversation history)
    # ------------------------------------------------------------------
    print("\n📝 Creating episodic entries (conversation history)...")

    episodes = [
        EpisodicEntry(
            timestamp="2024-11-10T09:15:00Z",
            actor="user",
            observation="Asked me to set up a new FastAPI project with SQLAlchemy and Alembic migrations.",
            salience=0.9,
            event_type="interaction",
            tags=["project-setup"],
        ),
        EpisodicEntry(
            timestamp="2024-11-10T09:45:00Z",
            actor="assistant",
            observation="Scaffolded project structure: app/, app/models/, app/routes/, app/services/. Created initial database models for User and Team.",
            salience=0.8,
            event_type="outcome",
            tags=["project-setup", "database"],
        ),
        EpisodicEntry(
            timestamp="2024-11-11T14:00:00Z",
            actor="user",
            observation="Reported a bug: login endpoint returns 500 when email has uppercase letters.",
            salience=0.95,
            event_type="interaction",
            tags=["bug", "auth"],
        ),
        EpisodicEntry(
            timestamp="2024-11-11T14:30:00Z",
            actor="assistant",
            observation="Fixed case-sensitivity bug by normalizing email to lowercase in the User model's validator. Added regression test.",
            salience=0.85,
            event_type="outcome",
            tags=["bug", "auth"],
        ),
    ]

    for ep in episodes:
        print(f"  [{ep.event_type}] {ep.observation[:70]}...")

    # ------------------------------------------------------------------
    # Step 2: Create semantic entries (learned facts)
    # ------------------------------------------------------------------
    print("\n🧠 Creating semantic entries (learned facts)...")

    facts = [
        SemanticEntry(
            subject="project",
            predicate="uses",
            object="FastAPI 0.104 with SQLAlchemy 2.0 async",
            confidence=0.95,
            tags=["tech-stack"],
        ),
        SemanticEntry(
            subject="project",
            predicate="requires",
            object="PostgreSQL 15 for production, SQLite for tests",
            confidence=0.9,
            tags=["tech-stack", "database"],
        ),
        SemanticEntry(
            subject="user",
            predicate="prefers",
            object="functional style with dependency injection over class-based services",
            confidence=0.85,
            tags=["coding-style"],
        ),
    ]

    for fact in facts:
        print(f"  {fact.subject} {fact.predicate} → {fact.object}")

    # ------------------------------------------------------------------
    # Step 3: Create procedural entries (learned skills)
    # ------------------------------------------------------------------
    print("\n⚙️  Creating procedural entries (learned skills)...")

    skills = [
        ProceduralEntry(
            name="generate_alembic_migration",
            description="Create an Alembic migration from model changes, run autogenerate, and verify the upgrade/downgrade SQL",
            language="python",
            body="alembic revision --autogenerate -m '<message>' && alembic upgrade head",
            usage_count=3,
            tags=["database", "migrations"],
        ),
        ProceduralEntry(
            name="write_integration_test",
            description="Write a pytest integration test using httpx AsyncClient with database fixtures",
            language="python",
            body="async def test_endpoint(client: AsyncClient, db: AsyncSession): ...",
            usage_count=7,
            tags=["testing"],
        ),
    ]

    for skill in skills:
        print(f'  Skill: "{skill.name}" (used {skill.usage_count}x)')

    # ------------------------------------------------------------------
    # Step 4: Create identity entries (user preferences)
    # ------------------------------------------------------------------
    print("\n🪪  Creating identity entry (user preferences)...")

    identity = IdentityEntry(
        preferences={
            "code_style": "concise, no unnecessary comments",
            "error_handling": "use custom exception classes",
            "testing": "prefer integration tests over unit tests",
        },
        persona="Senior Python backend developer",
        language="en",
        policies=["No print statements in production code", "Always type-hint function signatures"],
        tags=["preferences"],
    )

    print(f"  Persona: {identity.persona}")
    print(f"  Policies: {', '.join(identity.policies)}")

    # ------------------------------------------------------------------
    # Step 5: Bundle into a MemoryArtifact and sign
    # ------------------------------------------------------------------
    print("\n📦 Bundling into MemoryArtifact...")

    artifact = MemoryArtifact(
        source_agent=SourceAgent(
            name="coding-assistant",
            model_family="claude-3.5-sonnet",
            runtime="python",
            version="1.0.0",
        ),
        episodic=episodes,
        semantic=facts,
        procedural=skills,
        identity=[identity],
    )

    # Generate Ed25519 key pair and sign
    private_key = Ed25519PrivateKey.generate()
    seed = private_key.private_bytes_raw()
    pub = private_key.public_key().public_bytes_raw()

    signature = artifact.sign(seed)

    print(f"  Source agent: {artifact.source_agent.name} ({artifact.source_agent.model_family})")
    print(f"  Root hash:   {artifact.root_hash[:40]}...")
    print(f"  Signature:   {signature[:40]}...")
    print(f"  Entries:     {len(artifact.all_entries())} total")

    # ------------------------------------------------------------------
    # Step 6: Save to .pam file (human-readable JSON)
    # ------------------------------------------------------------------
    output_path = Path(__file__).resolve().parent / "output" / "my_first_artifact.pam"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    FileTransport.save(artifact, output_path)
    file_size = output_path.stat().st_size

    print(f"\n💾 Saved to: {output_path}")
    print(f"  File size: {file_size:,} bytes")
    print(f"  Format:    JSON (.pam) — human-readable, inspect with any text editor")

    # ------------------------------------------------------------------
    # Step 7: Verify integrity
    # ------------------------------------------------------------------
    print("\n🔒 Verifying integrity...")

    loaded = FileTransport.load(output_path)

    integrity_ok = loaded.verify_integrity()
    signature_ok = loaded.verify_signature(pub)

    print(f"  Integrity check: {'✅ PASS' if integrity_ok else '❌ FAIL'}")
    print(f"  Signature check: {'✅ PASS' if signature_ok else '❌ FAIL'}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Episodic entries:   {len(artifact.episodic)}")
    print(f"  Semantic entries:   {len(artifact.semantic)}")
    print(f"  Procedural entries: {len(artifact.procedural)}")
    print(f"  Identity entries:   {len(artifact.identity)}")
    print(f"  Total entries:      {len(artifact.all_entries())}")
    print(f"  Artifact signed:    Yes (Ed25519)")
    print(f"  File format:        JSON (.pam)")
    print(f"  All checks passed:  {'✅' if integrity_ok and signature_ok else '❌'}")
    print()


if __name__ == "__main__":
    main()
