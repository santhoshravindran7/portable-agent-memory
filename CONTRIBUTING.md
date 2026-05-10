# Contributing to Portable Agent Memory Protocol

Thank you for your interest in contributing to the Portable Agent Memory protocol! This document provides guidelines for contributing.

## Ways to Contribute

- **Protocol Feedback** — Open issues to discuss spec improvements or ambiguities
- **SDK Contributions** — Bug fixes, new features, or entirely new language SDKs (TypeScript, Rust, Go)
- **Framework Adapters** — Integrations with LangChain, CrewAI, AutoGen, Semantic Kernel, etc.
- **Bug Reports** — File issues with reproduction steps
- **Documentation** — Improve docs, examples, or tutorials

## Development Setup

```bash
# Clone the repo
git clone https://github.com/pam-protocol/pam-protocol.git
cd pam-protocol

# Install Python SDK in development mode
cd sdk/python
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Pull Request Process

1. **Fork** the repository and create a feature branch from `main`
2. **Write tests** for any new functionality
3. **Ensure all tests pass** — `pytest tests/ -v` must show all green
4. **Update documentation** if your change affects the public API
5. **Keep PRs focused** — one feature or fix per PR
6. **Write clear commit messages** — use conventional commits (`feat:`, `fix:`, `docs:`, etc.)

## Code Standards

### Python SDK
- Python 3.10+
- Type hints on all public functions
- Docstrings on all public classes and methods
- Pydantic v2 for data models
- `pytest` for testing
- Format with `black`, lint with `ruff`

### Protocol Spec
- Changes to `spec/PAM-SPEC-v1.md` require discussion in an issue first
- Schema changes must be reflected in both the spec and `schemas/` files
- Backward compatibility is required; breaking changes need a new schema version

## Reporting Issues

When filing a bug report, please include:
- Portable Agent Memory SDK version (`pip show pam-sdk`)
- Python version
- Minimal reproduction code
- Expected vs actual behavior
- Full error traceback

## Security Vulnerabilities

Please see [SECURITY.md](SECURITY.md) for responsible disclosure of security issues. **Do not** file security vulnerabilities as public issues.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
