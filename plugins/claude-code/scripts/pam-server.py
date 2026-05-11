#!/usr/bin/env python3
"""PAM MCP Server — exposes Portable Agent Memory as MCP tools over stdin/stdout JSON-RPC.

Auto-installs the PAM SDK on first run if not already available.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Auto-install PAM SDK if missing
# ---------------------------------------------------------------------------

def _ensure_pam_sdk() -> None:
    """Install pam-sdk if not importable."""
    try:
        import pam  # noqa: F401
        return
    except ImportError:
        pass

    # Try local SDK path first (development), then GitHub
    script_dir = Path(__file__).resolve().parent
    local_sdk = script_dir.parent.parent.parent / "sdk" / "python"
    if (local_sdk / "pyproject.toml").exists():
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-e", str(local_sdk)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
    else:
        # NOTE: In production, pin to a tagged release or PyPI package with hash verification.
        subprocess.check_call(
            [
                sys.executable, "-m", "pip", "install", "-q",
                "pam-sdk @ git+https://github.com/santhoshravindran7/portable-agent-memory.git@main#subdirectory=sdk/python",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )


_ensure_pam_sdk()

from pam import (  # noqa: E402
    EpisodicEntry,
    MemoryArtifact,
    ProceduralEntry,
    RehydrationEngine,
    SemanticEntry,
    SourceAgent,
    WorkingEntry,
)
from pam.transport import FileTransport  # noqa: E402

# ---------------------------------------------------------------------------
# Memory store (file-backed singleton)
# ---------------------------------------------------------------------------

PAM_DIR = Path(os.environ.get("PAM_HOME", Path.home() / ".pam"))
PAM_STORE = PAM_DIR / "memory.pam"
SOURCE_AGENT = SourceAgent(
    name="claude-code",
    model_family="claude",
    runtime="claude-code-plugin",
    version="0.1.0",
)


def _load_artifact() -> MemoryArtifact:
    """Load the memory artifact from disk, or create a fresh one."""
    if PAM_STORE.exists():
        try:
            return FileTransport.load(str(PAM_STORE))
        except Exception:
            pass
    return MemoryArtifact(source_agent=SOURCE_AGENT)


def _save_artifact(artifact: MemoryArtifact) -> None:
    """Persist the artifact to disk."""
    PAM_DIR.mkdir(parents=True, exist_ok=True)
    artifact.root_hash = artifact.compute_root_hash()
    # Sign if key exists
    key_path = PAM_DIR / "signing.key"
    if key_path.exists():
        try:
            artifact.sign(key_path.read_bytes()[:32])
        except Exception:
            pass
    FileTransport.save(artifact, str(PAM_STORE))


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_pam_remember(text: str, type: str = "semantic", metadata: dict | None = None) -> dict:
    """Store a memory entry."""
    artifact = _load_artifact()
    now = datetime.now(timezone.utc).isoformat()
    tags = (metadata or {}).get("tags", [])

    if type == "episodic":
        entry = EpisodicEntry(
            timestamp=now,
            actor="user",
            observation=text,
            salience=float((metadata or {}).get("salience", 0.7)),
            event_type=(metadata or {}).get("event_type", "observation"),
            tags=tags,
        )
        artifact.episodic.append(entry)
    elif type == "procedural":
        entry = ProceduralEntry(
            name=(metadata or {}).get("name", text[:60]),
            description=text,
            body=(metadata or {}).get("body", ""),
            language=(metadata or {}).get("language", "natural"),
            tags=tags,
        )
        artifact.procedural.append(entry)
    elif type == "working":
        goals = [g.strip() for g in text.split(";") if g.strip()] if ";" in text else [text]
        entry = WorkingEntry(
            goals=goals,
            scratch=(metadata or {}).get("scratch", ""),
            tags=tags,
        )
        artifact.working.append(entry)
    else:  # semantic (default)
        parts = text.split(" ", 2)
        if len(parts) >= 3:
            subject, predicate, obj = parts[0], parts[1], " ".join(parts[2:])
        else:
            subject, predicate, obj = text, "is", text
        entry = SemanticEntry(
            subject=subject,
            predicate=predicate,
            object=obj,
            confidence=float((metadata or {}).get("confidence", 0.8)),
            tags=tags,
        )
        artifact.semantic.append(entry)

    _save_artifact(artifact)
    return {
        "stored": True,
        "type": type,
        "id": entry.id,
        "message": f"Remembered as {type}: {text[:80]}{'...' if len(text) > 80 else ''}",
    }


def tool_pam_recall(query: str = "", type: str = "all") -> dict:
    """Search and retrieve memories."""
    artifact = _load_artifact()
    results: dict[str, list[dict]] = {"episodic": [], "semantic": [], "procedural": [], "working": []}

    def _matches(text: str) -> bool:
        if not query:
            return True
        return query.lower() in text.lower()

    if type in ("all", "episodic"):
        for e in artifact.episodic:
            if _matches(e.observation) or _matches(" ".join(e.tags)):
                results["episodic"].append({
                    "id": e.id, "timestamp": e.timestamp,
                    "observation": e.observation, "salience": e.salience,
                    "tags": e.tags,
                })

    if type in ("all", "semantic"):
        for e in artifact.semantic:
            text = f"{e.subject} {e.predicate} {e.object}"
            if _matches(text) or _matches(" ".join(e.tags)):
                results["semantic"].append({
                    "id": e.id, "subject": e.subject, "predicate": e.predicate,
                    "object": e.object, "confidence": e.confidence, "tags": e.tags,
                })

    if type in ("all", "procedural"):
        for e in artifact.procedural:
            if _matches(e.name) or _matches(e.description) or _matches(" ".join(e.tags)):
                results["procedural"].append({
                    "id": e.id, "name": e.name,
                    "description": e.description, "tags": e.tags,
                })

    if type in ("all", "working"):
        for e in artifact.working:
            if _matches(" ".join(e.goals)) or _matches(e.scratch) or _matches(" ".join(e.tags)):
                results["working"].append({
                    "id": e.id, "goals": e.goals,
                    "scratch": e.scratch, "tags": e.tags,
                })

    # Filter out empty categories
    results = {k: v for k, v in results.items() if v}
    total = sum(len(v) for v in results.values())
    return {"total": total, "query": query, "results": results}


def _safe_path(filepath: str) -> Path:
    """Resolve path and ensure it's within allowed directories."""
    resolved = Path(filepath).resolve()
    allowed_dirs = [Path.home() / ".pam", Path.cwd()]
    if not any(str(resolved).startswith(str(d.resolve())) for d in allowed_dirs):
        raise ValueError(f"Path {filepath} is outside allowed directories (~/.pam/ or current directory)")
    return resolved


