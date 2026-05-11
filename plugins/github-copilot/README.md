# PAM — GitHub Copilot Extension

> Persistent, portable, cryptographically-verified memory for AI agents — right inside GitHub Copilot Chat.

## What This Does

This GitHub Copilot Extension gives Copilot Chat persistent memory powered by the [Portable Agent Memory (PAM)](https://github.com/santhoshravindran7/portable-agent-memory) protocol. Memories are stored as `.pam` files with BLAKE3 integrity hashes and optional Ed25519 signatures.

## Commands

| Command | Description |
|---------|-------------|
| `@pam remember "some text"` | Store an episodic memory (observation) |
| `@pam remember --fact subject predicate object` | Store a semantic triple |
| `@pam remember --skill name description` | Store a procedural skill |
| `@pam recall` | List all stored memories |
| `@pam recall --query "search terms"` | Search and rehydrate memories |
| `@pam export` | Export the full `.pam` artifact as JSON |
| `@pam import <json>` | Import a `.pam` artifact |
| `@pam status` | Show memory statistics |
| `@pam verify` | Verify cryptographic integrity |
| `@pam help` | Show available commands |

## Architecture

```
┌─────────────────────────────────────────────┐
│           GitHub Copilot Chat               │
│  User types: @pam remember "fix auth bug"   │
└──────────────────┬──────────────────────────┘
                   │ POST /api/chat (SSE)
                   ▼
┌─────────────────────────────────────────────┐
│         PAM Copilot Extension               │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
│  │ handler  │→ │ command  │→ │ pam-bridge│ │
│  │   .js    │  │ parser   │  │   .js     │ │
│  └──────────┘  └──────────┘  └─────┬─────┘ │
│                                    │        │
│  ┌──────────┐  ┌──────────────────┐│        │
│  │  sse.js  │  │  Python SDK      ││        │
│  │ (stream) │  │  (child_process) │◄        │
│  └──────────┘  └──────────────────┘         │
└─────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  data/<user>.pam  (persistent JSON files)   │
│  BLAKE3 hashes · Ed25519 signatures         │
└─────────────────────────────────────────────┘
```

## Deployment

### Option 1: Vercel (Recommended)

1. Fork or clone this repo
2. Install the [Vercel CLI](https://vercel.com/cli) or connect via the dashboard
3. Deploy:
   ```bash
   cd plugins/github-copilot
   npx vercel --prod
   ```
4. Set the deployment URL in your GitHub App manifest

> **Note:** Vercel serverless functions need Python available in the runtime.
> For production, consider a Docker-based deployment (Option 3).

### Option 2: Azure Functions / Azure App Service

1. Create an Azure App Service (Node.js 18+)
2. Ensure Python 3.10+ is available on the instance
3. Deploy the `plugins/github-copilot/` directory
4. Set environment variables:
   - `PAM_PYTHON` — path to Python binary (default: `python3`)
   - `PAM_DATA_DIR` — persistent storage path for `.pam` files

### Option 3: Self-Hosted (Docker / VM)

```bash
cd plugins/github-copilot
npm install
# Ensure Python 3.10+ is available with the PAM SDK
pip install -e ../../sdk/python
npm start
```

The server runs on port 3000 by default (`PORT` env var to override).

## Registering as a GitHub App

1. Go to **GitHub Settings → Developer settings → GitHub Apps → New GitHub App**
2. Set the following:
   - **Name:** `portable-agent-memory`
   - **Homepage URL:** `https://github.com/santhoshravindran7/portable-agent-memory`
   - **Callback URL:** your deployment URL
   - **Webhook URL:** `https://YOUR_DEPLOYMENT_URL/api/chat`
   - **Permissions:** Contents → Read-only
3. Under **Copilot**, enable the extension and set the endpoint to `https://YOUR_DEPLOYMENT_URL/api/chat`
4. Install the app on your account/org
5. In any Copilot Chat, type `@pam help` to verify

See [app.yml](./app.yml) for the full manifest.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | Server port |
| `PAM_PYTHON` | `python3` | Python binary path |
| `PAM_DATA_DIR` | `./data` | Where `.pam` files are stored |

## Development

```bash
cd plugins/github-copilot
npm install
npm start
# Test with curl:
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"@pam help"}]}'
```

## License

MIT — see [LICENSE](../../LICENSE)
