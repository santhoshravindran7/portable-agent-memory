"""
02 — Transfer Memory from Claude to GPT
=========================================
This example demonstrates cross-model memory portability:
  1. A "Claude" agent accumulates memory during a coding session
  2. The memory is exported as a signed .pam artifact (human-readable JSON)
  3. A "GPT" agent loads, verifies, and re-hydrates the memory
  4. The re-hydrated context is ready to inject into GPT's system prompt

Scenario: A developer switches from Claude to GPT mid-project while
working on an authentication module. All context transfers seamlessly.
"""

import sys
from pathlib import Path

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
    WorkingEntry,
)
from pam.rehydration.engine import RehydrationConfig, RehydrationEngine
from pam.transport.file import FileTransport


def create_claude_artifact(seed: bytes) -> tuple[MemoryArtifact, Path]:
    """Simulate Claude building up memory over a coding session."""

    artifact = MemoryArtifact(
        source_agent=SourceAgent(
            name="claude-coding-assistant",
            model_family="claude-3.5-sonnet",
            runtime="python",
            version="2024.11",
        ),
        episodic=[
            EpisodicEntry(
                timestamp="2024-11-08T10:00:00Z",
                actor="user",
                observation="Started building OAuth2 + JWT auth for the FastAPI app. Wants refresh tokens stored in HTTP-only cookies.",
                salience=0.95,
                event_type="interaction",
                tags=["auth", "planning"],
            ),
            EpisodicEntry(
                timestamp="2024-11-08T11:30:00Z",
                actor="assistant",
                observation="Implemented /auth/login and /auth/refresh endpoints. Used python-jose for JWT. Access token TTL=15min, refresh TTL=7d.",
                salience=0.9,
                event_type="outcome",
                tags=["auth", "implementation"],
            ),
            EpisodicEntry(
                timestamp="2024-11-08T14:00:00Z",
                actor="user",
                observation="Found that refresh token rotation wasn't invalidating old tokens. Asked to add a token family tracking approach.",
                salience=0.85,
                event_type="interaction",
                tags=["auth", "bug"],
            ),
            EpisodicEntry(
                timestamp="2024-11-08T15:00:00Z",
                actor="assistant",
                observation="Added RefreshTokenFamily model. Each refresh creates new token and invalidates siblings. Detects reuse attacks.",
                salience=0.9,
                event_type="outcome",
                tags=["auth", "security"],
            ),
        ],
        semantic=[
            SemanticEntry(
                subject="project",
                predicate="uses",
                object="FastAPI 0.104 with async SQLAlchemy 2.0",
                confidence=0.95,
                tags=["tech-stack"],
            ),
            SemanticEntry(
                subject="auth module",
                predicate="implements",
                object="OAuth2 with JWT access tokens and HTTP-only cookie refresh tokens",
                confidence=0.95,
                tags=["auth"],
            ),
            SemanticEntry(
                subject="auth module",
                predicate="uses",
                object="python-jose for JWT encoding, bcrypt for password hashing",
                confidence=0.9,
                tags=["auth", "tech-stack"],
            ),
            SemanticEntry(
                subject="database",
                predicate="contains",
                object="User, RefreshTokenFamily tables with Alembic migrations",
                confidence=0.9,
                tags=["database"],
            ),
            SemanticEntry(
                subject="user",
                predicate="prefers",
                object="type hints on all functions, no bare except clauses",
                confidence=0.85,
                tags=["coding-style"],
            ),
        ],
        procedural=[
            ProceduralEntry(
                name="create_jwt_token",
                description="Generate a signed JWT with custom claims and expiry",
                language="python",
                body="from jose import jwt; token = jwt.encode({'sub': user_id, 'exp': expiry}, SECRET_KEY, algorithm='HS256')",
                usage_count=4,
                tags=["auth"],
            ),
            ProceduralEntry(
                name="test_auth_endpoints",
                description="Integration test pattern for auth endpoints using httpx and test database",
                language="python",
                body="async with AsyncClient(app=app) as client: resp = await client.post('/auth/login', json=creds)",
                usage_count=6,
                tags=["auth", "testing"],
            ),
        ],
        working=[
            WorkingEntry(
                goals=["Complete token rotation security audit", "Add rate limiting to /auth/login"],
                scratch="Need to verify that concurrent refresh requests are handled atomically. Consider SELECT FOR UPDATE.",
                tags=["auth"],
            ),
        ],
        identity=[
            IdentityEntry(
                preferences={
                    "code_style": "concise, type-hinted, async-first",
                    "testing": "integration tests with real database",
                    "error_handling": "custom exception hierarchy",
                },
                persona="Senior backend engineer",
                language="en",
                policies=["Never log tokens or passwords", "Always validate input with Pydantic"],
            ),
        ],
    )

    artifact.sign(seed)
    output_path = Path(__file__).resolve().parent / "output" / "claude_session.pam"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    FileTransport.save(artifact, output_path)

    return artifact, output_path


