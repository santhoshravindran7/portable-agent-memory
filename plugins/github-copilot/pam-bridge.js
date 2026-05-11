// pam-bridge.js — Executes PAM Python SDK commands via child_process.
// All memory operations are delegated to the Python SDK so end-users
// never need to pip-install anything; the server handles it.

const { execFile } = require("child_process");
const path = require("path");

const PYTHON = process.env.PAM_PYTHON || (process.platform === "win32" ? "python" : "python3");
const SDK_ROOT = path.resolve(__dirname, "..", "..", "sdk", "python");
const DATA_DIR = process.env.PAM_DATA_DIR || path.join(__dirname, "data");
const MAX_INPUT_SIZE = 100 * 1024; // 100KB — reject oversized inputs

/**
 * Run an inline Python script that imports the PAM SDK.
 * Returns { stdout, stderr } or throws on non-zero exit.
 */
function runPython(script) {
  return new Promise((resolve, reject) => {
    const child = execFile(
      PYTHON,
      ["-c", script],
      {
        env: { ...process.env, PYTHONPATH: SDK_ROOT },
        cwd: __dirname,
        timeout: 30_000,
        maxBuffer: 4 * 1024 * 1024,
      },
      (err, stdout, stderr) => {
        if (err) return reject(new Error(stderr || err.message));
        resolve({ stdout: stdout.trim(), stderr: stderr.trim() });
      }
    );
  });
}

/** Ensure the data directory exists. */
function ensureDataDir() {
  const fs = require("fs");
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

/** Path to the per-user artifact file. */
function artifactPath(userId) {
  const filePath = path.join(DATA_DIR, `${sanitize(userId)}.pam`);
  return safePath(filePath);
}

function safePath(filepath) {
  const resolved = path.resolve(filepath);
  const dataDir = path.resolve(DATA_DIR);
  if (!resolved.startsWith(dataDir)) {
    throw new Error(`Path traversal blocked: ${filepath}`);
  }
  return resolved;
}

function sanitize(s) {
  return String(s).replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 120);
}

// ── Commands ───────────────────────────────────────────────────────

async function remember(userId, text, opts = {}) {
  ensureDataDir();
  if (typeof text === "string" && text.length > MAX_INPUT_SIZE) {
    throw new Error(`Input too large: ${text.length} bytes exceeds ${MAX_INPUT_SIZE} byte limit`);
  }
  const optsStr = JSON.stringify(opts);
  if (optsStr.length > MAX_INPUT_SIZE) {
    throw new Error(`Options too large: ${optsStr.length} bytes exceeds ${MAX_INPUT_SIZE} byte limit`);
  }
  const filePath = artifactPath(userId);
  const escaped = JSON.stringify(text);
  const optsJson = JSON.stringify(opts);

  const script = `
import json, os, datetime
from pam import MemoryArtifact, SourceAgent, EpisodicEntry, SemanticEntry, ProceduralEntry
from pam.transport import FileTransport

fp = ${JSON.stringify(filePath)}
opts = json.loads(${JSON.stringify(optsJson)})
transport = FileTransport()

if os.path.exists(fp):
    artifact = transport.load(fp)
else:
    artifact = MemoryArtifact(
        source_agent=SourceAgent(
            name="github-copilot-pam",
            model_family="copilot",
            runtime="github-copilot-extension",
            version="0.1.0",
        )
    )

text = json.loads(${JSON.stringify(escaped)})
kind = opts.get("kind", "episodic")

if kind == "semantic":
    entry = SemanticEntry(
        subject=opts.get("subject", ""),
        predicate=opts.get("predicate", ""),
        object=opts.get("object_", ""),
        confidence=float(opts.get("confidence", 0.8)),
    )
    artifact.semantic.append(entry)
elif kind == "procedural":
    entry = ProceduralEntry(
        name=opts.get("name", "skill"),
        description=text,
        language="natural",
    )
    artifact.procedural.append(entry)
else:
    entry = EpisodicEntry(
        observation=text,
        actor="user",
        salience=float(opts.get("salience", 0.7)),
    )
    artifact.episodic.append(entry)

artifact.root_hash = ""
transport.save(artifact, fp)
print(json.dumps({"ok": True, "kind": kind, "id": entry.id}))
`;
  const { stdout } = await runPython(script);
  return JSON.parse(stdout);
}

