"""
Portable Agent Memory CLI — Zero-code memory management for AI agents.

Usage:
    pam remember "User prefers dark mode and TypeScript"
    pam remember --fact "project" "uses" "Next.js 14"
    pam remember --skill "deploy" "Deploy to production" "kubectl apply -f deploy.yaml"
    pam recall
    pam export my_memory.pam
    pam import colleague_memory.pam
    pam inspect my_memory.pam
    pam verify my_memory.pam
    pam status
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pam.models.artifact import MemoryArtifact, SourceAgent
from pam.models.entries import (
    EpisodicEntry,
    IdentityEntry,
    ProceduralEntry,
    SemanticEntry,
    WorkingEntry,
)
from pam.rehydration.engine import RehydrationEngine
from pam.transport.file import FileTransport

# --- Paths ---
PAM_DIR = Path.home() / ".pam"
KEYS_DIR = PAM_DIR / "keys"
MEMORIES_DIR = PAM_DIR / "memories"
CURRENT_ARTIFACT = MEMORIES_DIR / "current.pam"


def _ensure_dirs() -> None:
    MEMORIES_DIR.mkdir(parents=True, exist_ok=True)
    KEYS_DIR.mkdir(parents=True, exist_ok=True)


def _get_or_create_key() -> Ed25519PrivateKey:
    import os

    _ensure_dirs()
    key_path = KEYS_DIR / "agent.key"
    if key_path.exists():
        # Warn if key file permissions are too permissive (non-Windows)
        if sys.platform != "win32":
            mode = key_path.stat().st_mode & 0o777
            if mode & 0o077:  # group or other has access
                print(
                    f"  ⚠️  WARNING: Key file {key_path} has permissions {oct(mode)}"
                    " — should be 0600",
                    file=sys.stderr,
                )
        return Ed25519PrivateKey.from_private_bytes(key_path.read_bytes())
    key = Ed25519PrivateKey.generate()
    key_path.write_bytes(key.private_bytes_raw())
    if sys.platform != "win32":
        os.chmod(key_path, 0o600)
    pub_path = KEYS_DIR / "agent.pub"
    pub_path.write_bytes(key.public_key().public_bytes_raw())
    print(f"  Generated new signing key at {key_path}")
    return key


def _load_or_create() -> MemoryArtifact:
    _ensure_dirs()
    if CURRENT_ARTIFACT.exists():
        return FileTransport.load(str(CURRENT_ARTIFACT))
    return MemoryArtifact(
        source_agent=SourceAgent(
            name="pam-cli",
            model_family="user",
            runtime="pam-cli",
            version="0.1.0",
        )
    )


def _save(artifact: MemoryArtifact) -> None:
    key = _get_or_create_key()
    artifact.root_hash = ""  # Reset so save() recomputes
    artifact.sign(key.private_bytes_raw())
    FileTransport.save(artifact, str(CURRENT_ARTIFACT))


# --- Commands ---


def cmd_remember(args: argparse.Namespace) -> None:
    """Remember something — an observation, fact, or skill."""
    artifact = _load_or_create()

    if args.fact:
        if len(args.fact) != 3:
            print("Error: --fact requires exactly 3 values: subject predicate object")
            print('  Example: pam remember --fact "project" "uses" "Next.js"')
            sys.exit(1)
        subject, predicate, obj = args.fact
        artifact.semantic.append(
            SemanticEntry(subject=subject, predicate=predicate, object=obj, confidence=0.9)
        )
        _save(artifact)
        print(f"  Learned: {subject} {predicate} {obj}")

    elif args.skill:
        if len(args.skill) < 2:
            print("Error: --skill requires at least name and description")
            sys.exit(1)
        name = args.skill[0]
        desc = args.skill[1]
        body = args.skill[2] if len(args.skill) > 2 else ""
        artifact.procedural.append(
            ProceduralEntry(name=name, description=desc, body=body, language="natural")
        )
        _save(artifact)
        print(f"  Skill saved: {name} — {desc}")

    elif args.preference:
        pref_dict = {}
        for item in args.preference:
            if "=" in item:
                k, v = item.split("=", 1)
                pref_dict[k.strip()] = v.strip()
            else:
                pref_dict[item] = True
        persona = getattr(args, "persona", "") or ""
        policies = getattr(args, "policies", []) or []
        artifact.identity.append(
            IdentityEntry(preferences=pref_dict, persona=persona, policies=policies)
        )
        _save(artifact)
        print(f"  Preference saved: {pref_dict}")
        if persona:
            print(f"  Persona: {persona}")
        if policies:
            print(f"  Policies: {', '.join(policies)}")

    elif args.working:
        goals = args.working
        scratch = getattr(args, "scratch", "")
        pending = getattr(args, "pending", []) or []
        pending_actions = [{"action": a} for a in pending] if pending else []
        artifact.working.append(
            WorkingEntry(goals=goals, scratch=scratch, subgoals=[], pending_actions=pending_actions)
        )
        _save(artifact)
        print(f"  Working memory saved: {len(goals)} goal(s)")
        if pending_actions:
            print(f"  Pending actions: {len(pending_actions)}")

    elif args.text:
        observation = " ".join(args.text)
        artifact.episodic.append(
            EpisodicEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor="user",
                observation=observation,
                salience=0.8,
                event_type="observation",
            )
        )
        _save(artifact)
        print(f"  Remembered: {observation}")

    else:
        print("Error: provide text to remember, or use --fact/--skill/--preference/--working")
        sys.exit(1)

    total = len(artifact.all_entries())
    print(f"  Total memories: {total}")


def cmd_recall(args: argparse.Namespace) -> None:
    """Show what's in memory."""
    if not CURRENT_ARTIFACT.exists():
        if getattr(args, "json", False):
            print("[]")
        else:
            print("  No memories yet. Use 'pam remember' to start.")
        return

    artifact = FileTransport.load(str(CURRENT_ARTIFACT))
    entries = artifact.all_entries()

    # Filter by search query if provided
    if args.search:
        query = args.search.lower()
        filtered = []
        for e in entries:
            text = ""
            if hasattr(e, "observation"):
                text = e.observation
            elif hasattr(e, "subject"):
                text = f"{e.subject} {e.predicate} {e.object}"
            elif hasattr(e, "name"):
                text = f"{e.name} {e.description} {e.body}"
            elif hasattr(e, "persona"):
                text = f"{e.persona} {e.preferences} {' '.join(e.policies)} {e.custom_instructions}"
            elif hasattr(e, "goals"):
                text = f"{' '.join(e.goals)} {e.scratch}"
            if query in text.lower():
                filtered.append(e)
        entries = filtered

    # JSON output for programmatic access (VS Code extension, etc.)
    if getattr(args, "json", False):
        result = []
        for e in entries:
            item: dict = {"id": str(e.id)}
            if hasattr(e, "observation"):
                item["type"] = "episodic"
                item["content"] = e.observation
                item["timestamp"] = e.timestamp
            elif hasattr(e, "subject"):
                item["type"] = "semantic"
                item["content"] = f"{e.subject} {e.predicate} {e.object}"
                item["subject"] = e.subject
                item["predicate"] = e.predicate
                item["object"] = e.object
            elif hasattr(e, "name"):
                item["type"] = "procedural"
                item["content"] = e.description
                item["name"] = e.name
                item["description"] = e.description
                item["body"] = e.body
            elif hasattr(e, "persona"):
                item["type"] = "identity"
                item["content"] = str(e.preferences) if e.preferences else e.persona
                item["preferences"] = e.preferences
                item["persona"] = e.persona
                item["policies"] = e.policies
            elif hasattr(e, "goals"):
                item["type"] = "working"
                item["content"] = ", ".join(e.goals)
                item["goals"] = e.goals
                item["scratch"] = e.scratch
            result.append(item)
        print(json.dumps(result))
        return

    total = len(artifact.all_entries())

    print(f"\n  Portable Agent Memory — {total} entries")
    print(f"  Source: {artifact.source_agent.name} ({artifact.source_agent.model_family})")
    print(f"  Signed: {'Yes' if artifact.signature else 'No'}")
    if args.search:
        print(f"  Search: '{args.search}' — {len(entries)} matches")
    print()

    if artifact.episodic:
        eps = [e for e in entries if hasattr(e, "observation")] if args.search else artifact.episodic
        if eps:
            print(f"  Episodes ({len(eps)}):")
            for e in eps[-(args.limit or 10) :]:
                ts = e.timestamp[:10] if e.timestamp else "?"
                print(f"    [{ts}] {e.observation[:100]}")
            print()

    if artifact.semantic:
        sems = [e for e in entries if hasattr(e, "subject")] if args.search else artifact.semantic
        if sems:
            print(f"  Facts ({len(sems)}):")
            for s in sems:
                print(f"    {s.subject} {s.predicate} {s.object}")
            print()

    if artifact.procedural:
        procs = [e for e in entries if hasattr(e, "name") and hasattr(e, "description")] if args.search else artifact.procedural
        if procs:
            print(f"  Skills ({len(procs)}):")
            for p in procs:
                print(f"    {p.name}: {p.description}")
            print()

    if artifact.identity:
        ids = [e for e in entries if hasattr(e, "persona")] if args.search else artifact.identity
        if ids:
            print(f"  Identity ({len(ids)}):")
            for i in ids:
                if i.persona:
                    print(f"    Persona: {i.persona}")
                if i.preferences:
                    print(f"    Preferences: {i.preferences}")
                if i.policies:
                    print(f"    Policies: {', '.join(i.policies)}")
            print()

    if artifact.working:
        wrk = [e for e in entries if hasattr(e, "goals")] if args.search else artifact.working
        if wrk:
            print(f"  Working State ({len(wrk)}):")
            for w in wrk:
                if w.goals:
                    print(f"    Goals: {', '.join(w.goals)}")
            print()


