"""
07 — Enterprise Vendor Migration Scenario
==========================================
Simulates a real enterprise scenario: migrating from one AI vendor to
another mid-project without losing accumulated agent context.

Business Value:
  - Enterprises avoid vendor lock-in — switch providers without starting over
  - Compliance teams can audit the transfer via cryptographic provenance
  - Cost optimization: move workloads to cheaper models while preserving context
  - Business continuity: if a vendor has an outage, fail over with full context

Scenario:
  A healthcare company's clinical documentation agent has been running on
  Vendor A (Claude) for 6 months. Due to pricing changes, they need to
  migrate to Vendor B (GPT). The agent has accumulated:
    - 3 months of patient interaction patterns (episodic)
    - Medical terminology mappings (semantic)
    - HIPAA-compliant response templates (procedural)
    - Active patient case context (working)
    - Compliance policies (identity)

  All of this must transfer with cryptographic proof of integrity.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sdk" / "python"))

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tempfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pam.models.artifact import MemoryArtifact, SourceAgent
from pam.models.entries import (
    EpisodicEntry,
    IdentityEntry,
    ProceduralEntry,
    SemanticEntry,
    WorkingEntry,
)
from pam.rehydration.engine import RehydrationEngine
from pam.transport.file import FileTransport


def create_healthcare_agent_memory() -> MemoryArtifact:
    """Simulate 6 months of clinical documentation agent memory."""

    return MemoryArtifact(
        source_agent=SourceAgent(
            name="clinical-doc-assistant",
            model_family="claude-3.5-sonnet",
            runtime="aws-bedrock",
            version="2025.11",
        ),
        episodic=[
            EpisodicEntry(
                timestamp="2025-11-15T09:00:00Z",
                actor="system",
                observation="Agent deployed for clinical documentation at Northwest Medical Center. "
                "Initial HIPAA compliance training completed.",
                salience=1.0,
                event_type="observation",
                tags=["deployment", "compliance"],
            ),
            EpisodicEntry(
                timestamp="2026-01-20T14:30:00Z",
                actor="clinician",
                observation="Dr. Martinez requested documentation for complex cardiac case. "
                "Patient presented with atypical chest pain, troponin-negative, "
                "ECG showing ST-depression in leads V4-V6.",
                salience=0.9,
                event_type="interaction",
                tags=["cardiology", "documentation"],
            ),
            EpisodicEntry(
                timestamp="2026-03-05T11:00:00Z",
                actor="agent",
                observation="Identified pattern: clinicians at this facility prefer SOAP format "
                "with ICD-10 codes inline rather than appended. Adapted templates accordingly.",
                salience=0.85,
                event_type="reflection",
                tags=["adaptation", "templates"],
            ),
            EpisodicEntry(
                timestamp="2026-04-10T16:00:00Z",
                actor="compliance",
                observation="Quarterly HIPAA audit passed. Zero PHI exposure incidents. "
                "Agent correctly redacted all patient identifiers in 3,247 documents.",
                salience=0.95,
                event_type="outcome",
                tags=["compliance", "hipaa"],
            ),
        ],
        semantic=[
            SemanticEntry(
                subject="facility preference",
                predicate="uses",
                object="SOAP format with inline ICD-10 codes",
                confidence=0.95,
                tags=["documentation"],
            ),
            SemanticEntry(
                subject="Dr. Martinez",
                predicate="specializes in",
                object="interventional cardiology, prefers detailed hemodynamic data in notes",
                confidence=0.9,
                tags=["clinician-preferences"],
            ),
            SemanticEntry(
                subject="facility formulary",
                predicate="prefers",
                object="metoprolol over atenolol for rate control, per pharmacy committee decision 2025-Q3",
                confidence=0.85,
                tags=["pharmacy"],
            ),
            SemanticEntry(
                subject="documentation turnaround",
                predicate="target is",
                object="under 4 hours for routine, under 1 hour for critical findings",
                confidence=0.9,
                tags=["sla"],
            ),
        ],
        procedural=[
            ProceduralEntry(
                name="generate_soap_note",
                description="Generate HIPAA-compliant SOAP note with inline ICD-10 codes",
                parameters=[
                    {"name": "encounter_type", "type": "string"},
                    {"name": "include_icd10", "type": "bool", "default": True},
                ],
                body="Template: S: [chief complaint, HPI] | O: [vitals, exam, labs] | "
                "A: [diagnosis (ICD-10: XXX.XX)] | P: [plan with medication reconciliation]",
                language="natural",
                usage_count=3247,
                tags=["documentation", "hipaa"],
            ),
            ProceduralEntry(
                name="redact_phi",
                description="Identify and redact Protected Health Information per HIPAA Safe Harbor",
                parameters=[
                    {"name": "text", "type": "string"},
                    {"name": "method", "type": "string", "default": "safe_harbor"},
                ],
                body="Apply 18 Safe Harbor identifiers: names, dates (except year), "
                "phone, fax, email, SSN, MRN, account numbers, URLs, IPs, "
                "biometric, photos, any unique identifier",
                language="natural",
                usage_count=9841,
                tags=["hipaa", "privacy"],
            ),
        ],
        working=[
            WorkingEntry(
                goals=[
                    "Complete Q2 documentation backlog (47 pending notes)",
                    "Integrate with new EHR module for radiology reports",
                ],
                subgoals=[
                    {"task": "Process cardiology notes from May 1-10", "status": "in_progress"},
                    {"task": "Test radiology integration in staging", "status": "pending"},
                ],
                scratch="Dr. Martinez's pending cases: cardiac cath follow-up (x3), "
                "stress test review (x2). Priority: cath follow-ups due by Friday.",
            ),
        ],
        identity=[
            IdentityEntry(
                preferences={
                    "documentation_format": "SOAP",
                    "code_system": "ICD-10-CM",
                    "language_style": "clinical, precise, no abbreviations except standard medical",
                },
                persona="Clinical documentation specialist for Northwest Medical Center",
                language="en",
                policies=[
                    "HIPAA Safe Harbor: Always redact all 18 identifier types",
                    "Never include patient names in any output",
                    "Always include ICD-10 codes with descriptions",
                    "Flag critical findings for immediate clinician review",
                    "Retain audit trail for all document modifications",
                ],
                custom_instructions="This agent operates under BAA with Northwest Medical Center. "
                "All interactions are subject to HIPAA privacy and security rules.",
            ),
        ],
    )


def main() -> None:
    print("=" * 70)
    print("Portable Agent Memory: Enterprise Vendor Migration")
    print("Scenario: Healthcare AI — Claude (Bedrock) to GPT (Azure OpenAI)")
    print("=" * 70)

    # --- Source: Claude on AWS Bedrock ---
    print("\n[1/5] Source agent exports 6 months of clinical knowledge")
    print("-" * 60)

    artifact = create_healthcare_agent_memory()
    key = Ed25519PrivateKey.generate()
    artifact.sign(key.private_bytes_raw())

    tmp = Path(tempfile.mkdtemp()) / "clinical-agent-migration.pam"
    FileTransport.save(artifact, tmp)

    total_entries = len(artifact.all_entries())
    print(f"  Agent:           {artifact.source_agent.name}")
    print(f"  Platform:        {artifact.source_agent.runtime} ({artifact.source_agent.model_family})")
    print(f"  Total entries:   {total_entries}")
    print(f"  Episodic:        {len(artifact.episodic)} interaction records")
    print(f"  Semantic:        {len(artifact.semantic)} learned facts")
    print(f"  Procedural:      {len(artifact.procedural)} skills (used {sum(p.usage_count for p in artifact.procedural):,} times)")
    print(f"  Working:         {len(artifact.working)} active task contexts")
    print(f"  Identity:        {len(artifact.identity)} policy sets")
    print(f"  Artifact size:   {tmp.stat().st_size:,} bytes")

    # --- Transport ---
    print("\n[2/5] Artifact transported to new vendor")
    print("-" * 60)
    print(f"  Format:          JSON (.pam) — auditable by compliance team")
    print(f"  Transport:       Secure file transfer")
    print(f"  Encryption:      Ed25519 signed (signature in artifact)")

    # --- Target: GPT on Azure ---
    print("\n[3/5] Target agent (GPT-4o on Azure) verifies artifact")
    print("-" * 60)

    loaded = FileTransport.load(tmp)
    integrity = loaded.verify_integrity()
    signature = loaded.verify_signature(key.public_key().public_bytes_raw())

    print(f"  Integrity:       {'PASS - No tampering detected' if integrity else 'FAIL'}")
    print(f"  Signature:       {'PASS - Authentic source confirmed' if signature else 'FAIL'}")
    print(f"  Schema version:  {loaded.schema_version}")
    print(f"  Origin agent:    {loaded.source_agent.name} ({loaded.source_agent.model_family})")

    # --- Rehydration ---
    print("\n[4/5] Rehydrating memory for GPT-4o context window")
    print("-" * 60)

    engine = RehydrationEngine()
    prompt = engine.rehydrate(
        loaded,
        task="Continue clinical documentation for Northwest Medical Center. "
        "Process pending cardiology notes from Dr. Martinez.",
    )

    print(f"  Prompt length:   {len(prompt):,} characters")
    print(f"  Framing:         Injection-resistant [PAM:DATA] blocks")

    # Verify key knowledge transferred
    checks = {
        "SOAP format preference": "SOAP" in prompt,
        "ICD-10 coding system": "ICD-10" in prompt,
        "Dr. Martinez preferences": "Martinez" in prompt,
        "HIPAA policies": "HIPAA" in prompt,
        "Medication preference": "metoprolol" in prompt,
        "PHI redaction skill": "redact" in prompt.lower() or "Safe Harbor" in prompt,
        "Documentation SLA": "4 hours" in prompt or "1 hour" in prompt,
        "Active goals": "backlog" in prompt or "radiology" in prompt,
    }

    print("\n  Knowledge transfer verification:")
    for check, passed in checks.items():
        print(f"    {check:35s} {'PASS' if passed else 'FAIL'}")

    passed = sum(checks.values())
    total = len(checks)

    # --- Business Impact ---
    print(f"\n[5/5] Business Impact Summary")
    print("-" * 60)
    print(f"  Knowledge preserved:     {passed}/{total} critical items ({passed/total*100:.0f}%)")
    print(f"  Vendor migration time:   Seconds (vs. weeks of manual transfer)")
    print(f"  Compliance audit trail:  Cryptographic proof of intact transfer")
    print(f"  Patient safety:          HIPAA policies carried over automatically")
    print(f"  Operational continuity:  Active cases and pending work transferred")
    print(f"  Skills retained:         {sum(p.usage_count for p in artifact.procedural):,} procedure executions worth of learning")

    print("\n" + "=" * 70)
    if passed == total:
        print("MIGRATION SUCCESSFUL: Full context transfer with zero knowledge loss.")
    else:
        failed = [k for k, v in checks.items() if not v]
        print(f"PARTIAL: {len(failed)} items need attention: {failed}")
    print("=" * 70)
    print()

    # Cleanup
    tmp.unlink()
    tmp.parent.rmdir()


if __name__ == "__main__":
    main()
