"""
09 — Measuring Transfer Quality (TCS & RHF)
============================================
The PAM spec (§10) defines two metrics for *quantifying* how well memory
survives a transfer between agents:

  - Transfer Continuity Score (TCS): can the target agent still complete the
    source agent's tasks after re-hydration?  (task-success continuity)
  - Re-Hydration Fidelity (RHF): are the target agent's answers semantically
    close to the source agent's?  (response similarity)

This example builds a memory artifact, then evaluates two target agents against
the source:

  1. A "good" target that re-hydrated the memory and answers correctly.
  2. A "lossy" target that lost the memory and can't answer.

It prints a standardized evaluation report for each (spec §10.3).

No LLM calls are made — the "agents" here are simple Python functions so the
example is deterministic and runs anywhere. In a real evaluation you would swap
these for live model calls and (optionally) pass an `embed_fn` to RHF.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sdk" / "python"))

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pam.metrics import (
    AgentDescriptor,
    ProbeTask,
    RehydrationConfigSummary,
    evaluate_transfer,
)
from pam.models.artifact import MemoryArtifact, SourceAgent
from pam.models.entries import SemanticEntry

# Ground-truth facts the source agent "knows" from its memory.
FACTS = {
    "database port": "5433",
    "deploy region": "us-central1-a",
    "canary split": "7%",
}


def build_artifact() -> MemoryArtifact:
    artifact = MemoryArtifact(
        source_agent=SourceAgent(
            name="research-bot-alpha", model_family="gpt-4", runtime="python"
        ),
        semantic=[
            SemanticEntry(
                subject="database",
                predicate="port",
                object=FACTS["database port"],
                confidence=1.0,
            ),
            SemanticEntry(
                subject="deploy",
                predicate="region",
                object=FACTS["deploy region"],
                confidence=1.0,
            ),
            SemanticEntry(
                subject="canary",
                predicate="split",
                object=FACTS["canary split"],
                confidence=1.0,
            ),
        ],
    )
    artifact.sign(Ed25519PrivateKey.generate().private_bytes_raw())
    return artifact


# --- Probe sets (spec §10) ---
TASKS = [
    ProbeTask(
        id="t1",
        prompt="What port does the database use?",
        category="recall",
        expect_substring="5433",
    ),
    ProbeTask(
        id="t2",
        prompt="Which region do we deploy to?",
        category="recall",
        expect_substring="us-central1-a",
    ),
    ProbeTask(
        id="t3",
        prompt="What is the canary traffic split?",
        category="recall",
        expect_substring="7%",
    ),
]
QUESTIONS = [
    "Summarize the production database configuration.",
    "Describe the deployment strategy.",
]


def source_agent(prompt: str) -> str:
    """Source agent — answers from full memory."""
    return (
        f"The database runs on port {FACTS['database port']}, we deploy to "
        f"{FACTS['deploy region']}, using a {FACTS['canary split']} canary split."
    )


def good_target(prompt: str) -> str:
    """Target that successfully re-hydrated the memory."""
    return (
        f"Deployments go to {FACTS['deploy region']} with a "
        f"{FACTS['canary split']} canary split; the database listens on port "
        f"{FACTS['database port']}."
    )


def lossy_target(prompt: str) -> str:
    """Target that received no memory — pure session amnesia."""
    return "I don't have any information about that configuration."


def main() -> None:
    print("=" * 70)
    print("Portable Agent Memory: Transfer Quality Metrics (TCS & RHF)")
    print("=" * 70)

    artifact = build_artifact()
    config = RehydrationConfigSummary(
        token_budget=4096, relevance_threshold=0.3, format_style="xml"
    )

    for label, target_fn, target_name in [
        ("Re-hydrated target", good_target, "research-bot-beta"),
        ("Memory-less target", lossy_target, "research-bot-gamma"),
    ]:
        report = evaluate_transfer(
            source_agent_fn=source_agent,
            target_agent_fn=target_fn,
            tasks=TASKS,
            questions=QUESTIONS,
            artifact=artifact,
            target_descriptor=AgentDescriptor(
                name=target_name, model_family="claude-3"
            ),
            rehydration_config=config,
            evaluation_id=f"eval:{target_name}",
            timestamp="2026-01-15T12:00:00Z",
        )

        print(f"\n[{label}]")
        print("-" * 60)
        print(
            f"  Source: {report.source_agent.name} ({report.source_agent.model_family})"
        )
        print(
            f"  Target: {report.target_agent.name} ({report.target_agent.model_family})"
        )
        print(f"  TCS: {report.metrics.tcs:.2f}   RHF: {report.metrics.rhf:.2f}")
        for line in report.summary().split("\n"):
            print(f"    {line}")

    print("\n" + "=" * 70)
    print("Takeaway: a successful transfer keeps TCS and RHF high; a lossy one")
    print("collapses both — exactly the 'session amnesia' PAM is built to defeat.")
    print("=" * 70)


if __name__ == "__main__":
    main()