def cmd_export(args: argparse.Namespace) -> None:
    """Export memory to a portable .pam file."""
    if not CURRENT_ARTIFACT.exists():
        print("  No memories to export.")
        return

    artifact = FileTransport.load(str(CURRENT_ARTIFACT))
    output = args.output or "my_memory.pam"

    key = _get_or_create_key()
    artifact.sign(key.private_bytes_raw())
    FileTransport.save(artifact, output)

    total = len(artifact.all_entries())
    size = Path(output).stat().st_size
    print(f"  Exported {total} entries to {output} ({size:,} bytes)")
    print(f"  This file can be imported by any Portable Agent Memory-compatible agent.")
    print(f"  It's human-readable JSON — open it in any text editor to inspect.")


def cmd_import(args: argparse.Namespace) -> None:
    """Import memory from a .pam file."""
    path = Path(args.file)
    if not path.exists():
        print(f"  File not found: {path}")
        sys.exit(1)

    incoming = FileTransport.load(str(path))

    # Verify integrity
    if incoming.root_hash and not incoming.verify_integrity():
        print("  WARNING: Integrity check FAILED. This file may have been tampered with.")
        if not args.force:
            print("  Use --force to import anyway.")
            sys.exit(1)

    print(f"  Source: {incoming.source_agent.name} ({incoming.source_agent.model_family})")
    print(f"  Entries: {len(incoming.all_entries())}")
    print(f"  Integrity: {'PASS' if incoming.verify_integrity() else 'FAIL'}")

    # Merge into local memory
    local = _load_or_create()
    existing_ids = {e.id for e in local.all_entries()}
    added = 0

    for entry in incoming.episodic:
        if entry.id not in existing_ids:
            local.episodic.append(entry)
            added += 1
    for entry in incoming.semantic:
        if entry.id not in existing_ids:
            local.semantic.append(entry)
            added += 1
    for entry in incoming.procedural:
        if entry.id not in existing_ids:
            local.procedural.append(entry)
            added += 1
    for entry in incoming.identity:
        if entry.id not in existing_ids:
            local.identity.append(entry)
            added += 1
    for entry in incoming.working:
        if entry.id not in existing_ids:
            local.working.append(entry)
            added += 1

    _save(local)
    total = len(local.all_entries())
    print(f"  Imported {added} new entries (skipped {len(incoming.all_entries()) - added} duplicates)")
    print(f"  Total memories: {total}")

    # Show rehydrated summary
    if args.task:
        engine = RehydrationEngine()
        prompt = engine.rehydrate(local, task=args.task)
        print(f"\n  Rehydrated context for task '{args.task}':")
        print(f"  {'—' * 50}")
        for line in prompt.split("\n"):
            print(f"  {line}")


