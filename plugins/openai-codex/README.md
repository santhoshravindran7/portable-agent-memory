# Portable Agent Memory — OpenAI Codex Integration

## Installation

Copy the `AGENTS.md` file to your project root or global Codex config:

### Per-project (recommended)
```bash
cp plugins/openai-codex/AGENTS.md /path/to/your/project/AGENTS.md
```

### Global (applies to all projects)
```bash
mkdir -p ~/.codex
cp plugins/openai-codex/AGENTS.md ~/.codex/AGENTS.md
```

Codex automatically discovers and follows AGENTS.md instructions.

## What You Get

- **Persistent memory** across Codex sessions
- **Portable export/import** — transfer context to Claude, GPT, Copilot, or any PAM-compatible agent
- **Cryptographic integrity** — BLAKE3 hashes + Ed25519 signatures
- **Human-readable** — .pam files are JSON, inspect anytime

## How It Works

1. Codex reads `AGENTS.md` at session start
2. The instructions tell Codex to check `~/.pam/memories/` for existing memories
3. During conversation, Codex saves important context (preferences, facts, skills)
4. On export, memories travel to any other agent via `.pam` files

## Uninstall

```bash
rm AGENTS.md           # or ~/.codex/AGENTS.md for global
rm -rf ~/.pam/         # optionally remove stored memories
```
