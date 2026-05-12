# Portable Agent Memory — Browser Extension

A Chrome/Edge browser extension that provides persistent, portable memory for AI agents across ChatGPT, Claude, Gemini, and Microsoft Copilot.

## Features

- **Quick Remember** — Save observations, facts, skills, and working context from any AI chat
- **Text Selection** — Highlight text on AI chat pages and click "Remember this"
- **Memory Injection** — Paste memory context directly into AI chat inputs or clipboard
- **Export/Import** — Download memories as `.pam` files for cross-agent portability
- **Side Panel** — Full memory management with tabs, search, and bulk operations
- **Context Menu** — Right-click selected text to remember it

## Installation

1. Open Chrome/Edge and navigate to `chrome://extensions/` (or `edge://extensions/`)
2. Enable **Developer mode** (toggle in top-right corner)
3. Click **Load unpacked**
4. Select this `browser-extension` folder
5. The PAM icon will appear in your toolbar

## Supported AI Chat Sites

| Site | URL |
|------|-----|
| ChatGPT | chat.openai.com, chatgpt.com |
| Claude | claude.ai |
| Gemini | gemini.google.com |
| Microsoft Copilot | copilot.microsoft.com |

## Usage

### Quick Remember (Popup)
1. Click the PAM icon in your toolbar
2. Type a memory and select the type (Episode, Fact, Skill, Working)
3. Click "Remember"

### On AI Chat Pages
- A floating PAM button appears in the bottom-right corner
- Select text → click the "Remember this" tooltip that appears
- Use the floating button menu to inject memory context into the chat

### Export/Import
- **Export**: Click "Export .pam" to download your memories as a portable JSON file
- **Import**: Click "Import .pam" to load memories from a `.pam` file (from another agent or device)

## PAM Format (Browser Edition)

The browser extension uses a lightweight version of the PAM format:

```json
{
  "version": "1.0",
  "source_agent": {
    "name": "browser-extension",
    "model_family": "user",
    "runtime": "chrome",
    "version": "0.1.0"
  },
  "created_at": "2024-01-01T00:00:00.000Z",
  "episodic": [...],
  "semantic": [...],
  "procedural": [...],
  "working": [...],
  "identity": [...],
  "root_hash": "sha256:...",
  "signature": ""
}
```

### Hash Algorithm Note

The browser extension uses **SHA-256** (via Web Crypto API) for entry IDs and root hash computation. The full PAM SDK uses BLAKE3. Both produce content-addressable identifiers, but hashes will differ between browser and SDK-generated artifacts. The `sha256:` prefix on IDs distinguishes browser-generated entries.

## Memory Types

| Type | Description | Example |
|------|-------------|---------|
| **Episodic** | Events, observations, things that happened | "User prefers Python over JavaScript" |
| **Semantic** | Structured facts (subject-predicate-object) | "React" "is" "a UI framework" |
| **Procedural** | Skills, how-to knowledge | "Deploy to AWS: use CDK..." |
| **Working** | Current goals and active context | "Working on auth module refactor" |
| **Identity** | Persistent identity/preferences | "name: Alex" |

## Architecture

```
popup/          — Quick access popup (360×500px)
sidebar/        — Full side panel view with tabs & search
background/     — Service worker for storage & messaging
content/        — Content script injected on AI chat pages
lib/            — Pure JS PAM implementation (no dependencies)
icons/          — Extension icons (SVG-based PNG placeholders)
```

## Development

No build step required. Edit files and reload the extension:
1. Make changes
2. Go to `chrome://extensions/`
3. Click the refresh icon on the PAM extension card

## Privacy

- All memories stored **locally** in `chrome.storage.local`
- No data sent to external servers
- Export/import is manual and user-controlled
- No analytics or telemetry

## License

Part of the [Portable Agent Memory](https://github.com/portable-agent-memory) project.
