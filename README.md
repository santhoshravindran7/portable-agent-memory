# Portable Agent Memory Protocol

> **MCP standardized tool access. A2A standardized task handoff. Portable Agent Memory standardizes verified memory transfer.**

Portable Agent Memory is an open protocol and reference SDK for **portable, cryptographically-verified memory transfer across heterogeneous AI agents**. Your AI agent's memory shouldn't die when you close the tab or switch providers.

Portable Agent Memory uses plain JSON — no special tools needed to inspect or create artifacts. Any language with a JSON parser can implement Portable Agent Memory.

Portable Agent Memory lets any agent export its memory as a signed, portable artifact that any other agent can verify and re-hydrate — across models, vendors, and runtimes.

---

## Why Portable Agent Memory?

Today's AI agents suffer from six critical memory problems:

| Problem | What Happens | Portable Agent Memory's Solution |
|---------|-------------|----------------|
| **Vendor lock-in** | Switch from Claude to GPT? Start from zero. | Portable `.pam` artifacts (plain JSON) work with any model |
| **Session amnesia** | Close the tab, lose everything | Persistent, exportable memory across sessions |
| **No integrity** | Memory can be silently modified | BLAKE3 Merkle-DAG with Ed25519 signatures |
| **Coarse access** | All-or-nothing memory sharing | Capability tokens for fine-grained scoped access |
| **Prompt injection** | Recalled memory can hijack the agent | Injection-resistant structural framing |
| **No cross-model transfer** | Different context windows, tokenizers, formats | Model-aware re-hydration with summarization |

## Where Portable Agent Memory Fits

```
┌──────────────────────────────────────────────────────────────────┐
│                   Agent Interoperability Stack                   │
├──────────────────────────────────────────────────────────────────┤
│  Portable Agent Memory — Memory Transfer (what agents know)     │
│  A2A                   — Task Handoff (what agents do)          │
│  MCP                   — Tool Access (what agents use)          │
└──────────────────────────────────────────────────────────────────┘
```

## Key Features

- 🧠 **5-Component Memory Model** — Episodic events, Semantic facts, Procedural skills, Working state, Identity preferences
- 🔐 **Cryptographic Verification** — BLAKE3 content-addressed entries in an Ed25519-signed Merkle-DAG
- 🎫 **Capability-Scoped Access** — Fine-grained tokens for selective memory disclosure between agents
- 🛡️ **Injection-Resistant Re-Hydration** — Structural framing prevents prompt injection via recalled memory
- 📦 **JSON-First Format** — `.pam` files are human-readable JSON; CBOR (`.pam.cbor`) available for compact transport
- 📊 **Measurable Fidelity** — Transfer Continuity Score (TCS) and Re-Hydration Fidelity (RHF) metrics

## Format Philosophy

Portable Agent Memory is JSON-first by design:
- `.pam` files are human-readable JSON — inspect with any text editor
- No special tools required to read or create Portable Agent Memory artifacts
- CBOR (`.pam.cbor`) available as optional compact format for bandwidth-sensitive transport
- Any language with a JSON parser can implement Portable Agent Memory

## Quick Start

### Option 1: Marketplace Plugin (recommended — no install needed)

