# Portable Agent Memory — Copilot CLI Skill

## Description

Use this skill to persist, export, and import AI agent memory across sessions and across different AI models. Enables memory portability between Claude, GPT, Gemini, and any other LLM. Memory is stored as signed, content-addressable JSON artifacts using the Portable Agent Memory protocol.

## When to Use

- User says "remember this", "save memory", "export memory", "what do you remember"
- User wants to transfer context to another AI
- User wants persistent memory across sessions
- User says "import memory", "load memory", "continue from where X left off"
- You learn something important about the user's preferences, project, or workflow
- User mentions a `.pam` file

## Prerequisites

On first use, auto-install the SDK directly from GitHub (no PyPI needed):

```bash
# NOTE: In production, pin to a tagged release or PyPI package with hash verification.
pip install "pam-sdk @ git+https://github.com/santhoshravindran7/portable-agent-memory.git@main#subdirectory=sdk/python"
```

If already installed locally, skip this step. Check with: `python -c "import pam; print(pam.__version__)"`

Dependencies (`cryptography`, `blake3`, `pydantic`, `cbor2`) are installed automatically.

## How It Works

Portable Agent Memory stores memory as **entries** inside a **MemoryArtifact**:

- **Episodic** — events, interactions, observations (what happened)
- **Semantic** — knowledge triples: subject-predicate-object (facts learned)
- **Procedural** — reusable skills and procedures (how to do things)
- **Identity** — user preferences, persona, policies (who the user is)
- **Working** — current goals and scratch-pad (what's in progress)

Each entry is content-addressable (BLAKE3 hash). Artifacts are signed with Ed25519 keys for integrity verification. Files are human-readable JSON with `.pam` extension.

## Commands / Triggers

### Remember / Save

When the user says "remember this" or you learn something important, run:

```python
import os
from pathlib import Path
from datetime import datetime, timezone
from pam import MemoryArtifact, EpisodicEntry, SemanticEntry, ProceduralEntry, IdentityEntry
from pam.models import SourceAgent
from pam.transport.file import FileTransport
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# --- Setup paths ---
PAM_DIR = Path.home() / ".pam"
KEYS_DIR = PAM_DIR / "keys"
MEMORIES_DIR = PAM_DIR / "memories"
MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
KEYS_DIR.mkdir(parents=True, exist_ok=True)

# --- Key management (auto-generate on first use) ---
def get_or_create_key() -> Ed25519PrivateKey:
    key_path = KEYS_DIR / "agent.key"
    if key_path.exists():
        return Ed25519PrivateKey.from_private_bytes(key_path.read_bytes())
    key = Ed25519PrivateKey.generate()
    key_path.write_bytes(key.private_bytes_raw())
    # Save public key for verification
    pub_path = KEYS_DIR / "agent.pub"
    pub_path.write_bytes(key.public_key().public_bytes_raw())
    return key

# --- Load or create artifact ---
def load_or_create_artifact() -> MemoryArtifact:
    artifact_path = MEMORIES_DIR / "current.pam"
    if artifact_path.exists():
        return FileTransport.load(str(artifact_path))
    return MemoryArtifact(
        source_agent=SourceAgent(
            name="copilot-cli",
            model_family="claude",
            runtime="github-copilot-cli",
            version="1.0"
        )
    )

# --- Save artifact (sign + write) ---
def save_artifact(artifact: MemoryArtifact) -> None:
    key = get_or_create_key()
    artifact.sign(key.private_bytes_raw())
    FileTransport.save(artifact, str(MEMORIES_DIR / "current.pam"))

# --- Remember an episodic event ---
def remember_episode(observation: str, actor: str = "user", salience: float = 0.7) -> str:
    artifact = load_or_create_artifact()
    entry = EpisodicEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=actor,
        observation=observation,
        salience=salience,
        event_type="observation"
    )
    artifact.episodic.append(entry)
    save_artifact(artifact)
    return f"Remembered: {observation}"

# --- Remember a fact (semantic triple) ---
def remember_fact(subject: str, predicate: str, obj: str, confidence: float = 0.9) -> str:
    artifact = load_or_create_artifact()
    entry = SemanticEntry(
        subject=subject,
        predicate=predicate,
        object=obj,
        confidence=confidence
    )
    artifact.semantic.append(entry)
    save_artifact(artifact)
    return f"Learned: {subject} {predicate} {obj}"

# --- Remember a skill/procedure ---
def remember_skill(name: str, description: str, body: str = "", language: str = "natural") -> str:
    artifact = load_or_create_artifact()
    entry = ProceduralEntry(
        name=name,
        description=description,
        body=body,
        language=language
    )
    artifact.procedural.append(entry)
    save_artifact(artifact)
    return f"Skill saved: {name}"

# --- Remember user preferences/identity ---
def remember_identity(preferences: dict = None, persona: str = "", policies: list = None, custom_instructions: str = "") -> str:
    artifact = load_or_create_artifact()
    entry = IdentityEntry(
        preferences=preferences or {},
        persona=persona,
        policies=policies or [],
        custom_instructions=custom_instructions
    )
    artifact.identity.append(entry)
    save_artifact(artifact)
    return f"Identity updated: {persona or 'preferences saved'}"
```

**Usage examples:**

```python
# User says "Remember that I prefer dark mode"
remember_identity(preferences={"theme": "dark_mode"})

# User says "Remember that this project uses FastAPI"
remember_fact("project", "uses", "FastAPI")

# You observe the user's debugging workflow
remember_episode("User debugs by running tests first, then checking logs", actor="agent", salience=0.8)

# You discover a useful procedure
remember_skill("run_tests", "Run project test suite", "pytest -xvs tests/", language="shell")
```

### Recall / What Do You Remember

When the user asks what you remember:

```python
from pathlib import Path
from pam.transport.file import FileTransport

def recall_memory() -> str:
    artifact_path = Path.home() / ".pam" / "memories" / "current.pam"
    if not artifact_path.exists():
        return "No memories stored yet. Say 'remember this' to start building memory."

    artifact = FileTransport.load(str(artifact_path))
    lines = []

    if artifact.episodic:
        lines.append(f"## Episodes ({len(artifact.episodic)})")
        for e in artifact.episodic[-10:]:  # show last 10
            lines.append(f"- [{e.timestamp[:10]}] {e.observation}")

    if artifact.semantic:
        lines.append(f"\n## Facts ({len(artifact.semantic)})")
        for s in artifact.semantic:
            lines.append(f"- {s.subject} {s.predicate} {s.object} (confidence: {s.confidence})")

    if artifact.procedural:
        lines.append(f"\n## Skills ({len(artifact.procedural)})")
        for p in artifact.procedural:
            lines.append(f"- **{p.name}**: {p.description}")

    if artifact.identity:
        lines.append(f"\n## Identity ({len(artifact.identity)})")
        for i in artifact.identity:
            if i.persona:
                lines.append(f"- Persona: {i.persona}")
            if i.preferences:
                lines.append(f"- Preferences: {i.preferences}")
            if i.policies:
                lines.append(f"- Policies: {i.policies}")

    if not lines:
        return "Memory artifact exists but is empty."

    return "\n".join(lines)

print(recall_memory())
```

### Export Memory

When the user wants to export memory for another agent:

```python
import shutil
from pathlib import Path
from pam.transport.file import FileTransport
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def export_memory(output_path: str = "exported_memory.pam") -> str:
    """Export current memory as a signed, portable Portable Agent Memory artifact."""
    PAM_DIR = Path.home() / ".pam"
    source = PAM_DIR / "memories" / "current.pam"

    if not source.exists():
        return "No memory to export. Nothing stored yet."

    artifact = FileTransport.load(str(source))

    # Ensure it's signed with current key
    key_path = PAM_DIR / "keys" / "agent.key"
    if key_path.exists():
        key = Ed25519PrivateKey.from_private_bytes(key_path.read_bytes())
        artifact.sign(key.private_bytes_raw())

    # Save to the requested path
    FileTransport.save(artifact, output_path)

    entry_count = len(artifact.all_entries())
    return f"Exported {entry_count} memory entries to {output_path}\nThis file can be imported by any Portable Agent Memory-compatible agent."

print(export_memory("./my_memory.pam"))
```

### Import Memory

When the user provides a `.pam` file or says "import memory":

```python
from pathlib import Path
from pam import MemoryArtifact, RehydrationEngine
from pam.transport.file import FileTransport

def import_memory(path: str, task: str = "") -> str:
    """Import and re-hydrate memory from another agent."""
    p = Path(path)
    if not p.exists():
        return f"File not found: {path}"

    # Load the artifact
    artifact = FileTransport.load(str(p))

    # Verify integrity
    if artifact.root_hash:
        if not artifact.verify_integrity():
            return "WARNING: Artifact integrity check failed. Content may have been modified."

    # Re-hydrate (rank entries by relevance to current task)
    engine = RehydrationEngine()
    context = engine.rehydrate(artifact, task=task)

    # Optionally merge into local memory
    local_path = Path.home() / ".pam" / "memories" / "current.pam"
    if local_path.exists():
        local = FileTransport.load(str(local_path))
    else:
        from pam.models import SourceAgent
        local = MemoryArtifact(
            source_agent=SourceAgent(
                name="copilot-cli",
                model_family="claude",
                runtime="github-copilot-cli",
                version="1.0"
            )
        )

    # Merge entries (avoid duplicates by ID)
    existing_ids = {e.id for e in local.all_entries()}
    for entry in artifact.episodic:
        if entry.id not in existing_ids:
            local.episodic.append(entry)
    for entry in artifact.semantic:
        if entry.id not in existing_ids:
            local.semantic.append(entry)
    for entry in artifact.procedural:
        if entry.id not in existing_ids:
            local.procedural.append(entry)
    for entry in artifact.identity:
        if entry.id not in existing_ids:
            local.identity.append(entry)

    # Save merged artifact
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key_path = Path.home() / ".pam" / "keys" / "agent.key"
    if key_path.exists():
        key = Ed25519PrivateKey.from_private_bytes(key_path.read_bytes())
        local.sign(key.private_bytes_raw())
    FileTransport.save(local, str(local_path))

    imported_count = len(artifact.all_entries())
    return f"Imported {imported_count} entries from {path}\n\nRe-hydrated context:\n{context}"

# Usage:
# print(import_memory("./colleague_memory.pam", task="Continue building the auth module"))
```

### Memory Status

Show what's in the current memory store:

```python
from pathlib import Path
from pam.transport.file import FileTransport

def memory_status() -> str:
    """Show memory store status."""
    PAM_DIR = Path.home() / ".pam"
    memories_dir = PAM_DIR / "memories"
    keys_dir = PAM_DIR / "keys"

    lines = ["## Portable Agent Memory Status\n"]

    # Key status
    if (keys_dir / "agent.key").exists():
        lines.append("🔑 Signing key: configured")
    else:
        lines.append("🔑 Signing key: not yet created (will auto-generate on first save)")

    # Memory files
    pam_files = list(memories_dir.glob("*.pam")) if memories_dir.exists() else []
    lines.append(f"📁 Memory files: {len(pam_files)}")

    # Current artifact details
    current = memories_dir / "current.pam"
    if current.exists():
        artifact = FileTransport.load(str(current))
        lines.append(f"\n### Current Artifact")
        lines.append(f"- Source: {artifact.source_agent.name} ({artifact.source_agent.model_family})")
        lines.append(f"- Created: {artifact.created_at}")
        lines.append(f"- Episodic entries: {len(artifact.episodic)}")
        lines.append(f"- Semantic entries: {len(artifact.semantic)}")
        lines.append(f"- Procedural entries: {len(artifact.procedural)}")
        lines.append(f"- Identity entries: {len(artifact.identity)}")
        lines.append(f"- Working entries: {len(artifact.working)}")
        lines.append(f"- Total entries: {len(artifact.all_entries())}")
        lines.append(f"- Signed: {'yes' if artifact.signature else 'no'}")
        if artifact.root_hash:
            lines.append(f"- Integrity: {'✓ valid' if artifact.verify_integrity() else '✗ INVALID'}")
    else:
        lines.append("\nNo memory artifact yet. Say 'remember this' to start.")

    return "\n".join(lines)

print(memory_status())
```

## Automatic Memory Behaviors

Beyond explicit "remember" commands, proactively create memory entries when:

1. **User states a preference** → `remember_identity(preferences={...})`
2. **You learn a project fact** → `remember_fact(subject, predicate, object)`
3. **A significant event occurs** → `remember_episode(observation, salience=0.8)`
4. **You discover a reusable pattern** → `remember_skill(name, description, body)`
5. **Session ends** → Consider saving working memory (goals, pending actions)

## Notes

- All `.pam` files are human-readable JSON — users can inspect them anytime
- The signing key in `~/.pam/keys/agent.key` is a 32-byte Ed25519 seed
- Memory is incremental: entries accumulate, old ones are never deleted unless explicitly requested
- On import, entries are deduplicated by content-addressable ID (same content = same hash)
- The rehydration engine ranks entries by relevance when importing, so large memories don't overwhelm context
