# Changelog

All notable changes to the Portable Agent Memory Protocol will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Evaluation metrics module** (`pam.metrics`) implementing spec §10:
  - Transfer Continuity Score (TCS) and Re-Hydration Fidelity (RHF), with spec-aligned interpretation bands
  - Embedding-agnostic semantic similarity (dependency-free lexical fallback; pluggable `embed_fn` for real embedding models)
  - Probe-task harness (`ProbeTask`, `run_probe_tasks`) and a high-level `evaluate_transfer` orchestrator
  - Standardized `EvaluationReport` matching the spec §10.3 JSON shape
  - `pam evaluate <results.json>` CLI command (text and `--json` output)
  - Example `09_evaluation_metrics.py` and 47 new tests

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