def _validate_tool_args(tool_name: str, tool_args: dict, tools_list: list) -> bool:
    """Validate args match the declared inputSchema."""
    tool_def = next((t for t in tools_list if t["name"] == tool_name), None)
    if not tool_def:
        return False
    schema = tool_def.get("inputSchema", {})
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    # Check no unexpected args
    for key in tool_args:
        if key not in properties:
            raise ValueError(f"Unexpected argument: {key}")
    # Check required args
    for req in required:
        if req not in tool_args:
            raise ValueError(f"Missing required argument: {req}")
    return True


def tool_pam_export(filepath: str = "") -> dict:
    """Export memories to a .pam file."""
    artifact = _load_artifact()
    if not filepath:
        filepath = "memory-export.pam"
    if not filepath.endswith(".pam"):
        filepath += ".pam"
    path = _safe_path(filepath)
    _save_artifact(artifact)
    FileTransport.save(artifact, str(path))
    total = len(artifact.all_entries())
    size = path.stat().st_size
    return {
        "exported": True,
        "filepath": str(path),
        "total_memories": total,
        "file_size_bytes": size,
        "message": f"Exported {total} memories to {path} ({size} bytes)",
    }


def tool_pam_import(filepath: str) -> dict:
    """Import memories from a .pam file."""
    path = _safe_path(filepath)
    if not path.exists():
        return {"error": f"File not found: {path}"}
    incoming = FileTransport.load(str(path))
    artifact = _load_artifact()

    # Merge entries, deduplicating by ID
    existing_ids = {e.id for e in artifact.all_entries()}
    counts = {"episodic": 0, "semantic": 0, "procedural": 0, "working": 0}

    for e in incoming.episodic:
        if e.id not in existing_ids:
            artifact.episodic.append(e)
            counts["episodic"] += 1
    for e in incoming.semantic:
        if e.id not in existing_ids:
            artifact.semantic.append(e)
            counts["semantic"] += 1
    for e in incoming.procedural:
        if e.id not in existing_ids:
            artifact.procedural.append(e)
            counts["procedural"] += 1
    for e in incoming.working:
        if e.id not in existing_ids:
            artifact.working.append(e)
            counts["working"] += 1

    _save_artifact(artifact)
    total = sum(counts.values())
    return {
        "imported": True,
        "filepath": str(path),
        "new_memories": total,
        "counts": counts,
        "integrity_verified": artifact.verify_integrity(),
        "message": f"Imported {total} new memories from {path}",
    }