def cmd_inspect(args: argparse.Namespace) -> None:
    """Inspect a .pam file without importing it."""
    path = Path(args.file)
    if not path.exists():
        print(f"  File not found: {path}")
        sys.exit(1)

    artifact = FileTransport.load(str(path))
    total = len(artifact.all_entries())

    print(f"\n  File: {path}")
    print(f"  Size: {path.stat().st_size:,} bytes")
    print(f"  Format: {'JSON' if path.suffix == '.pam' else 'CBOR'}")
    print()
    print(f"  Source Agent: {artifact.source_agent.name}")
    print(f"  Model:        {artifact.source_agent.model_family}")
    print(f"  Runtime:      {artifact.source_agent.runtime}")
    print(f"  Version:      {artifact.pam_version}")
    print(f"  Created:      {artifact.created_at}")
    print()
    print(f"  Entries:      {total} total")
    print(f"    Episodic:   {len(artifact.episodic)}")
    print(f"    Semantic:   {len(artifact.semantic)}")
    print(f"    Procedural: {len(artifact.procedural)}")
    print(f"    Working:    {len(artifact.working)}")
    print(f"    Identity:   {len(artifact.identity)}")
    print()
    print(f"  Root Hash:    {artifact.root_hash[:50] + '...' if artifact.root_hash else 'Not computed'}")
    print(f"  Signature:    {'Present' if artifact.signature else 'None'}")
    print(f"  Integrity:    {'PASS' if artifact.verify_integrity() else 'FAIL'}")


