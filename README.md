# platform-logging

**Package:** `cloud_dog_logging`  
**Standard:** PS-40 (Logging & Observability)  
**Version:** `0.3.0`  
**Status:** Implemented

## Purpose

Drop-in Python library implementing the PS-40 logging and observability standard. Provides two mandatory log streams (audit + application), structured JSON output, correlation ID propagation, secret redaction, and configurable rotation.

## Key Features

- **Two log streams**: Audit (append-only, security/compliance) + Application (operational/diagnostic)
- **Structured JSON Lines**: One JSON object per line, mandatory schema
- **Correlation IDs**: Automatic propagation via `contextvars` (async-safe)
- **Secret redaction**: Pattern-based, configurable, applied to all output
- **Log rotation**: Size + time-based with retention policy; zero entry loss
- **Audit event helpers**: Typed methods for login, CRUD, config change, tool call, security events
- **FastAPI middleware**: Request logging + correlation ID injection (optional)
- **Backward compatible**: `setup_logger()` drop-in for existing projects
- **Pluggable audit sinks**: `FileSink`, `StdoutSink`, `DatabaseSink`, `FanOutSink`
- **Audit signing hooks**: `HMACSigner` hash-chain support (optional)
- **Tool event helper**: `log_tool_event(...)` for MCP/tool operations
- **Redaction presets**: built-in `default` and `file_tools` presets
- **DEBUG log sampling**: per-logger `SamplingFilter`
- **Audit batching**: `BatchingSink` wrapper for throughput
- **Structured exceptions**: `format_exception()` with stable `stack_hash`
- **Zero external dependencies**: Core uses stdlib `logging` only

## Dependencies

- **Required:** stdlib `logging` (no external deps for core)
- **Optional:** `python-json-logger` (enhanced JSON formatting)

## Documents

- [REQUIREMENTS.md](REQUIREMENTS.md) — Functional and non-functional requirements (24 FRs)
- [ARCHITECTURE.md](ARCHITECTURE.md) — Module layout, component design, integration pattern
- [TESTS.md](TESTS.md) — Test plan, directory structure, coverage map (UT/ST/IT/AT)

## Quick Start

```python
from cloud_dog_logging import get_logger, get_audit_logger, setup_logging
from cloud_dog_logging.audit_schema import Actor

# At startup
setup_logging(config)

# Application logging
logger = get_logger(__name__)
logger.info("Processing request", extra={"user_id": user.id})

# Audit logging
audit = get_audit_logger()
audit.log_login(actor=Actor(type="user", id=str(user.id)), outcome="success")
```

## Installation

```bash
pip install cloud-dog-logging
```

## API Overview

- `setup_logging(...)` configures application and audit logging sinks.
- `get_logger(...)` returns an application logger.
- `get_audit_logger(...)` returns the audit event logger.

## Examples

- Configure structured application and audit logging during service startup.
- Emit audit events with correlation identifiers and redaction applied.
- Attach middleware helpers to framework runtimes without bespoke logger code.

## Validation Status (2026-02-18)

- Package implemented and built: `cloud_dog_logging-0.3.0`
- Quality gates run in this uplift:
  - `pytest tests --env tests/env-UT -q` -> `201 passed`
  - `pytest tests --env tests/env-IT -q` -> `201 passed`
  - `ruff check cloud_dog_logging tests` -> pass
  - `ruff format --check cloud_dog_logging tests` -> pass
  - `<platform-config>/.venv/bin/python -m build --no-isolation` -> pass (sdist + wheel)

---

## Licence

Apache-2.0 — Copyright (c) 2026 Cloud-Dog, Viewdeck Engineering Limited
