#!/usr/bin/env python3
"""PAM auto-save script — called by hooks to persist working context on session end."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _ensure_pam_sdk() -> None:
    try:
        import pam  # noqa: F401
        return
    except ImportError:
        pass
    script_dir = Path(__file__).resolve().parent
    local_sdk = script_dir.parent.parent.parent / "sdk" / "python"
    if (local_sdk / "pyproject.toml").exists():
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "-e", str(local_sdk)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q",
             "pam-sdk @ git+https://github.com/santhoshravindran7/portable-agent-memory.git#subdirectory=sdk/python"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


_ensure_pam_sdk()

from pam import MemoryArtifact, SourceAgent, WorkingEntry  # noqa: E402
from pam.transport import FileTransport  # noqa: E402

PAM_DIR = Path(os.environ.get("PAM_HOME", Path.home() / ".pam"))
PAM_STORE = PAM_DIR / "memory.pam"


def save_working() -> None:
    """Save a working-memory entry noting the session end."""
    if PAM_STORE.exists():
        try:
            artifact = FileTransport.load(str(PAM_STORE))
        except Exception:
            return
    else:
        artifact = MemoryArtifact(
            source_agent=SourceAgent(
                name="claude-code", model_family="claude",
                runtime="claude-code-plugin", version="0.1.0",
            )
        )

    cwd = os.getcwd()
    entry = WorkingEntry(
        goals=[f"Session ended in {cwd}"],
        scratch=f"Auto-saved at {datetime.now(timezone.utc).isoformat()}",
        tags=["auto-save", "session-end"],
    )
    artifact.working.append(entry)
    artifact.root_hash = artifact.compute_root_hash()

    PAM_DIR.mkdir(parents=True, exist_ok=True)
    key_path = PAM_DIR / "signing.key"
    if key_path.exists():
        try:
            artifact.sign(key_path.read_bytes()[:32])
        except Exception:
            pass
    FileTransport.save(artifact, str(PAM_STORE))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "save-working"
    if cmd == "save-working":
        save_working()
