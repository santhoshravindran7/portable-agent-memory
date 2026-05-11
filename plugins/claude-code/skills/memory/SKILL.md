# Portable Agent Memory (PAM) — Skill

You have access to **Portable Agent Memory (PAM)** — a persistent, portable, cryptographically-verified memory system. Use it to remember context across sessions and transfer knowledge between AI agents.

## When to Use Memory

**Proactively remember** important information during conversations:

- **User preferences**: coding style, language choices, tool preferences, communication style
- **Project context**: architecture decisions, tech stack, directory structure, conventions
- **Facts and decisions**: key outcomes, agreements, resolved debates, chosen approaches
- **Procedures**: workflows the user frequently uses, deployment steps, debugging patterns
- **Working context**: current goals, in-progress tasks, blockers, next steps

## How to Use Memory

### Automatic Memory (do this without being asked)

1. **At session start**: Call `pam_recall` with an empty query to load existing memories. Silently incorporate them into your understanding — don't narrate unless asked.
2. **During conversation**: When you detect important information (preferences, decisions, facts), call `pam_remember` to save it. Briefly mention what you saved (e.g., "I'll remember that you prefer TypeScript").
3. **At session end**: Call `pam_remember` with type `working` to save current goals, in-progress work, and next steps.

### Available MCP Tools

| Tool | Purpose |
|------|---------|
| `pam_remember` | Store a memory (episodic, semantic, procedural, or working) |
| `pam_recall` | Search and retrieve memories by query and/or type |
| `pam_export` | Export all memories to a portable `.pam` file |
| `pam_import` | Import memories from a `.pam` file |
| `pam_verify` | Verify cryptographic integrity of the memory store |
| `pam_status` | Show memory statistics (counts by type, storage info) |
| `pam_rehydrate` | Generate a context prompt from memories, optionally filtered by task |

### Memory Types

- **episodic**: Specific events and interactions — "User deployed v2.1 to staging on Friday"
- **semantic**: Knowledge facts — "User's project uses FastAPI with PostgreSQL"
- **procedural**: Reusable procedures — "To deploy: run `make build && kubectl apply -f k8s/`"
- **working**: Current context — goals, sub-goals, scratch notes, pending actions

### Best Practices

1. **Be selective**: Don't remember everything. Focus on high-salience information that will be useful in future sessions.
2. **Use the right type**: Preferences → semantic. Events → episodic. How-to → procedural. Current state → working.
3. **Include context**: When remembering, include enough context for future recall without the original conversation.
4. **Check before storing duplicates**: Call `pam_recall` before `pam_remember` to avoid storing information you already know.
5. **Respect privacy**: Never store secrets, tokens, passwords, or sensitive credentials in memory.

### Example Patterns

**User says "I always use 4-space indentation":**
```
→ pam_remember(text="User prefers 4-space indentation for all code", type="semantic")
```

**User completes a deployment:**
```
→ pam_remember(text="Deployed v2.1 to production. Migration included adding user_preferences table.", type="episodic")
```

**User shows you their deploy workflow:**
```
→ pam_remember(text="Deploy workflow: 1) Run tests with pytest 2) Build with docker compose 3) Push to ECR 4) Apply k8s manifests", type="procedural")
```

**End of session:**
```
→ pam_remember(text="Working on: migrating auth from sessions to JWT. Done: user model, token generation. Next: refresh token endpoint, middleware.", type="working")
```
