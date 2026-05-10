# Portable Agent Memory — Generic Skill

You have the Portable Agent Memory capability. This enables you to persist memory across sessions and transfer memory between different AI agents. Use the `pam-sdk` Python package (install: `pip install pam-sdk`).

## Triggers

Activate Portable Agent Memory when the user:
- Says "remember this", "save memory", "export memory", "what do you remember"
- Wants to transfer context to/from another AI agent
- Says "import memory", "load memory", "continue from where [agent] left off"
- Mentions a `.pam` file
- States an important preference, fact, or workflow you should retain

## Memory Types

| Type | Class | Use For |
|------|-------|---------|
| Episodic | `EpisodicEntry` | Events, interactions, observations |
| Semantic | `SemanticEntry` | Facts as subject-predicate-object triples |
| Procedural | `ProceduralEntry` | Reusable skills and procedures |
| Identity | `IdentityEntry` | User preferences, persona, policies |
| Working | `WorkingEntry` | Current goals, scratch-pad |

## Implementation

### Initialization

```python
from pathlib import Path
from datetime import datetime, timezone
from pam import MemoryArtifact, EpisodicEntry, SemanticEntry, ProceduralEntry, IdentityEntry, WorkingEntry
from pam.models import SourceAgent
from pam.transport.file import FileTransport
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PAM_DIR = Path.home() / ".pam"
KEYS_DIR = PAM_DIR / "keys"
MEMORIES_DIR = PAM_DIR / "memories"
MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
KEYS_DIR.mkdir(parents=True, exist_ok=True)

# Auto-generate signing key on first use
def get_or_create_key() -> Ed25519PrivateKey:
    key_path = KEYS_DIR / "agent.key"
    if key_path.exists():
        return Ed25519PrivateKey.from_private_bytes(key_path.read_bytes())
    key = Ed25519PrivateKey.generate()
    key_path.write_bytes(key.private_bytes_raw())
    key_path.with_suffix(".pub").write_bytes(key.public_key().public_bytes_raw())
    return key

# Replace "your-agent-name" and "model-family" with your actual values
AGENT_NAME = "ai-agent"
MODEL_FAMILY = "llm"
RUNTIME = "generic"

def load_or_create_artifact() -> MemoryArtifact:
    path = MEMORIES_DIR / "current.pam"
    if path.exists():
        return FileTransport.load(str(path))
    return MemoryArtifact(
        source_agent=SourceAgent(name=AGENT_NAME, model_family=MODEL_FAMILY, runtime=RUNTIME, version="1.0")
    )

def save_artifact(artifact: MemoryArtifact) -> None:
    key = get_or_create_key()
    artifact.sign(key.private_bytes_raw())
    FileTransport.save(artifact, str(MEMORIES_DIR / "current.pam"))
```

### Remember

```python
def remember_episode(observation: str, actor: str = "user", salience: float = 0.7):
    artifact = load_or_create_artifact()
    artifact.episodic.append(EpisodicEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=actor, observation=observation, salience=salience, event_type="observation"
    ))
    save_artifact(artifact)

def remember_fact(subject: str, predicate: str, obj: str, confidence: float = 0.9):
    artifact = load_or_create_artifact()
    artifact.semantic.append(SemanticEntry(subject=subject, predicate=predicate, object=obj, confidence=confidence))
    save_artifact(artifact)

def remember_skill(name: str, description: str, body: str = "", language: str = "natural"):
    artifact = load_or_create_artifact()
    artifact.procedural.append(ProceduralEntry(name=name, description=description, body=body, language=language))
    save_artifact(artifact)

def remember_identity(preferences: dict = None, persona: str = "", policies: list = None):
    artifact = load_or_create_artifact()
    artifact.identity.append(IdentityEntry(preferences=preferences or {}, persona=persona, policies=policies or []))
    save_artifact(artifact)
```

### Recall

```python
def recall() -> str:
    path = MEMORIES_DIR / "current.pam"
    if not path.exists():
        return "No memories stored yet."
    artifact = FileTransport.load(str(path))
    lines = []
    for e in artifact.episodic[-10:]:
        lines.append(f"[Episode] {e.observation}")
    for s in artifact.semantic:
        lines.append(f"[Fact] {s.subject} {s.predicate} {s.object}")
    for p in artifact.procedural:
        lines.append(f"[Skill] {p.name}: {p.description}")
    for i in artifact.identity:
        lines.append(f"[Identity] {i.preferences} {i.persona}")
    return "\n".join(lines) if lines else "Memory is empty."
```

### Export

```python
def export_memory(output_path: str = "exported_memory.pam") -> str:
    source = MEMORIES_DIR / "current.pam"
    if not source.exists():
        return "No memory to export."
    artifact = FileTransport.load(str(source))
    key = get_or_create_key()
    artifact.sign(key.private_bytes_raw())
    FileTransport.save(artifact, output_path)
    return f"Exported {len(artifact.all_entries())} entries to {output_path}"
```

### Import

```python
from pam import RehydrationEngine

def import_memory(path: str, task: str = "") -> str:
    imported = FileTransport.load(path)
    if imported.root_hash and not imported.verify_integrity():
        print("WARNING: Artifact integrity check failed — content may have been modified.")

    # Re-hydrate for context
    engine = RehydrationEngine()
    context = engine.rehydrate(imported, task=task)

    # Merge into local store (deduplicate by content-addressable ID)
    local = load_or_create_artifact()
    existing_ids = {e.id for e in local.all_entries()}
    for entry in imported.episodic:
        if entry.id not in existing_ids:
            local.episodic.append(entry)
    for entry in imported.semantic:
        if entry.id not in existing_ids:
            local.semantic.append(entry)
    for entry in imported.procedural:
        if entry.id not in existing_ids:
            local.procedural.append(entry)
    for entry in imported.identity:
        if entry.id not in existing_ids:
            local.identity.append(entry)
    save_artifact(local)
    return f"Imported {len(imported.all_entries())} entries.\n\nContext:\n{context}"
```

### Status

```python
def memory_status() -> str:
    path = MEMORIES_DIR / "current.pam"
    if not path.exists():
        return "No memory artifact. Say 'remember this' to start."
    artifact = FileTransport.load(str(path))
    return (
        f"Entries: {len(artifact.all_entries())} "
        f"(episodic={len(artifact.episodic)}, semantic={len(artifact.semantic)}, "
        f"procedural={len(artifact.procedural)}, identity={len(artifact.identity)})\n"
        f"Signed: {'yes' if artifact.signature else 'no'}\n"
        f"Integrity: {'valid' if artifact.verify_integrity() else 'INVALID'}"
    )
```

## Storage Layout

```
~/.pam/
├── keys/
│   ├── agent.key      # Ed25519 private key (32 bytes)
│   └── agent.pub      # Ed25519 public key (32 bytes)
└── memories/
    └── current.pam    # Current memory artifact (JSON)
```

## Proactive Memory

Don't wait for explicit "remember" commands. Automatically save:
- User preferences when stated
- Project facts when discovered
- Significant interactions
- Reusable workflows and procedures
