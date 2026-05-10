"""
08 — Multi-Session Continuity (Session Amnesia Prevention)
==========================================================
Demonstrates how Portable Agent Memory solves the "session amnesia" problem:
agents lose all context when a session ends.

Business Value:
  - Developers don't re-explain their codebase every new chat session
  - Customer support agents maintain context across shift changes
  - Research agents accumulate knowledge across weeks of investigation
  - Cost savings: no wasted tokens re-establishing context

Scenario:
  A developer has 3 coding sessions across 3 days. Each session's
  knowledge accumulates into the memory artifact. By session 3,
  the agent knows everything from sessions 1 and 2 — even though
  each session used a fresh context window.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sdk" / "python"))

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tempfile

from pam.models.artifact import MemoryArtifact, SourceAgent
from pam.models.entries import (
    EpisodicEntry,
    ProceduralEntry,
    SemanticEntry,
    WorkingEntry,
    IdentityEntry,
)
from pam.rehydration.engine import RehydrationEngine
from pam.transport.file import FileTransport


def simulate_session(
    session_num: int,
    day: str,
    existing_artifact: MemoryArtifact | None,
) -> MemoryArtifact:
    """Simulate a coding session that builds on previous memory."""

    if existing_artifact:
        artifact = existing_artifact
        # Reset root_hash since we'll be adding new entries
        artifact.root_hash = ""
    else:
        artifact = MemoryArtifact(
            source_agent=SourceAgent(
                name="dev-assistant",
                model_family="claude",
                runtime="copilot-cli",
            ),
        )

    if session_num == 1:
        artifact.episodic.append(EpisodicEntry(
            timestamp=f"{day}T09:00:00Z",
            actor="user",
            observation="Starting new e-commerce project. Tech stack: Next.js 14, Prisma, PostgreSQL, Stripe for payments.",
            salience=1.0,
            event_type="interaction",
            tags=["project-init"],
        ))
        artifact.episodic.append(EpisodicEntry(
            timestamp=f"{day}T11:00:00Z",
            actor="agent",
            observation="Set up project structure with app router, created Prisma schema with User, Product, Order, OrderItem models.",
            salience=0.9,
            event_type="outcome",
            tags=["implementation"],
        ))
        artifact.semantic.extend([
            SemanticEntry(subject="project", predicate="uses", object="Next.js 14 app router with TypeScript", confidence=0.95),
            SemanticEntry(subject="database", predicate="is", object="PostgreSQL via Prisma ORM", confidence=0.95),
            SemanticEntry(subject="payments", predicate="handled by", object="Stripe with webhook verification", confidence=0.9),
        ])
        artifact.procedural.append(ProceduralEntry(
            name="prisma_migrate",
            description="Run Prisma migration and generate client",
            body="npx prisma migrate dev --name <migration_name> && npx prisma generate",
            language="shell",
        ))
        artifact.identity.append(IdentityEntry(
            preferences={"framework": "Next.js", "orm": "Prisma", "style": "functional React, server components preferred"},
            persona="Full-stack TypeScript developer",
            language="en",
            policies=["Use server components by default", "Validate all inputs with Zod"],
        ))

    elif session_num == 2:
        artifact.episodic.append(EpisodicEntry(
            timestamp=f"{day}T10:00:00Z",
            actor="user",
            observation="Need to implement shopping cart. Should persist in database for logged-in users, localStorage for guests.",
            salience=0.9,
            event_type="interaction",
            tags=["cart"],
        ))
        artifact.episodic.append(EpisodicEntry(
            timestamp=f"{day}T14:00:00Z",
            actor="agent",
            observation="Implemented CartItem model in Prisma, cart API routes (/api/cart), "
            "and useCart hook with optimistic updates. Guest cart merges on login.",
            salience=0.9,
            event_type="outcome",
            tags=["cart", "implementation"],
        ))
        artifact.episodic.append(EpisodicEntry(
            timestamp=f"{day}T15:30:00Z",
            actor="user",
            observation="Found race condition: two tabs adding items simultaneously causes duplicate entries. "
            "Need to use database-level upsert.",
            salience=0.85,
            event_type="interaction",
            tags=["cart", "bug"],
        ))
        artifact.semantic.extend([
            SemanticEntry(subject="cart", predicate="uses", object="database for authenticated users, localStorage for guests", confidence=0.9),
            SemanticEntry(subject="cart bug", predicate="was", object="race condition with concurrent adds, fixed with Prisma upsert", confidence=0.95),
        ])
        artifact.working.append(WorkingEntry(
            goals=["Implement Stripe checkout flow", "Add inventory tracking to prevent overselling"],
            scratch="Cart merge logic: on login, merge guest cart items with DB cart, "
            "preferring higher quantities. Delete guest cart after merge.",
        ))

    elif session_num == 3:
        artifact.episodic.append(EpisodicEntry(
            timestamp=f"{day}T09:30:00Z",
            actor="user",
            observation="Let's implement the Stripe checkout. Need to handle webhooks for payment confirmation.",
            salience=0.9,
            event_type="interaction",
            tags=["payments", "stripe"],
        ))
        artifact.semantic.append(SemanticEntry(
            subject="stripe webhook",
            predicate="must verify",
            object="signature using STRIPE_WEBHOOK_SECRET before processing events",
            confidence=0.95,
            tags=["security", "payments"],
        ))
        artifact.procedural.append(ProceduralEntry(
            name="verify_stripe_webhook",
            description="Verify Stripe webhook signature to prevent spoofing",
            body="const event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET);",
            language="typescript",
            usage_count=1,
        ))
        # Update working state — replace entry to recompute content hash
        if artifact.working:
            old = artifact.working[0]
            new_goals = old.goals + ["Add order confirmation emails"]
            new_scratch = old.scratch + " Stripe checkout session created with line_items from cart."
            artifact.working[0] = WorkingEntry(
                goals=new_goals,
                subgoals=old.subgoals,
                scratch=new_scratch,
                parent_ids=[old.id],
                tags=old.tags,
            )

    return artifact


def main() -> None:
    print("=" * 70)
    print("Portable Agent Memory: Multi-Session Continuity")
    print("Preventing Session Amnesia Across 3 Days of Development")
    print("=" * 70)

    tmp_dir = Path(tempfile.mkdtemp())
    pam_path = tmp_dir / "dev-memory.pam"
    artifact = None

    sessions = [
        (1, "2026-05-08", "Project setup: Next.js + Prisma + Stripe"),
        (2, "2026-05-09", "Shopping cart implementation + bug fix"),
        (3, "2026-05-10", "Stripe checkout + webhook integration"),
    ]

    for session_num, day, description in sessions:
        print(f"\n{'='*60}")
        print(f"  SESSION {session_num} — Day {day}")
        print(f"  {description}")
        print(f"{'='*60}")

        # Load previous memory if exists
        if pam_path.exists():
            artifact = FileTransport.load(pam_path)
            print(f"\n  Loaded memory from previous session:")
            print(f"    Episodic entries:  {len(artifact.episodic)}")
            print(f"    Semantic facts:    {len(artifact.semantic)}")
            print(f"    Procedures:        {len(artifact.procedural)}")
            print(f"    Active goals:      {sum(len(w.goals) for w in artifact.working)}")
        else:
            print(f"\n  Fresh start — no previous memory")

        # Simulate session
        artifact = simulate_session(session_num, day, artifact)

        # Save updated memory
        FileTransport.save(artifact, pam_path)

        print(f"\n  After session {session_num}:")
        print(f"    Total episodic:    {len(artifact.episodic)} events")
        print(f"    Total semantic:    {len(artifact.semantic)} facts")
        print(f"    Total procedural:  {len(artifact.procedural)} skills")
        print(f"    Working goals:     {sum(len(w.goals) for w in artifact.working)}")
        print(f"    Artifact size:     {pam_path.stat().st_size:,} bytes")

    # --- Final: Rehydrate with full accumulated context ---
    print(f"\n{'='*70}")
    print("FINAL: Rehydrating all 3 sessions of context for a NEW session")
    print("=" * 70)

    final = FileTransport.load(pam_path)
    engine = RehydrationEngine()
    prompt = engine.rehydrate(
        final,
        task="Continue building the e-commerce app. What's the status and what should we work on next?",
    )

    # Verify accumulated knowledge
    knowledge_checks = {
        "Next.js tech stack (Session 1)": "Next.js" in prompt,
        "Prisma ORM (Session 1)": "Prisma" in prompt,
        "Cart race condition fix (Session 2)": "race" in prompt.lower() or "upsert" in prompt.lower() or "cart" in prompt.lower(),
        "Stripe webhooks (Session 3)": "Stripe" in prompt or "webhook" in prompt,
        "Active goals carried forward": "checkout" in prompt.lower() or "inventory" in prompt.lower() or "email" in prompt.lower(),
    }

    print(f"\n  Accumulated knowledge across 3 sessions:")
    for check, passed in knowledge_checks.items():
        print(f"    {check:42s} {'PASS' if passed else 'FAIL'}")

    passed = sum(knowledge_checks.values())
    total = len(knowledge_checks)

    print(f"\n  Knowledge retained: {passed}/{total} ({passed/total*100:.0f}%)")
    print(f"  Total context:      {len(final.all_entries())} entries from 3 sessions")
    print(f"  Prompt size:        {len(prompt):,} characters")

    print(f"\n  Without Portable Agent Memory: Session 3 would know NOTHING from Sessions 1-2.")
    print(f"  With Portable Agent Memory:    All {len(final.all_entries())} entries available with cryptographic integrity.")
    print()

    # Cleanup
    pam_path.unlink()
    tmp_dir.rmdir()


if __name__ == "__main__":
    main()