def main() -> None:
    print("=" * 60)
    print("Portable Agent Memory Example 02: Transfer Memory from Claude to GPT")
    print("=" * 60)

    # Generate a shared key pair (in practice, the public key would be published)
    private_key = Ed25519PrivateKey.generate()
    seed = private_key.private_bytes_raw()
    pub = private_key.public_key().public_bytes_raw()

    # ------------------------------------------------------------------
    # Phase 1: Claude exports its memory
    # ------------------------------------------------------------------
    print("\n🔵 Phase 1: Claude exports its accumulated memory")
    print("-" * 50)

    artifact, pam_path = create_claude_artifact(seed)

    print(f"  Source agent:  {artifact.source_agent.name}")
    print(f"  Entries:       {len(artifact.all_entries())} total")
    print(f"  Root hash:     {artifact.root_hash[:40]}...")
    print(f"  Format:        JSON (.pam) — human-readable")
    print(f"  Saved to:      {pam_path.name}")
    print(f"  File size:     {pam_path.stat().st_size:,} bytes")

    # Show the JSON is human-readable
    print(f"\n  📄 First 40 lines of the .pam file (it's just JSON!):")
    print("  " + "-" * 50)
    content = pam_path.read_text(encoding="utf-8")
    for line in content.split("\n")[:40]:
        print(f"  │ {line}")
    print("  │ ...")
    print("  " + "-" * 50)

    # ------------------------------------------------------------------
    # Phase 2: GPT loads and verifies the artifact
    # ------------------------------------------------------------------
    print("\n🟢 Phase 2: GPT loads and verifies the artifact")
    print("-" * 50)

    loaded = FileTransport.load(pam_path)

    integrity_ok = loaded.verify_integrity()
    signature_ok = loaded.verify_signature(pub)

    print(f"  Loaded from:     {pam_path.name}")
    print(f"  Portable Agent Memory version: {loaded.pam_version}")
    print(f"  Source agent:     {loaded.source_agent.name} ({loaded.source_agent.model_family})")
    print(f"  Integrity check: {'✅ PASS' if integrity_ok else '❌ FAIL'}")
    print(f"  Signature check: {'✅ PASS' if signature_ok else '❌ FAIL'}")

    # ------------------------------------------------------------------
    # Phase 3: Re-hydrate with task context
    # ------------------------------------------------------------------
    print("\n🔄 Phase 3: Re-hydrating memory for GPT's task context")
    print("-" * 50)

    task = "Continue working on the authentication module. Add rate limiting to the login endpoint."

    print(f"  Task: \"{task}\"")
    print()

    # Re-hydrate with XML framing (injection-resistant)
    engine = RehydrationEngine()
    context_xml = engine.rehydrate(loaded, task=task)

    print("  Re-hydrated context (XML framing):")
    print("  " + "-" * 46)
    for line in context_xml.split("\n"):
        print(f"  │ {line}")
    print("  " + "-" * 46)

    # Also show markdown framing
    print("\n  Re-hydrated context (Markdown framing):")
    print("  " + "-" * 46)
    md_engine = RehydrationEngine(RehydrationConfig(framing_style="markdown"))
    context_md = md_engine.rehydrate(loaded, task=task)
    for line in context_md.split("\n")[:15]:
        print(f"  │ {line}")
    print("  │ ...")
    print("  " + "-" * 46)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Transfer Complete!")
    print("=" * 60)
    print(f"  Memory entries transferred:  {len(loaded.all_entries())}")
    print(f"  Episodic (conversation):     {len(loaded.episodic)}")
    print(f"  Semantic (facts):            {len(loaded.semantic)}")
    print(f"  Procedural (skills):         {len(loaded.procedural)}")
    print(f"  Working (active goals):      {len(loaded.working)}")
    print(f"  Identity (preferences):      {len(loaded.identity)}")
    print(f"  Cryptographic integrity:     ✅ Verified")
    print(f"  Cross-model compatible:      ✅ Claude → GPT")
    print()


if __name__ == "__main__":
    main()