async function recall(userId, query = "") {
  ensureDataDir();
  if (typeof query === "string" && query.length > MAX_INPUT_SIZE) {
    throw new Error(`Query too large: ${query.length} bytes exceeds ${MAX_INPUT_SIZE} byte limit`);
  }
  const filePath = artifactPath(userId);
  const escaped = JSON.stringify(query);

  const script = `
import json, os
from pam import MemoryArtifact
from pam.transport import FileTransport
from pam.rehydration import RehydrationEngine

fp = ${JSON.stringify(filePath)}
query = json.loads(${JSON.stringify(escaped)})

if not os.path.exists(fp):
    print(json.dumps({"memories": [], "prompt": "No memories stored yet."}))
    raise SystemExit(0)

transport = FileTransport()
artifact = transport.load(fp)

engine = RehydrationEngine()
prompt = engine.rehydrate(artifact, task=query)

memories = []
for e in artifact.episodic:
    memories.append({"type": "episodic", "observation": e.observation, "created": e.created_at, "id": e.id})
for e in artifact.semantic:
    memories.append({"type": "semantic", "subject": e.subject, "predicate": e.predicate, "object": e.object, "id": e.id})
for e in artifact.procedural:
    memories.append({"type": "procedural", "name": e.name, "description": e.description, "id": e.id})
for e in artifact.working:
    memories.append({"type": "working", "goals": e.goals, "scratch": e.scratch, "id": e.id})

print(json.dumps({"memories": memories, "prompt": prompt}))
`;
  const { stdout } = await runPython(script);
  return JSON.parse(stdout);
}

async function exportArtifact(userId) {
  ensureDataDir();
  const filePath = artifactPath(userId);

  const script = `
import json, os
from pam.transport import FileTransport

fp = ${JSON.stringify(filePath)}
if not os.path.exists(fp):
    print(json.dumps({"error": "No memories to export."}))
    raise SystemExit(0)

transport = FileTransport()
artifact = transport.load(fp)
artifact.root_hash = ""
artifact.root_hash = artifact.compute_root_hash()
print(artifact.to_json(pretty=True))
`;
  const { stdout } = await runPython(script);
  return stdout;
}

async function importArtifact(userId, jsonContent) {
  ensureDataDir();
  if (typeof jsonContent === "string" && jsonContent.length > MAX_INPUT_SIZE) {
    throw new Error(`Import content too large: ${jsonContent.length} bytes exceeds ${MAX_INPUT_SIZE} byte limit`);
  }
  // Validate JSON before passing to Python
  try {
    JSON.parse(jsonContent);
  } catch (_) {
    throw new Error("Invalid JSON: importArtifact requires valid JSON content");
  }
  const filePath = artifactPath(userId);
  const escaped = JSON.stringify(jsonContent);

  const script = `
import json
from pam import MemoryArtifact
from pam.transport import FileTransport

raw = json.loads(${JSON.stringify(escaped)})
artifact = MemoryArtifact.from_json(raw)
transport = FileTransport()
transport.save(artifact, ${JSON.stringify(filePath)})

count = len(artifact.episodic) + len(artifact.semantic) + len(artifact.procedural) + len(artifact.working)
print(json.dumps({"ok": True, "entries": count}))
`;
  const { stdout } = await runPython(script);
  return JSON.parse(stdout);
}

async function status(userId) {
  ensureDataDir();
  const filePath = artifactPath(userId);

  const script = `
import json, os
from pam.transport import FileTransport

fp = ${JSON.stringify(filePath)}
if not os.path.exists(fp):
    print(json.dumps({"exists": False}))
    raise SystemExit(0)

transport = FileTransport()
artifact = transport.load(fp)

stats = {
    "exists": True,
    "episodic": len(artifact.episodic),
    "semantic": len(artifact.semantic),
    "procedural": len(artifact.procedural),
    "working": len(artifact.working),
    "identity": len(artifact.identity),
    "total": len(artifact.episodic) + len(artifact.semantic) + len(artifact.procedural) + len(artifact.working) + len(artifact.identity),
    "created_at": artifact.created_at,
    "agent": artifact.source_agent.name if artifact.source_agent else "unknown",
    "has_root_hash": bool(artifact.root_hash),
    "has_signature": bool(artifact.signature),
}
print(json.dumps(stats))
`;
  const { stdout } = await runPython(script);
  return JSON.parse(stdout);
}

async function verify(userId) {
  ensureDataDir();
  const filePath = artifactPath(userId);

  const script = `
import json, os
from pam.transport import FileTransport
from pam.provenance import ProvenanceGraph

fp = ${JSON.stringify(filePath)}
if not os.path.exists(fp):
    print(json.dumps({"error": "No memories to verify."}))
    raise SystemExit(0)

transport = FileTransport()
artifact = transport.load(fp)

# Recompute root hash for comparison
artifact.root_hash = artifact.compute_root_hash()

# Verify individual entry integrity
all_entries = artifact.episodic + artifact.semantic + artifact.procedural + artifact.working + artifact.identity
graph = ProvenanceGraph(all_entries)
valid, invalid_ids = graph.verify_all()

# Verify artifact-level integrity
artifact_ok = artifact.verify_integrity()

print(json.dumps({
    "artifact_integrity": artifact_ok,
    "provenance_valid": valid,
    "invalid_entry_ids": invalid_ids,
    "total_entries": len(all_entries),
    "root_hash": artifact.root_hash,
}))
`;
  const { stdout } = await runPython(script);
  return JSON.parse(stdout);
}

module.exports = { remember, recall, exportArtifact, importArtifact, status, verify };