def cmd_verify(args: argparse.Namespace) -> None:
    """Verify integrity of a .pam file."""
    path = Path(args.file) if args.file else CURRENT_ARTIFACT
    if not path.exists():
        if args.file:
            print(f"  File not found: {path}")
        else:
            print("  No memories to verify.")
        sys.exit(1)

    artifact = FileTransport.load(str(path))
    integrity = artifact.verify_integrity()

    print(f"  File:      {path}")
    print(f"  Integrity: {'PASS' if integrity else 'FAIL'}")

    if args.pubkey:
        pub_bytes = Path(args.pubkey).read_bytes()
        sig_ok = artifact.verify_signature(pub_bytes)
        print(f"  Signature: {'PASS' if sig_ok else 'FAIL'}")

    if not integrity:
        print("\n  WARNING: This artifact may have been tampered with!")
        print("  Content hashes do not match. Do NOT trust this memory.")
        sys.exit(1)


def cmd_status(args: argparse.Namespace) -> None:
    """Show Portable Agent Memory status."""
    if getattr(args, "json", False):
        # JSON output for programmatic access (VS Code extension, etc.)
        result = {"total": 0, "episodic": 0, "semantic": 0, "procedural": 0, "working": 0, "identity": 0}
        if CURRENT_ARTIFACT.exists():
            artifact = FileTransport.load(str(CURRENT_ARTIFACT))
            result = {
                "total": len(artifact.all_entries()),
                "episodic": len(artifact.episodic),
                "semantic": len(artifact.semantic),
                "procedural": len(artifact.procedural),
                "working": len(artifact.working),
                "identity": len(artifact.identity),
            }
        print(json.dumps(result))
        return

    print(f"\n  Portable Agent Memory CLI v0.1.0")
    print(f"  Storage: {PAM_DIR}")
    print(f"  Keys:    {KEYS_DIR}")
    print()

    if CURRENT_ARTIFACT.exists():
        artifact = FileTransport.load(str(CURRENT_ARTIFACT))
        total = len(artifact.all_entries())
        size = CURRENT_ARTIFACT.stat().st_size
        print(f"  Current memory: {total} entries ({size:,} bytes)")
        print(f"  Episodic: {len(artifact.episodic)} | Semantic: {len(artifact.semantic)} | "
              f"Procedural: {len(artifact.procedural)} | Working: {len(artifact.working)} | "
              f"Identity: {len(artifact.identity)}")
        print(f"  Signed: {'Yes' if artifact.signature else 'No'}")
        print(f"  Integrity: {'PASS' if artifact.verify_integrity() else 'FAIL'}")
    else:
        print("  No memories stored yet.")
        print("  Get started: pam remember 'Your first memory'")

    key_path = KEYS_DIR / "agent.key"
    print(f"\n  Signing key: {'Present' if key_path.exists() else 'Not yet generated (auto-creates on first use)'}")
    print()


