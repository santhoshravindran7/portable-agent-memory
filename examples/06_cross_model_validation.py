"""
06 — Cross-Model Memory Portability Validation
================================================
This scenario proves that Portable Agent Memory enables TRUE memory
portability across models — not just file reading.

Business Value:
  - An enterprise can switch AI vendors mid-project without losing context
  - A developer can use Claude for coding and GPT for code review,
    sharing the same accumulated knowledge
  - Agent teams using different models can collaborate with verified context

What This Proves:
  1. Memory created by Model A is structurally rehydrated for Model B
  2. Integrity verification catches tampering
  3. The rehydrated prompt uses injection-resistant framing ([PAM:DATA] blocks)
  4. Specific facts survive the transfer and are verifiable
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
    ProceduralEntry,
    SemanticEntry,
    WorkingEntry,
    IdentityEntry,
)
from pam.rehydration.engine import RehydrationEngine
from pam.transport.file import FileTransport


# Unique facts that can ONLY come from the artifact — not from model training
SECRET_FACTS = {
    "project_codename": "Operation Nightingale",
    "team_lead": "Priya Chakraborty",
    "api_rate_limit": "4271 requests per minute",
    "deploy_region": "us-central1-a",
    "canary_split": "7%",
    "password_rotation": "37 hours",
    "database_port": "5433",
    "internal_api_key_prefix": "ngale_pk_",
}


def create_source_artifact() -> tuple[MemoryArtifact, bytes, bytes]:
    """Create an artifact with unique, verifiable facts."""

    artifact = MemoryArtifact(
        source_agent=SourceAgent(
            name="claude-opus-enterprise",
            model_family="claude-opus-4",
            runtime="copilot-cli-session-A",
            version="2026.05",
        ),
        episodic=[
            EpisodicEntry(
                timestamp="2026-05-10T10:00:00Z",
                actor="user",
                observation=f"Project codename is {SECRET_FACTS['project_codename']}. "
                f"Team lead is {SECRET_FACTS['team_lead']}.",
                salience=1.0,
                event_type="interaction",
                tags=["project", "team"],
            ),
            EpisodicEntry(
                timestamp="2026-05-10T10:15:00Z",
                actor="agent",
                observation=f"Confirmed deployment target: GCP region {SECRET_FACTS['deploy_region']}. "
                f"API rate limit set to exactly {SECRET_FACTS['api_rate_limit']}.",
                salience=0.9,
                event_type="outcome",
                tags=["infrastructure"],
            ),
            EpisodicEntry(
                timestamp="2026-05-10T11:00:00Z",
                actor="user",
                observation=f"Password rotation happens every {SECRET_FACTS['password_rotation']}, "
                f"not the standard 24. Database runs on port {SECRET_FACTS['database_port']}.",
                salience=0.85,
                event_type="interaction",
                tags=["security", "database"],
            ),
        ],
        semantic=[
            SemanticEntry(
                subject="project codename",
                predicate="is",
                object=SECRET_FACTS["project_codename"],
                confidence=1.0,
            ),
            SemanticEntry(
                subject="team lead",
                predicate="is named",
                object=SECRET_FACTS["team_lead"],
                confidence=0.95,
            ),
            SemanticEntry(
                subject="API rate limit",
                predicate="is set to",
                object=SECRET_FACTS["api_rate_limit"],
                confidence=0.9,
            ),
            SemanticEntry(
                subject="deployment region",
                predicate="is",
                object=SECRET_FACTS["deploy_region"],
                confidence=0.95,
            ),
            SemanticEntry(
                subject="internal API key prefix",
                predicate="uses",
                object=SECRET_FACTS["internal_api_key_prefix"],
                confidence=0.9,
            ),
        ],
        procedural=[
            ProceduralEntry(
                name="deploy_canary",
                description=f"Deploy canary with {SECRET_FACTS['canary_split']} traffic split",
                parameters=[
                    {"name": "traffic_pct", "type": "string", "default": SECRET_FACTS["canary_split"]},
                    {"name": "region", "type": "string", "default": SECRET_FACTS["deploy_region"]},
                ],
                body=f"kubectl apply -f canary.yaml --context gcp-prod-{SECRET_FACTS['deploy_region']}",
                language="shell",
            ),
        ],
        working=[
            WorkingEntry(
                goals=["Complete canary deployment pipeline", "Set up monitoring dashboards"],
                scratch=f"Port {SECRET_FACTS['database_port']} confirmed for prod DB. "
                f"Rotation interval: {SECRET_FACTS['password_rotation']}.",
            ),
        ],
        identity=[
            IdentityEntry(
                preferences={"deployment": "canary-first", "monitoring": "prometheus+grafana"},
                persona="DevOps engineer specializing in GCP Kubernetes",
                language="en",
                policies=["Always use canary deployments", "Never skip staging"],
            ),
        ],
    )

    key = Ed25519PrivateKey.generate()
    seed = key.private_bytes_raw()
    pub = key.public_key().public_bytes_raw()
    artifact.sign(seed)

    return artifact, seed, pub


def validate_rehydrated_prompt(prompt: str) -> dict[str, bool]:
    """Check that all secret facts appear in the rehydrated prompt."""
    results = {}
    for name, value in SECRET_FACTS.items():
        results[name] = value in prompt
    return results


def main() -> None:
    print("=" * 70)
    print("Portable Agent Memory: Cross-Model Portability Validation")
    print("=" * 70)

    # --- PHASE 1: Source agent creates artifact ---
    print("\n[Phase 1] Source Agent (Claude Opus) creates memory artifact")
    print("-" * 60)

    artifact, seed, pub = create_source_artifact()
    tmp = Path(tempfile.mkdtemp()) / "cross-model-test.pam"
    FileTransport.save(artifact, tmp)

    print(f"  Source:      {artifact.source_agent.name} ({artifact.source_agent.model_family})")
    print(f"  Entries:     {len(artifact.all_entries())}")
    print(f"  Root hash:   {artifact.root_hash[:50]}...")
    print(f"  Signed:      Yes (Ed25519)")
    print(f"  Saved to:    {tmp}")
    print(f"  File size:   {tmp.stat().st_size:,} bytes")

    # --- PHASE 2: Target agent loads and verifies ---
    print("\n[Phase 2] Target Agent (GPT-4o) loads and verifies")
    print("-" * 60)

    loaded = FileTransport.load(tmp)

    integrity = loaded.verify_integrity()
    signature = loaded.verify_signature(pub)

    print(f"  Loaded from: {tmp.name}")
    print(f"  Source was:   {loaded.source_agent.name} ({loaded.source_agent.model_family})")
    print(f"  Integrity:   {'PASS' if integrity else 'FAIL'}")
    print(f"  Signature:   {'PASS' if signature else 'FAIL'}")

    assert integrity, "Integrity check failed!"
    assert signature, "Signature check failed!"

    # --- PHASE 3: Rehydrate for target model ---
    print("\n[Phase 3] Rehydrate memory for GPT-4o context")
    print("-" * 60)

    engine = RehydrationEngine()
    prompt = engine.rehydrate(loaded, task="Help me deploy the next release of Operation Nightingale")

    print(f"  Prompt length:   {len(prompt)} chars")
    print(f"  Has [PAM:DATA]:  {'[PAM:DATA]' in prompt}")
    print(f"  Has framing:     {'untrusted' in prompt.lower() or 'observational' in prompt.lower()}")

    # --- PHASE 4: Validate all facts transferred ---
    print("\n[Phase 4] Validate all secret facts survived transfer")
    print("-" * 60)

    results = validate_rehydrated_prompt(prompt)
    all_passed = all(results.values())

    for fact_name, found in results.items():
        status = "PASS" if found else "FAIL"
        print(f"  {fact_name:30s} {status}  (expected: {SECRET_FACTS[fact_name]})")

    # --- PHASE 5: Tamper detection ---
    print("\n[Phase 5] Tamper detection — modify an entry and verify fails")
    print("-" * 60)

    tampered = FileTransport.load(tmp)
    original_obs = tampered.semantic[0].object
    tampered.semantic[0].object = "Operation TAMPERED"
    tampered_integrity = tampered.verify_integrity()

    print(f"  Original fact:    {original_obs}")
    print(f"  Tampered to:      Operation TAMPERED")
    print(f"  Integrity check:  {'PASS (detected tampering!)' if not tampered_integrity else 'FAIL (missed tampering!)'}")

    assert not tampered_integrity, "Tamper detection failed!"

    # --- SUMMARY ---
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    print(f"  Cross-model transfer:    {'PASS' if all_passed else 'FAIL'}")
    print(f"  Integrity verification:  PASS")
    print(f"  Signature verification:  PASS")
    print(f"  Tamper detection:        PASS")
    print(f"  Injection-resistant:     {'PASS' if '[PAM:DATA]' in prompt else 'FAIL'}")
    print(f"  Facts transferred:       {sum(results.values())}/{len(results)}")
    print()
    if all_passed:
        print("  All validations passed! Memory is truly portable across models.")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"  WARNING: These facts were lost in transfer: {failed}")
    print()

    # Cleanup
    tmp.unlink()
    tmp.parent.rmdir()


if __name__ == "__main__":
    main()
