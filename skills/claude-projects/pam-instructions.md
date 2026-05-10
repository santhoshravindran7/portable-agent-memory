# Portable Agent Memory — Claude Projects Instructions

You have access to the Portable Agent Memory system via the `pam-sdk` Python package. Use it to persist memory across conversations and enable memory portability between AI agents.

## When to Activate

- User says "remember this", "save memory", "export memory", "what do you remember"
- User wants to transfer context to another AI
- User says "import memory", "load memory"
- You learn important facts about the user's preferences, project, or workflow
- User mentions a `.pam` file

## Core Operations

### Setup (run once per session if needed)

```python
from pathlib import Path
from datetime import datetime, timezone
from pam import MemoryArtifact, EpisodicEntry, SemanticEntry, ProceduralEntry, IdentityEntry
from pam.models import SourceAgent
from pam.transport.file import FileTransport
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PAM_DIR = Path.home() / ".pam"
KEYS_DIR = PAM_DIR / "keys"
MEMORIES_DIR = PAM_DIR / "memories"
MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
KEYS_DIR.mkdir(parents=True, exist_ok=True)

def get_or_create_key() -> Ed25519PrivateKey:
    key_path = KEYS_DIR / "agent.key"
    if key_path.exists():
        return Ed25519PrivateKey.from_private_bytes(key_path.read_bytes())
    key = Ed25519PrivateKey.generate()
    key_path.write_bytes(key.private_bytes_raw())
    key_path.with_suffix(".pub").write_bytes(key.public_key().public_bytes_raw())
    return key

def load_or_create_artifact() -> MemoryArtifact:
    path = MEMORIES_DIR / "current.pam"
    if path.exists():
        return FileTransport.load(str(path))
    return MemoryArtifact(
        source_agent=SourceAgent(name="claude", model_family="claude", runtime="claude-projects", version="1.0")
    )

def save_artifact(artifact: MemoryArtifact) -> None:
    key = get_or_create_key()
    artifact.sign(key.private_bytes_raw())
    FileTransport.save(artifact, str(MEMORIES_DIR / "current.pam"))
```

### Remember

```python
# Episodic (events/observations)
artifact = load_or_create_artifact()
artifact.episodic.append(EpisodicEntry(
    timestamp=datetime.now(timezone.utc).isoformat(),
    actor="user", observation="...", salience=0.8, event_type="observation"
))
save_artifact(artifact)

# Semantic (facts: subject-predicate-object)
artifact = load_or_create_artifact()
artifact.semantic.append(SemanticEntry(subject="project", predicate="uses", object="FastAPI", confidence=0.95))
save_artifact(artifact)

# Identity (preferences)
artifact = load_or_create_artifact()
artifact.identity.append(IdentityEntry(preferences={"style": "concise"}, persona=""))
save_artifact(artifact)

# Procedural (skills)
artifact = load_or_create_artifact()
artifact.procedural.append(ProceduralEntry(name="deploy", description="Deploy to prod", body="git push origin main", language="shell"))
save_artifact(artifact)
```

### Recall

```python
path = MEMORIES_DIR / "current.pam"
if path.exists():
    artifact = FileTransport.load(str(path))
    for e in artifact.episodic[-5:]:
        print(f"[{e.timestamp[:10]}] {e.observation}")
    for s in artifact.semantic:
        print(f"{s.subject} {s.predicate} {s.object}")
    for p in artifact.procedural:
        print(f"Skill: {p.name} — {p.description}")
    for i in artifact.identity:
        print(f"Preferences: {i.preferences}")
```

### Export

```python
artifact = FileTransport.load(str(MEMORIES_DIR / "current.pam"))
key = get_or_create_key()
artifact.sign(key.private_bytes_raw())
FileTransport.save(artifact, "exported_memory.pam")
```

### Import

```python
from pam import RehydrationEngine

imported = FileTransport.load("path/to/file.pam")
if imported.root_hash and not imported.verify_integrity():
    print("WARNING: integrity check failed")

# Re-hydrate for context
engine = RehydrationEngine()
context = engine.rehydrate(imported, task="current task description")
print(context)

# Merge into local memory
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
```

## Automatic Behaviors

Proactively remember when:
- User states a preference → save as IdentityEntry
- You discover a project fact → save as SemanticEntry
- A significant interaction occurs → save as EpisodicEntry
- You learn a reusable workflow → save as ProceduralEntry

## Storage

- Memories: `~/.pam/memories/current.pam` (human-readable JSON)
- Keys: `~/.pam/keys/agent.key` (32-byte Ed25519 seed)
- Entries are content-addressable (BLAKE3 hash = deduplication on import)
