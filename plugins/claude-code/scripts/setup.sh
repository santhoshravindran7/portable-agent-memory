#!/usr/bin/env bash
# PAM Plugin Setup — installs the PAM SDK and generates signing keys.
set -euo pipefail

PAM_HOME="${PAM_HOME:-$HOME/.pam}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SDK_LOCAL="$SCRIPT_DIR/../../sdk/python"

echo "🧠 Portable Agent Memory — Setup"
echo "================================="

# 1. Install PAM SDK
echo ""
echo "📦 Installing PAM SDK..."
if [ -f "$SDK_LOCAL/pyproject.toml" ]; then
    echo "   Found local SDK at $SDK_LOCAL"
    python3 -m pip install -q -e "$SDK_LOCAL"
else
    echo "   Installing from GitHub..."
    python3 -m pip install -q "pam-sdk @ git+https://github.com/santhoshravindran7/portable-agent-memory.git#subdirectory=sdk/python"
fi
echo "   ✅ PAM SDK installed"

# 2. Create PAM directory
echo ""
echo "📁 Setting up PAM directory at $PAM_HOME..."
mkdir -p "$PAM_HOME"
echo "   ✅ Directory ready"

# 3. Generate signing keys (if not present)
echo ""
if [ -f "$PAM_HOME/signing.key" ]; then
    echo "🔑 Signing keys already exist — skipping"
else
    echo "🔑 Generating Ed25519 signing keys..."
    python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat
from pathlib import Path

key = Ed25519PrivateKey.generate()
priv = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
pub = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

pam_home = Path('$PAM_HOME')
(pam_home / 'signing.key').write_bytes(priv)
(pam_home / 'signing.pub').write_bytes(pub)
print('   ✅ Keys generated')
print(f'   Private key: {pam_home}/signing.key')
print(f'   Public key:  {pam_home}/signing.pub')
"
fi

echo ""
echo "🎉 Setup complete! PAM is ready."
echo "   Memory store: $PAM_HOME/memory.pam"
echo ""
echo "   Available slash commands:"
echo "     /remember <text>        — Store a memory"
echo "     /recall [query]         — Search memories"
echo "     /export-memory [file]   — Export to .pam file"
echo "     /import-memory <file>   — Import from .pam file"
echo "     /memory-status          — Show statistics"
