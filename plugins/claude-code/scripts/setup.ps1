# PAM Plugin Setup — installs the PAM SDK and generates signing keys (Windows).
$ErrorActionPreference = "Stop"

$PamHome = if ($env:PAM_HOME) { $env:PAM_HOME } else { Join-Path $HOME ".pam" }
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SdkLocal = Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "sdk\python"

Write-Host "🧠 Portable Agent Memory — Setup" -ForegroundColor Cyan
Write-Host "================================="

# 1. Install PAM SDK
Write-Host ""
Write-Host "📦 Installing PAM SDK..." -ForegroundColor Yellow
if (Test-Path (Join-Path $SdkLocal "pyproject.toml")) {
    Write-Host "   Found local SDK at $SdkLocal"
    python -m pip install -q -e $SdkLocal
} else {
    Write-Host "   Installing from GitHub..."
    # NOTE: In production, pin to a tagged release or PyPI package with hash verification.
    python -m pip install -q "pam-sdk @ git+https://github.com/santhoshravindran7/portable-agent-memory.git@main#subdirectory=sdk/python"
}
Write-Host "   ✅ PAM SDK installed" -ForegroundColor Green

# 2. Create PAM directory
Write-Host ""
Write-Host "📁 Setting up PAM directory at $PamHome..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $PamHome | Out-Null
Write-Host "   ✅ Directory ready" -ForegroundColor Green

# 3. Generate signing keys (if not present)
Write-Host ""
$KeyPath = Join-Path $PamHome "signing.key"
if (Test-Path $KeyPath) {
    Write-Host "🔑 Signing keys already exist — skipping" -ForegroundColor Yellow
} else {
    Write-Host "🔑 Generating Ed25519 signing keys..." -ForegroundColor Yellow
    $pyScript = @"
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat
from pathlib import Path

key = Ed25519PrivateKey.generate()
priv = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
pub = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

pam_home = Path(r'$PamHome')
(pam_home / 'signing.key').write_bytes(priv)
(pam_home / 'signing.pub').write_bytes(pub)
print('   Keys generated successfully')
"@
    python -c $pyScript
    # Restrict ACL on private key: owner-only access
    $keyAcl = Get-Acl $KeyPath
    $keyAcl.SetAccessRuleProtection($true, $false)  # Disable inheritance, remove inherited rules
    $owner = $keyAcl.Owner
    if (-not $owner) { $owner = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name }
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($owner, "FullControl", "Allow")
    $keyAcl.SetAccessRule($rule)
    Set-Acl -Path $KeyPath -AclObject $keyAcl
    Write-Host "   ✅ Keys generated" -ForegroundColor Green
    Write-Host "   Private key: $PamHome\signing.key (ACL restricted to owner)"
    Write-Host "   Public key:  $PamHome\signing.pub"
}

Write-Host ""
Write-Host "🎉 Setup complete! PAM is ready." -ForegroundColor Green
Write-Host "   Memory store: $PamHome\memory.pam"
Write-Host ""
Write-Host "   Available slash commands:"
Write-Host "     /remember <text>        — Store a memory"
Write-Host "     /recall [query]         — Search memories"
Write-Host "     /export-memory [file]   — Export to .pam file"
Write-Host "     /import-memory <file>   — Import from .pam file"
Write-Host "     /memory-status          — Show statistics"