def cmd_clear(args: argparse.Namespace) -> None:
    """Clear all stored memories."""
    if not CURRENT_ARTIFACT.exists():
        print("  No memories to clear.")
        return

    if not args.force:
        print("  This will delete all stored memories. Use --force to confirm.")
        return

    CURRENT_ARTIFACT.unlink()
    print("  All memories cleared.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pam",
        description="Portable Agent Memory — Manage AI agent memory from the command line",
    )
    parser.add_argument("--version", action="version", version="pam 0.1.0")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # remember
    p_remember = subparsers.add_parser("remember", help="Remember something")
    p_remember.add_argument("text", nargs="*", help="What to remember")
    p_remember.add_argument("--fact", nargs=3, metavar=("SUBJECT", "PREDICATE", "OBJECT"),
                            help="Remember a fact triple")
    p_remember.add_argument("--skill", nargs="+", metavar="VALUE",
                            help="Remember a skill: name description [body]")
    p_remember.add_argument("--preference", nargs="+", metavar="KEY=VALUE",
                            help="Remember preferences (key=value pairs)")
    p_remember.add_argument("--working", nargs="+", metavar="GOAL",
                            help="Remember working-memory goals")
    p_remember.add_argument("--scratch", default="", help="Scratch-pad notes for working memory")
    p_remember.add_argument("--pending", nargs="+", metavar="ACTION",
                            help="Pending actions for working memory")
    p_remember.add_argument("--persona", default="",
                            help="Persona description for identity/preference memory")
    p_remember.add_argument("--policies", nargs="+", metavar="POLICY",
                            help="Policies for identity/preference memory")

    # recall
    p_recall = subparsers.add_parser("recall", help="Show stored memories")
    p_recall.add_argument("--limit", type=int, default=10, help="Max episodes to show")
    p_recall.add_argument("--json", action="store_true", help="Output as JSON (for integrations)")
    p_recall.add_argument("--search", type=str, default="", help="Search memories by keyword")

    # export
    p_export = subparsers.add_parser("export", help="Export memory to a .pam file")
    p_export.add_argument("output", nargs="?", default="my_memory.pam", help="Output file path")

    # import
    p_import = subparsers.add_parser("import", help="Import memory from a .pam file")
    p_import.add_argument("file", help="Path to .pam file")
    p_import.add_argument("--task", default="", help="Task context for rehydration preview")
    p_import.add_argument("--force", action="store_true", help="Import even if integrity fails")

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect a .pam file")
    p_inspect.add_argument("file", help="Path to .pam file")

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify integrity of a .pam file")
    p_verify.add_argument("file", nargs="?", default=None, help="Path to .pam file (defaults to current memory)")
    p_verify.add_argument("--pubkey", help="Path to public key file for signature verification")

    # status
    p_status = subparsers.add_parser("status", help="Show Portable Agent Memory status")
    p_status.add_argument("--json", action="store_true", help="Output as JSON (for integrations)")

    # clear
    p_clear = subparsers.add_parser("clear", help="Clear all stored memories")
    p_clear.add_argument("--force", action="store_true", help="Confirm deletion")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "remember": cmd_remember,
        "recall": cmd_recall,
        "export": cmd_export,
        "import": cmd_import,
        "inspect": cmd_inspect,
        "verify": cmd_verify,
        "status": cmd_status,
        "clear": cmd_clear,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
