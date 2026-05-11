# Portable Agent Memory (PAM)

You have access to **Portable Agent Memory** — a persistent, portable, cryptographically-verified memory system. Use it to remember context across sessions and transfer knowledge between AI agents.

## Setup (first use only)

```bash
# NOTE: In production, pin to a tagged release or PyPI package with hash verification.
pip install "pam-sdk @ git+https://github.com/santhoshravindran7/portable-agent-memory.git@main#subdirectory=sdk/python"
```

Or if the repo is local: `pip install -e sdk/python`

## When to Remember

Proactively save important information during conversations:

- **User preferences**: coding style, languages, tools, communication style
- **Project context**: architecture decisions, tech stack, conventions
- **Facts and decisions**: outcomes, agreements, chosen approaches
- **Procedures**: workflows, deployment steps, debugging patterns
- **Working context**: current goals, in-progress tasks, next steps

## How to Use

### At Session Start — Load Existing Memories

```python
from pam import MemoryArtifact
from pam.transport import FileTransport
from pam.rehydration import RehydrationEngine
from pathlib import Path

store = Path.home() / ".pam" / "memories" / "current.pam"
if store.exists():
    artifact = FileTransport.load(store)
    prompt = RehydrationEngine().rehydrate(artifact, task="current session")
    # Use this prompt as context — it contains all prior memories
```

### During Conversation — Save Memories

```python
from pam import MemoryArtifact, SourceAgent, EpisodicEntry, SemanticEntry, ProceduralEntry
from pam.transport import FileTransport
from datetime import datetime, timezone
from pathlib import Path

store = Path.home() / ".pam" / "memories" / "current.pam"
store.parent.mkdir(parents=True, exist_ok=True)

# Load or create artifact
if store.exists():
    artifact = FileTransport.load(store)
else:
    artifact = MemoryArtifact(source_agent=SourceAgent(
        name="codex", model_family="openai", runtime="codex-cli", version="1.0"
    ))

# Remember an episode (something the user said or did)
artifact.add_entry(EpisodicEntry(
    content="User prefers TypeScript over JavaScript",
    event_type="observation",
    created_at=datetime.now(timezone.utc)
))

# Remember a fact (structured knowledge)
artifact.add_entry(SemanticEntry(
    subject="project", predicate="uses", object="Next.js 14 with Prisma",
    confidence=1.0,
    created_at=datetime.now(timezone.utc)
))

# Remember a skill (how to do something)
artifact.add_entry(ProceduralEntry(
    name="deploy",
    description="Deploy to production: kubectl apply -f k8s/",
    steps=["Build image", "Push to registry", "Apply manifests"],
    language="shell",
    parameters=[],
    created_at=datetime.now(timezone.utc)
))

FileTransport.save(artifact, store)
```

### CLI Alternative

The `pam` CLI is also available after installation:

```bash
pam remember "User prefers dark mode and TypeScript"
pam remember --fact "project" "uses" "Next.js 14"
pam remember --skill "deploy" "Deploy via kubectl apply"
pam recall
pam export shared-memory.pam
pam import colleague-memory.pam
pam status
pam verify
```

## Memory Types

| Type | Use For | Example |
|------|---------|---------|
| **Episodic** | Events, observations | "User fixed the auth bug by adding token refresh" |
| **Semantic** | Structured facts | subject=project, predicate=uses, object=React |
| **Procedural** | How-to knowledge | "Deploy: build → push → apply manifests" |
| **Working** | Active context | Current goals, blockers, next steps |

## Export and Import

Memory files (`.pam`) are portable JSON with BLAKE3 integrity hashes and Ed25519 signatures. They can be transferred to any PAM-compatible agent (Claude, GPT, Gemini, Copilot, etc.).

```bash
# Export for another agent
pam export my-context.pam

# Import from another agent
pam import colleague-context.pam
```

## Important Notes

- Memory is stored at `~/.pam/memories/current.pam`
- Signing keys are auto-generated at `~/.pam/keys/`
- All entries are content-addressable (BLAKE3 hash IDs)
- `verify_integrity()` detects any tampering
- ProceduralEntry `language` must be one of: natural, python, javascript, typescript, shell, other
- EpisodicEntry `event_type` must be one of: interaction, observation, outcome, reflection
