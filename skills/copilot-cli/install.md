# Installing the Portable Agent Memory Skill for GitHub Copilot CLI

## Steps

1. Install the Portable Agent Memory SDK directly from GitHub:
   ```bash
   pip install git+https://github.com/santhoshravindran7/portable-agent-memory.git#subdirectory=sdk/python
   ```

2. Copy the skill file:
   ```bash
   mkdir -p ~/.copilot/skills/pam
   cp skills/copilot-cli/pam.md ~/.copilot/skills/pam/pam.md
   ```

3. Done — your agent now has persistent, portable memory.

## CLI Tool

After installation, you also get the `pam` command:

```bash
pam remember "User prefers TypeScript and dark mode"
pam remember --fact "project" "uses" "Next.js 14"
pam recall
pam export my_memory.pam
pam import colleague_memory.pam
pam inspect some_file.pam
pam status
```

No code needed — manage agent memory from the command line.

## Verify

Ask your Copilot CLI agent:
> "What do you remember?"

It should check `~/.pam/memories/` and report any stored memories, or indicate the memory store is empty.

## What You Get

- **Persistent memory** across sessions — facts, preferences, and skills survive restarts
- **Export/import** — transfer memory between agents with signed `.pam` files
- **Auto-signing** — Ed25519 key auto-generated on first use in `~/.pam/keys/`
- **Human-readable** — `.pam` files are JSON, inspect them anytime

## Uninstall

```bash
rm ~/.copilot/skills/pam/pam.md
# Optionally remove stored memories:
rm -rf ~/.pam/
```
