// command-parser.js — Parses user messages into PAM commands.

/**
 * Parse a raw chat message into a structured command.
 *
 * Supported forms:
 *   remember "some text"
 *   remember --fact subject predicate object
 *   remember --skill name description…
 *   recall
 *   recall --query "search terms"
 *   export
 *   import <url-or-json>
 *   status
 *   verify
 *   help
 */
function parseCommand(raw) {
  const text = raw.replace(/^@pam\s*/i, "").trim();

  if (!text || /^help$/i.test(text)) {
    return { command: "help" };
  }

  // remember --fact subject predicate object
  const factMatch = text.match(
    /^remember\s+--fact\s+(\S+)\s+(\S+)\s+(.+)$/i
  );
  if (factMatch) {
    return {
      command: "remember",
      text: `${factMatch[1]} ${factMatch[2]} ${factMatch[3]}`,
      opts: {
        kind: "semantic",
        subject: factMatch[1],
        predicate: factMatch[2],
        object_: factMatch[3].replace(/^["']|["']$/g, ""),
      },
    };
  }

  // remember --skill name description
  const skillMatch = text.match(/^remember\s+--skill\s+(\S+)\s+(.+)$/i);
  if (skillMatch) {
    return {
      command: "remember",
      text: skillMatch[2].replace(/^["']|["']$/g, ""),
      opts: {
        kind: "procedural",
        name: skillMatch[1],
      },
    };
  }

  // remember "text" or remember text
  const rememberMatch = text.match(/^remember\s+(.+)$/is);
  if (rememberMatch) {
    return {
      command: "remember",
      text: rememberMatch[1].replace(/^["']|["']$/g, "").trim(),
      opts: { kind: "episodic" },
    };
  }

  // recall --query "search terms"
  const recallQueryMatch = text.match(/^recall\s+--query\s+(.+)$/i);
  if (recallQueryMatch) {
    return {
      command: "recall",
      query: recallQueryMatch[1].replace(/^["']|["']$/g, "").trim(),
    };
  }

  if (/^recall$/i.test(text)) {
    return { command: "recall", query: "" };
  }

  if (/^export$/i.test(text)) {
    return { command: "export" };
  }

  const importMatch = text.match(/^import\s+(.+)$/i);
  if (importMatch) {
    return { command: "import", source: importMatch[1].trim() };
  }

  if (/^status$/i.test(text)) {
    return { command: "status" };
  }

  if (/^verify$/i.test(text)) {
    return { command: "verify" };
  }

  // Default: treat as episodic remember
  return {
    command: "remember",
    text: text,
    opts: { kind: "episodic" },
  };
}

module.exports = { parseCommand };
