"""
03 — Selective Memory Disclosure with Capability Tokens
========================================================
This example demonstrates the Portable Agent Memory security model:
  1. A rich artifact with mixed-sensitivity content is created
  2. Capability tokens scope access to specific tags or components
  3. Each token holder sees only what they're authorized to see

Scenario: A customer support AI has memory about a client including
billing data, technical issues, and personal preferences. Different
downstream agents receive scoped views of this memory.
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
    SemanticEntry,
)


def main() -> None:
    print("=" * 60)
    print("Portable Agent Memory Example 03: Selective Memory Disclosure")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Create a rich artifact with mixed-sensitivity content
    # ------------------------------------------------------------------
    print("\n📋 Creating artifact with mixed-sensitivity content...")

    billing_entries = [
        SemanticEntry(
            subject="customer/acme-corp",
            predicate="has_plan",
            object="Enterprise tier, $2,400/month, 50 seats",
            confidence=0.95,
            tags=["billing", "customer-data"],
        ),
        SemanticEntry(
            subject="customer/acme-corp",
            predicate="payment_status",
            object="Invoice #1042 overdue by 15 days, $2,400 outstanding",
            confidence=0.9,
            tags=["billing", "sensitive"],
        ),
        EpisodicEntry(
            timestamp="2024-11-05T10:00:00Z",
            actor="customer",
            observation="Requested to downgrade from Enterprise to Team plan due to budget cuts.",
            salience=0.9,
            event_type="interaction",
            tags=["billing", "account-change"],
        ),
    ]

    technical_entries = [
        SemanticEntry(
            subject="customer/acme-corp",
            predicate="uses",
            object="API v2 with Python SDK, averaging 12K requests/day",
            confidence=0.9,
            tags=["technical", "usage"],
        ),
        EpisodicEntry(
            timestamp="2024-11-07T14:00:00Z",
            actor="customer",
            observation="Reported intermittent 503 errors on /api/v2/reports endpoint during peak hours (2-4 PM EST).",
            salience=0.95,
            event_type="interaction",
            tags=["technical", "bug-report"],
        ),
        EpisodicEntry(
            timestamp="2024-11-07T16:00:00Z",
            actor="assistant",
            observation="Identified rate limiting as root cause. Increased per-customer limit from 100 to 200 req/min. Issue resolved.",
            salience=0.85,
            event_type="outcome",
            tags=["technical", "resolution"],
        ),
    ]

    preference_entries = [
        IdentityEntry(
            preferences={
                "communication": "Prefers email over chat",
                "timezone": "US/Eastern",
                "contact": "Sarah Chen, VP Engineering",
            },
            persona="Enterprise customer",
            language="en",
            tags=["preferences", "customer-data"],
        ),
    ]

    all_entries = billing_entries + technical_entries + preference_entries

    artifact = MemoryArtifact(
        source_agent=SourceAgent(
            name="support-agent", model_family="claude-3.5-sonnet", runtime="python"
        ),
        episodic=[e for e in all_entries if isinstance(e, EpisodicEntry)],
        semantic=[e for e in all_entries if isinstance(e, SemanticEntry)],
        identity=[e for e in all_entries if isinstance(e, IdentityEntry)],
    )

    print(f"  Total entries: {len(artifact.all_entries())}")
    print(f"  Billing:       {len(billing_entries)} entries")
    print(f"  Technical:     {len(technical_entries)} entries")
    print(f"  Preferences:   {len(preference_entries)} entries")

    # ------------------------------------------------------------------
    # Step 2: Generate keys and create capability tokens
    # ------------------------------------------------------------------
    print("\n🔑 Creating scoped capability tokens...")

    private_key = Ed25519PrivateKey.generate()
    seed = private_key.private_bytes_raw()
    pub = private_key.public_key().public_bytes_raw()

    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    # Token 1: Billing team — can only see "billing" tagged entries
    billing_token = CapabilityToken(
        scope=CapabilityScope(type="tag", value=["billing"]),
        permissions=["read"],
        issuer="support-agent",
        audience="billing-team-agent",
        expires_at=expires,
    )
    billing_token.sign(seed)

    # Token 2: Engineering team — can only see "semantic" component entries
    engineering_token = CapabilityToken(
        scope=CapabilityScope(type="component", value=["semantic"]),
        permissions=["read"],
        issuer="support-agent",
        audience="engineering-agent",
        expires_at=expires,
    )
    engineering_token.sign(seed)

    # Token 3: Technical support — can only see "technical" tagged entries
    tech_support_token = CapabilityToken(
        scope=CapabilityScope(type="tag", value=["technical"]),
        permissions=["read"],
        issuer="support-agent",
        audience="tech-support-agent",
        expires_at=expires,
    )
    tech_support_token.sign(seed)

    # Token 4: Full access (wildcard)
    admin_token = CapabilityToken(
        scope=CapabilityScope(type="wildcard", value="*"),
        permissions=["read"],
        issuer="support-agent",
        audience="admin-agent",
        expires_at=expires,
    )
    admin_token.sign(seed)

    print(f"  ✅ Billing token:        scope=tag:billing")
    print(f"  ✅ Engineering token:     scope=component:semantic")
    print(f"  ✅ Tech support token:    scope=tag:technical")
    print(f"  ✅ Admin token:           scope=wildcard:*")

    # ------------------------------------------------------------------
    # Step 3: Demonstrate filtering
    # ------------------------------------------------------------------
    print("\n🔍 Filtering entries by capability token...")
    print("-" * 60)

    validator = CapabilityValidator()
    entries = artifact.all_entries()

    def show_filtered(name: str, token: CapabilityToken) -> None:
        sig_valid = validator.validate_token(token, pub)
        filtered = validator.filter_entries(entries, token)
        print(f"\n  👤 {name} (signature valid: {'✅' if sig_valid else '❌'})")
        print(f"     Scope: {token.scope.type} = {token.scope.value}")
        print(f"     Can see: {len(filtered)} / {len(entries)} entries")
        if filtered:
            for entry in filtered:
                if isinstance(entry, SemanticEntry):
                    print(f"       • [semantic] {entry.subject} {entry.predicate} {entry.object[:50]}")
                elif isinstance(entry, EpisodicEntry):
                    print(f"       • [episodic] {entry.observation[:60]}...")
                elif isinstance(entry, IdentityEntry):
                    print(f"       • [identity] Persona: {entry.persona}")
        hidden_count = len(entries) - len(filtered)
        if hidden_count:
            print(f"     🚫 Hidden: {hidden_count} entries not accessible")

    show_filtered("Billing Team Agent", billing_token)
    show_filtered("Engineering Agent", engineering_token)
    show_filtered("Tech Support Agent", tech_support_token)
    show_filtered("Admin Agent", admin_token)

    # ------------------------------------------------------------------
    # Step 4: Demonstrate security — wrong key, expired token
    # ------------------------------------------------------------------
    print("\n\n🛡️  Security demonstrations...")
    print("-" * 60)

    # Wrong key
    other_key = Ed25519PrivateKey.generate()
    other_pub = other_key.public_key().public_bytes_raw()
    wrong_key_valid = validator.validate_token(billing_token, other_pub)
    print(f"\n  Wrong public key validation: {'✅ PASS (bad!)' if wrong_key_valid else '❌ REJECTED (correct!)'}")

    # Expired token
    expired_token = CapabilityToken(
        scope=CapabilityScope(type="wildcard", value="*"),
        permissions=["read"],
        issuer="support-agent",
        expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    )
    expired_token.sign(seed)
    expired_valid = validator.validate_token(expired_token, pub)
    print(f"  Expired token validation:   {'✅ PASS (bad!)' if expired_valid else '❌ REJECTED (correct!)'}")

    # No read permission
    write_only_token = CapabilityToken(
        scope=CapabilityScope(type="wildcard", value="*"),
        permissions=["write"],
        issuer="support-agent",
        expires_at=expires,
    )
    write_filtered = validator.filter_entries(entries, write_only_token)
    print(f"  Write-only token filtering: {len(write_filtered)} entries visible (correct: 0)")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("Capability Scoping Summary")
    print("=" * 60)
    print("  The same artifact contains 7 entries, but each agent")
    print("  sees only what its capability token allows:")
    print(f"    Billing team:     {len(validator.filter_entries(entries, billing_token))} entries (billing-tagged)")
    print(f"    Engineering:      {len(validator.filter_entries(entries, engineering_token))} entries (semantic only)")
    print(f"    Tech support:     {len(validator.filter_entries(entries, tech_support_token))} entries (technical-tagged)")
    print(f"    Admin:            {len(validator.filter_entries(entries, admin_token))} entries (full access)")
    print(f"    Wrong key:        REJECTED")
    print(f"    Expired token:    REJECTED")
    print()


if __name__ == "__main__":
    main()