| Platform | Install |
|----------|---------|
| **GitHub Copilot** | Install from [GitHub Marketplace](https://github.com/marketplace) → use `@pam remember ...` in chat |
| **Claude Code** | `/plugin install portable-agent-memory` → use `/remember ...` |
| **OpenAI Codex** | Copy `plugins/openai-codex/AGENTS.md` to your project root |
| **Copilot CLI** | Copy `skills/copilot-cli/pam.md` to `~/.copilot/skills/pam/` |

### Option 2: CLI (for power users)

```bash
pip install git+https://github.com/santhoshravindran7/portable-agent-memory.git#subdirectory=sdk/python
```

```bash
pam remember "I prefer TypeScript and dark mode"
pam remember --fact "project" "uses" "Next.js 14"
pam recall
pam export my-memory.pam
pam import colleague-memory.pam
```

### Option 3: Python SDK (for developers building integrations)

```python
from pam import MemoryArtifact, SourceAgent, EpisodicEntry, SemanticEntry, IdentityEntry
from pam.rehydration.engine import RehydrationEngine
from pam.transport.file import FileTransport
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from datetime import datetime

# 1. Create memory entries
episodic = EpisodicEntry(
    timestamp=datetime.now().isoformat(),
    actor="user",
    observation="User prefers async Python with type hints",
    salience=0.9,
    event_type="observation"
)

semantic = SemanticEntry(
    subject="project", predicate="uses", object="FastAPI with SQLAlchemy",
    confidence=0.95, source_event_ids=[episodic.id]
)

identity = IdentityEntry(
    preferences={"style": "concise", "testing": "pytest"},
    persona="Senior Python developer",
    language="en",
    policies=["Always include type hints"],
    custom_instructions="Prefer functional patterns"
)

# 2. Bundle into a signed artifact
artifact = MemoryArtifact(
    source_agent=SourceAgent(name="my-claude-agent", model_family="claude", runtime="custom"),
    episodic=[episodic],
    semantic=[semantic],
    identity=[identity],
)

private_key = Ed25519PrivateKey.generate()
artifact.sign(private_key.private_bytes_raw())

# 3. Export as portable .pam file (human-readable JSON)
FileTransport.save(artifact, "my_memory.pam")

# 4. Later, on a different model — load and re-hydrate
loaded = FileTransport.load("my_memory.pam")
assert loaded.verify_signature(private_key.public_key().public_bytes_raw())
assert loaded.verify_integrity()

engine = RehydrationEngine()
context = engine.rehydrate(loaded, task="Continue building the auth module")
print(context)  # Ready to inject into any LLM's context window
```

## Examples

| Example | Description |
|---------|-------------|
| [`01_basic_memory.py`](examples/01_basic_memory.py) | Create, sign, save, and verify a Portable Agent Memory artifact |
| [`02_cross_model_transfer.py`](examples/02_cross_model_transfer.py) | Transfer memory from Claude to GPT |
| [`03_capability_scoping.py`](examples/03_capability_scoping.py) | Selective memory disclosure with capability tokens |
| [`04_provenance_verification.py`](examples/04_provenance_verification.py) | Tamper-evident memory with Merkle-DAG |
| [`05_multi_agent_handoff.py`](examples/05_multi_agent_handoff.py) | 3-agent team collaboration with scoped handoffs |
| [`06_cross_model_validation.py`](examples/06_cross_model_validation.py) | Prove memory portability with secret facts + tamper detection |
| [`07_enterprise_vendor_migration.py`](examples/07_enterprise_vendor_migration.py) | Healthcare AI vendor migration (Claude → GPT) with HIPAA compliance |
| [`08_session_continuity.py`](examples/08_session_continuity.py) | Accumulate knowledge across 3 sessions — defeat session amnesia |

Run any example:
```bash
cd pam-protocol
python examples/02_cross_model_transfer.py
```

## Project Structure

```
pam-protocol/
├── spec/
│   └── PAM-SPEC-v1.md          # Full protocol specification (RFC-style)
├── schemas/
│   ├── artifact.schema.json     # Memory artifact envelope schema
│   ├── entries.schema.json      # Entry type schemas (5 components)
│   └── capability-token.schema.json
├── sdk/python/
│   ├── pam/
│   │   ├── models/              # Entry types, artifact, source agent
│   │   ├── provenance/          # Merkle-DAG graph operations
│   │   ├── capabilities/        # Capability tokens & validation
│   │   ├── rehydration/         # Re-hydration engine (6-step pipeline)
│   │   ├── serialization/       # JSON (pretty + canonical) & CBOR codecs
│   │   └── transport/           # File-based transport (.pam JSON, .pam.cbor)
│   └── tests/                   # 54 tests
├── examples/                    # 8 runnable demo scripts
├── plugins/
│   ├── github-copilot/          # GitHub Copilot Extension (Marketplace)
│   ├── claude-code/             # Claude Code Plugin (MCP server + skills)
│   └── openai-codex/            # OpenAI Codex (AGENTS.md)
├── skills/
│   └── copilot-cli/             # GitHub Copilot CLI skill
└── README.md
```

## How Portable Agent Memory Works

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Source   │     │  Export   │     │ Verify   │     │  Target  │
│  Agent    │────▶│  .pam    │────▶│ Integrity│────▶│  Agent   │
│ (Claude)  │     │ artifact │     │ + Caps   │     │  (GPT)   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                │                 │
                 BLAKE3 hash     Ed25519 sig       Re-hydrate:
                 Merkle-DAG      Cap tokens        rank, compress,
                 JSON encode     Scope filter       frame, inject
```

**The 6-step re-hydration pipeline:**
1. **Verify** — Check cryptographic signatures and schema version
2. **Filter** — Apply capability token scoping
3. **Rank** — Score entries by relevance to current task
4. **Compress** — Replace low-salience entries with summaries to fit token budget
5. **Frame** — Wrap content in injection-resistant boundaries
6. **Render** — Format for target model's context window

## Comparison

| Feature | Portable Agent Memory | Mem0 | Letta | AMCP | MCP | A2A |
|---------|-----|------|-------|------|-----|-----|
| Portable format | ✅ | ❌ | ❌ | ✅ | N/A | N/A |
| Cross-LLM transfer | ✅ | ❌ | ❌ | ✅ (spec) | N/A | N/A |
| Crypto verification | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Capability scoping | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Injection defense | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Working SDK | ✅ | ✅ | ✅ | Partial | ✅ | ✅ |
| SaaS available | 🔜 | ✅ | ✅ | ❌ | ❌ | ❌ |
| Open protocol | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |

## Roadmap

- [x] Protocol Specification v1.0
- [x] Python SDK with 54 tests
- [x] JSON Schemas
- [x] Working examples (8 scenarios)
- [x] CLI tool (`pam remember`, `pam recall`, etc.)
- [x] GitHub Copilot Extension (Marketplace plugin)
- [x] Claude Code Plugin (MCP server + skills)
- [x] OpenAI Codex integration (AGENTS.md)
- [x] GitHub Copilot CLI skill
- [ ] LangChain / CrewAI adapters
- [ ] TypeScript SDK
- [ ] Portable Agent Memory Cloud (managed verification + re-hydration service)
- [ ] Memory Marketplace
- [ ] Conformance certification program

## Protocol Specification

The full spec is at [`spec/PAM-SPEC-v1.md`](spec/PAM-SPEC-v1.md) — an implementable, RFC-style document covering:

- Memory artifact format and the 5-component model
- Merkle-DAG provenance graph
- Serialization (JSON-first with optional CBOR)
- Capability-based access control
- 7-step re-hydration protocol
- Injection-resistant framing
- Redaction pipeline
- Transport bindings (HTTP, MCP, file, WebSocket)
- TCS/RHF evaluation metrics
- Security considerations
- Schema versioning and migration

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. We welcome:
- Protocol feedback and spec improvements
- SDK contributions (especially TypeScript, Rust, Go)
- Framework adapters (LangChain, CrewAI, AutoGen, Semantic Kernel)
- Bug reports and feature requests

## License

[Apache License 2.0](LICENSE)

## Citation

```bibtex
@software{pam_protocol,
  title={Portable Agent Memory Protocol},
  year={2026},
  url={https://github.com/pam-protocol/pam-protocol},
  license={Apache-2.0}
}
```
