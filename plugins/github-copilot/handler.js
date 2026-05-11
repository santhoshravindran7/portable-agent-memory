// handler.js — Core request handler shared by Express server and Vercel function.

const { parseCommand } = require("./command-parser");
const bridge = require("./pam-bridge");
const { initSSE, sendContent, sendDone } = require("./sse");

const HELP_TEXT = `## 🧠 PAM — Portable Agent Memory

**Available commands:**

| Command | Description |
|---------|-------------|
| \`@pam remember "text"\` | Store an episodic memory |
| \`@pam remember --fact subject predicate object\` | Store a semantic fact |
| \`@pam remember --skill name description\` | Store a procedural skill |
| \`@pam recall\` | Show all memories |
| \`@pam recall --query "terms"\` | Search memories |
| \`@pam export\` | Export as .pam JSON |
| \`@pam import <json>\` | Import a .pam artifact |
| \`@pam status\` | Show memory statistics |
| \`@pam verify\` | Verify cryptographic integrity |
| \`@pam help\` | Show this help |

Memories are persistent, portable, and cryptographically verified using BLAKE3 hashes.
`;

/**
 * Handle a GitHub Copilot Extension chat request.
 * Expects req.body.messages (array with role/content).
 */
async function handleChat(req, res) {
  initSSE(res);

  try {
    const messages = req.body?.messages || [];
    const lastMsg = messages[messages.length - 1];
    const userText = lastMsg?.content || "";
    const userId =
      req.headers["x-github-user"] ||
      req.body?.copilot_user?.login ||
      "default";

    const cmd = parseCommand(userText);

    switch (cmd.command) {
      case "help":
        sendContent(res, HELP_TEXT);
        break;

      case "remember": {
        const result = await bridge.remember(userId, cmd.text, cmd.opts);
        sendContent(
          res,
          `✅ **Memory stored** (${result.kind})\n\n` +
            `> ${cmd.text}\n\n` +
            `Entry ID: \`${result.id}\``
        );
        break;
      }

      case "recall": {
        const result = await bridge.recall(userId, cmd.query);
        if (!result.memories.length) {
          sendContent(
            res,
            "📭 No memories found. Use `@pam remember` to store one."
          );
        } else {
          let md = `## 🧠 Recalled Memories (${result.memories.length})\n\n`;
          for (const m of result.memories) {
            if (m.type === "episodic") {
              md += `- **📝 Episodic:** ${m.observation} _(${m.created})_\n`;
            } else if (m.type === "semantic") {
              md += `- **🔗 Semantic:** ${m.subject} → ${m.predicate} → ${m.object}\n`;
            } else if (m.type === "procedural") {
              md += `- **⚙️ Procedural:** **${m.name}** — ${m.description}\n`;
            } else if (m.type === "working") {
              md += `- **📋 Working:** goals=${JSON.stringify(m.goals)}\n`;
            }
          }
          if (cmd.query) {
            md += `\n---\n### Rehydrated Context\n\n\`\`\`\n${result.prompt}\n\`\`\``;
          }
          sendContent(res, md);
        }
        break;
      }

      case "export": {
        const json = await bridge.exportArtifact(userId);
        sendContent(
          res,
          `## 📦 Exported PAM Artifact\n\n\`\`\`json\n${json}\n\`\`\``
        );
        break;
      }

      case "import": {
        const result = await bridge.importArtifact(userId, cmd.source);
        if (result.error) {
          sendContent(res, `❌ Import failed: ${result.error}`);
        } else {
          sendContent(
            res,
            `✅ **Imported** ${result.entries} memory entries successfully.`
          );
        }
        break;
      }

      case "status": {
        const stats = await bridge.status(userId);
        if (!stats.exists) {
          sendContent(
            res,
            "📭 No memory artifact found. Use `@pam remember` to get started."
          );
        } else {
          sendContent(
            res,
            `## 📊 Memory Status\n\n` +
              `| Metric | Value |\n|--------|-------|\n` +
              `| **Total Entries** | ${stats.total} |\n` +
              `| Episodic | ${stats.episodic} |\n` +
              `| Semantic | ${stats.semantic} |\n` +
              `| Procedural | ${stats.procedural} |\n` +
              `| Working | ${stats.working} |\n` +
              `| Identity | ${stats.identity} |\n` +
              `| Created | ${stats.created_at} |\n` +
              `| Agent | ${stats.agent} |\n` +
              `| Root Hash | ${stats.has_root_hash ? "✅" : "❌"} |\n` +
              `| Signed | ${stats.has_signature ? "✅" : "❌"} |`
          );
        }
        break;
      }

      case "verify": {
        const result = await bridge.verify(userId);
        if (result.error) {
          sendContent(res, `❌ ${result.error}`);
        } else {
          const icon = result.artifact_integrity ? "✅" : "❌";
          sendContent(
            res,
            `## 🔐 Integrity Verification\n\n` +
              `| Check | Result |\n|-------|--------|\n` +
              `| Artifact integrity | ${icon} |\n` +
              `| Provenance valid | ${result.provenance_valid ? "✅" : "❌"} |\n` +
              `| Invalid entries | ${result.invalid_entry_ids.length} |\n` +
              `| Total entries | ${result.total_entries} |\n` +
              `| Root hash | \`${result.root_hash.slice(0, 16)}…\` |`
          );
        }
        break;
      }

      default:
        sendContent(res, HELP_TEXT);
    }
  } catch (err) {
    sendContent(
      res,
      `❌ **Error:** ${err.message}\n\nMake sure the PAM Python SDK is installed on the server.`
    );
  }

  sendDone(res);
  res.end();
}

module.exports = { handleChat };