def tool_pam_verify() -> dict:
    """Verify cryptographic integrity of the memory store."""
    artifact = _load_artifact()
    integrity_ok = artifact.verify_integrity()

    result: dict = {
        "integrity": integrity_ok,
        "root_hash": artifact.root_hash,
        "total_entries": len(artifact.all_entries()),
    }

    if artifact.signature:
        pub_key_path = PAM_DIR / "signing.pub"
        if pub_key_path.exists():
            sig_ok = artifact.verify_signature(pub_key_path.read_bytes()[:32])
            result["signature_verified"] = sig_ok
        else:
            result["signature_verified"] = None
            result["note"] = "Signed but no public key found for verification"
    else:
        result["signature_verified"] = None
        result["note"] = "Artifact is not signed"

    return result


def tool_pam_status() -> dict:
    """Show memory statistics."""
    artifact = _load_artifact()
    store_size = PAM_STORE.stat().st_size if PAM_STORE.exists() else 0
    return {
        "storage_path": str(PAM_STORE),
        "file_size_bytes": store_size,
        "counts": {
            "episodic": len(artifact.episodic),
            "semantic": len(artifact.semantic),
            "procedural": len(artifact.procedural),
            "working": len(artifact.working),
            "total": len(artifact.all_entries()),
        },
        "root_hash": artifact.root_hash,
        "signed": bool(artifact.signature),
        "created_at": artifact.created_at,
        "pam_version": artifact.pam_version,
    }


def tool_pam_rehydrate(task: str = "") -> dict:
    """Generate a context prompt from memories, optionally filtered by task relevance."""
    artifact = _load_artifact()
    engine = RehydrationEngine()
    context = engine.rehydrate(artifact, task=task)
    return {
        "context": context,
        "task": task,
        "entries_used": len(artifact.all_entries()),
    }


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = {
    "pam_remember": {
        "fn": tool_pam_remember,
        "description": "Store a memory. Types: episodic (events), semantic (facts/preferences), procedural (workflows), working (current context).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The text to remember"},
                "type": {
                    "type": "string",
                    "enum": ["episodic", "semantic", "procedural", "working"],
                    "default": "semantic",
                    "description": "Memory type",
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata (tags, salience, confidence, etc.)",
                    "default": {},
                },
            },
            "required": ["text"],
        },
    },
    "pam_recall": {
        "fn": tool_pam_recall,
        "description": "Search and retrieve memories. Empty query returns all memories.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "default": "", "description": "Search query (substring match)"},
                "type": {
                    "type": "string",
                    "enum": ["all", "episodic", "semantic", "procedural", "working"],
                    "default": "all",
                    "description": "Filter by memory type",
                },
            },
        },
    },
    "pam_export": {
        "fn": tool_pam_export,
        "description": "Export all memories to a portable .pam file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "default": "", "description": "Output file path (defaults to memory-export.pam)"},
            },
        },
    },
    "pam_import": {
        "fn": tool_pam_import,
        "description": "Import memories from a .pam file, deduplicating by content hash.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to .pam file to import"},
            },
            "required": ["filepath"],
        },
    },
    "pam_verify": {
        "fn": tool_pam_verify,
        "description": "Verify cryptographic integrity (BLAKE3 hashes, Ed25519 signatures) of the memory store.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "pam_status": {
        "fn": tool_pam_status,
        "description": "Show memory store statistics: counts by type, storage info, integrity status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "pam_rehydrate": {
        "fn": tool_pam_rehydrate,
        "description": "Generate a context prompt from memories, ranked by relevance to an optional task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "default": "", "description": "Optional task description for relevance ranking"},
            },
        },
    },
}

# ---------------------------------------------------------------------------
# MCP JSON-RPC server (stdin/stdout)
# ---------------------------------------------------------------------------

def _write_response(response: dict) -> None:
    """Write a JSON-RPC response to stdout."""
    msg = json.dumps(response)
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def _handle_request(request: dict) -> dict:
    """Handle a single JSON-RPC request and return a response."""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "portable-agent-memory",
                    "version": "0.1.0",
                },
            },
        }

    if method == "notifications/initialized":
        return None  # No response for notifications

    if method == "tools/list":
        tool_list = []
        for name, spec in TOOLS.items():
            tool_list.append({
                "name": name,
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
            })
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tool_list},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {tool_name}"})}],
                    "isError": True,
                },
            }

        try:
            # Validate tool arguments against declared schema
            tool_list = [
                {"name": n, "inputSchema": s["inputSchema"]}
                for n, s in TOOLS.items()
            ]
            _validate_tool_args(tool_name, tool_args, tool_list)

            result = TOOLS[tool_name]["fn"](**tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                    "isError": False,
                },
            }
        except Exception as exc:
            error_msg = str(exc)
            # Strip home directory path from error messages
            home = str(Path.home())
            error_msg = error_msg.replace(home, "~")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps({"error": error_msg})}],
                    "isError": True,
                },
            }

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    """Run the MCP server, reading JSON-RPC messages from stdin."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            _write_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            })
            continue

        response = _handle_request(request)
        if response is not None:
            _write_response(response)


if __name__ == "__main__":
    main()
