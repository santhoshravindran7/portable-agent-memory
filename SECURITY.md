# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in the Portable Agent Memory Protocol or SDK, please report it responsibly.

**Do NOT file a public GitHub issue for security vulnerabilities.**

Instead, please email: **security@pam-protocol.dev** (or use GitHub's private vulnerability reporting feature)

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Assessment**: Within 7 days
- **Fix/Mitigation**: Within 30 days for critical issues
- **Public Disclosure**: After fix is released, coordinated with reporter

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Current |

## Security Considerations

Portable Agent Memory handles cryptographic operations and agent memory, which may contain sensitive data. Key areas:

- **Ed25519 Signatures**: Used for artifact and capability token signing
- **BLAKE3 Hashing**: Used for content-addressable entry IDs and provenance verification
- **Capability Tokens**: Control access to memory segments — token leakage grants access
- **Re-Hydration**: Injection-resistant framing is critical — bypasses could enable prompt injection
- **Redaction Pipeline**: PII detection failures could leak sensitive data

## Best Practices for Users

- Store Ed25519 private keys securely (never in source code)
- Set appropriate expiration times on capability tokens
- Use the redaction pipeline before exporting artifacts containing user data
- Verify artifact signatures before re-hydration in untrusted environments
