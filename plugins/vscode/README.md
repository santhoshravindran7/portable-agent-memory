# Portable Agent Memory (PAM) for VS Code

> **Persistent, portable, cryptographically-verified memory for AI agents.**

Give your AI coding assistant a brain that persists across sessions, transfers between models, and verifies its own integrity.

## ✨ Features

### 🧠 Remember Anything
- **Episodic Memory** — Store experiences, conversations, and context
- **Semantic Memory** — Record facts as subject/predicate/object triples
- **Procedural Memory** — Save skills and how-to knowledge
- **Working Memory** — Track active context items
- **Identity Memory** — Preserve preferences and personality

### 🔍 Instant Recall
- Full-text search across all memory types
- Beautiful webview panel with color-coded memory cards
- Sidebar tree view organized by memory type

### 📦 Portable & Secure
- Export/import `.pam` files — move memories between machines
- Cryptographic integrity verification
- Works with any AI model: Copilot, Claude, GPT, local models

### 📊 Status at a Glance
- Status bar shows total memory count
- Quick status command for detailed breakdown

## 🚀 Quick Start

1. Install the extension
2. Open Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`)
3. Type "PAM: Remember This" and enter your first memory
4. Use "PAM: Recall" to view all stored memories

## 📋 Commands

| Command | Description |
|---------|-------------|
| `PAM: Remember This` | Store text as episodic memory |
| `PAM: Remember Selection` | Store selected text as memory |
| `PAM: Remember Fact` | Quick input for subject/predicate/object |
| `PAM: Recall` | Show all memories in webview panel |
| `PAM: Search Memory` | Full-text search across memories |
| `PAM: Export Memory` | Export to `.pam` file |
| `PAM: Import Memory` | Import from `.pam` file |
| `PAM: Verify Integrity` | Cryptographic integrity check |
| `PAM: Status` | Show memory statistics |
| `PAM: Clear All` | Clear all memories (with confirmation) |

## 🔧 Requirements

This extension requires the PAM CLI tool. If not installed, you'll be prompted to install it automatically:

```bash
pip install git+https://github.com/santhoshravindran7/portable-agent-memory.git@main#subdirectory=sdk/python
```

## 🏗️ How It Works

PAM uses the open [Portable Agent Memory](https://github.com/santhoshravindran7/portable-agent-memory) protocol:

1. **Memories** are stored locally as cryptographically-signed artifacts
2. **Memory types** follow cognitive science categories (episodic, semantic, procedural)
3. **Export/Import** uses the `.pam` format for cross-agent transfer
4. **Verification** ensures no tampering via SHA-256 integrity chains

## 🌐 Cross-Agent Compatibility

PAM memories work across:
- GitHub Copilot
- Claude (via MCP)
- ChatGPT
- Local models (Ollama, LM Studio)
- Any agent implementing the PAM protocol

## 📄 License

Apache-2.0 — See [repository](https://github.com/santhoshravindran7/portable-agent-memory) for details.
