# Changelog

All notable changes to the Portable Agent Memory Protocol will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-09

### Added
- **Portable Agent Memory Protocol Specification v1.0** — RFC-style document covering memory artifact format, provenance graph, capability tokens, re-hydration protocol, transport bindings, and security considerations
- **Python SDK** (`pam-sdk`) with 46 passing tests
  - 5-component memory model (Episodic, Semantic, Procedural, Working, Identity)
  - BLAKE3 content-addressable entries
  - Ed25519 signed Merkle-DAG provenance graph
  - Capability-scoped access control with token validation
  - 6-step re-hydration engine (verify → filter → rank → compress → frame → render)
  - JSON (canonical) and CBOR serialization
  - File transport (`.pam` and `.pam.json` formats)
- **JSON Schemas** for artifact envelope, entry types, and capability tokens
- **5 working examples** demonstrating cross-model transfer, capability scoping, provenance verification, and multi-agent handoff
