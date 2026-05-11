# Portable Agent Memory — Claude Code Plugin

**Persistent, portable, cryptographically-verified memory that travels with you across AI agents.**

PAM gives Claude Code a long-term memory that persists across sessions, exports to portable `.pam` files, and can be imported by any PAM-compatible AI agent.

## Installation

### From Claude Code Marketplace

```
/plugin install portable-agent-memory
```

### Manual Setup (optional)

Run the setup script to pre-install the SDK and generate signing keys:

```bash
# macOS / Linux
bash plugins/claude-code/scripts/setup.sh

# Windows
powershell plugins/claude-code/scripts/setup.ps1
```

> **Note:** The plugin auto-installs the PAM SDK on first use — manual setup is optional.

## Slash Commands

| Command | Description |
|---------|-------------|
| `/remember <text>` | Store a memory (auto-detects type) |
| `/recall [query]` | Search memories (empty = show all) |
| `/export-memory [file]` | Export to portable `.pam` file |
| `/import-memory <file>` | Import memories from `.pam` file |
| `/memory-status` | Show memory statistics |

## How It Works

### Automatic Memory

The plugin's skill instructs Claude to **automatically**:
- Load existing memories at session start
- Detect and save important context during conversations (preferences, decisions, facts)
- Save working context (goals, progress) at session end via hooks

### Memory Types

| Type | Use For | Example |
|------|---------|---------|
| **Semantic** | Facts & preferences | "User prefers TypeScript with strict mode" |
| **Episodic** | Events & interactions | "Deployed v2.1 to production on Friday" |
| **Procedural** | Workflows & how-tos | "Deploy: run tests → build → push → apply k8s" |
| **Working** | Current context | "Working on auth module, JWT refresh next" |

### Portability

Export your memories and use them with any PAM-compatible agent:

```
/export-memory project-context.pam
```

Then in another agent (GPT, Gemini, or another Claude instance):

```
/import-memory project-context.pam
```

### Cryptographic Integrity

Every memory is content-addressable via **BLAKE3** hashes. The memory store is signed with **Ed25519** keys. On import, PAM verifies that memories haven't been tampered with.

## Architecture

```
~/.pam/
├── memory.pam       # Your memory store (human-readable JSON)
├── signing.key      # Ed25519 private key (auto-generated)
└── signing.pub      # Ed25519 public key
```

The plugin runs an **MCP server** (`scripts/pam-server.py`) that wraps the PAM Python SDK, exposing these tools:

- `pam_remember` — Store a memory with type classification
- `pam_recall` — Substring search across all memory types
- `pam_export` — Serialize to `.pam` file with integrity hashes
- `pam_import` — Merge from `.pam` file with deduplication
- `pam_verify` — Check BLAKE3 hashes and Ed25519 signatures
- `pam_status` — Memory counts, storage info, integrity status
- `pam_rehydrate` — Generate ranked context prompt for a task

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PAM_HOME` | `~/.pam` | Memory storage directory |

## License

Apache-2.0 — see the [PAM repository](https://github.com/santhoshravindran7/portable-agent-memory) for details.
