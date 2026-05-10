# Portable Agent Memory Skills — For Any AI Agent

Portable Agent Memory skills are **agent instruction files** that teach an AI agent how to persist, export, and import portable memory artifacts. Drop a skill file into your agent's configuration and it gains persistent, cross-model memory — no servers, no hosting, no infrastructure.

## How It Works

1. **Install the SDK**: `pip install pam-sdk`
2. **Copy the skill file** for your agent platform into its instructions folder
3. **Done** — your agent now has persistent, portable memory

The agent itself manages memory by running Python code via the Portable Agent Memory SDK. Memory is stored as `.pam` files (human-readable JSON) in `~/.pam/memories/`. Cryptographic signing uses Ed25519 keys auto-generated in `~/.pam/keys/`.

## Available Skills

| Platform | File | Install Location |
|----------|------|-----------------|
| GitHub Copilot CLI | `copilot-cli/pam.md` | `~/.copilot/skills/pam/pam.md` |
| Claude Projects | `claude-projects/pam-instructions.md` | Project custom instructions |
| Generic (any LLM) | `generic/pam-skill.md` | System prompt or custom instructions |

## Zero Hosting Required

- No MCP server to run
- No cloud service to configure
- No API keys to manage
- Memory lives as local files the agent reads/writes directly
- Export a `.pam` file to transfer memory between agents on different machines or models

## Design Principles

- **Zero config** — works out of the box after `pip install pam-sdk`
- **Auto-key generation** — Ed25519 keypair created on first use
- **File-based storage** — memories are human-readable JSON in `~/.pam/memories/`
- **Incremental** — each "remember" adds to the artifact, doesn't rebuild
- **Portable** — export produces a file any Portable Agent Memory-compatible agent can import
- **Secure** — signed artifacts with BLAKE3 content hashing, verified on import
- **Model-agnostic** — works with Claude, GPT, Gemini, or any LLM that can run Python

## Quick Start

```bash
pip install pam-sdk

# For Copilot CLI:
mkdir -p ~/.copilot/skills/pam
cp skills/copilot-cli/pam.md ~/.copilot/skills/pam/pam.md

# For Claude Projects:
# Paste contents of skills/claude-projects/pam-instructions.md into Project instructions

# For any other agent:
# Include contents of skills/generic/pam-skill.md in your system prompt
```

Then just tell your agent: *"Remember that I prefer TypeScript over JavaScript"* — it handles the rest.
