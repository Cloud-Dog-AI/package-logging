# cloud-dog-logging

**Part of the [Cloud-Dog AI Platform](https://www.cloud-dog.ai)**

> Intelligent automation through composable AI agents, MCP servers, and shared platform services.

## About Cloud-Dog AI

Cloud-Dog AI is a platform of 10+ composable services for AI-powered business automation — natural language SQL queries, email management, file operations, git workflows, notification delivery, and expert knowledge retrieval. All services share a common set of platform packages for configuration, logging, authentication, job queues, LLM integration, vector databases, and caching.

This package provides: structured JSON logging with correlation ID propagation, audit trails, and configurable per-module log levels.

## Installation

```bash
pip install cloud-dog-logging
```

Available from the [Cloud-Dog AI package registry](https://www.cloud-dog.ai/packages).

## Quick Start

```python
from cloud_dog_logging import *

# See API Reference below for available functions and classes
```

## API Reference

### Functions

| Function | Description |
|----------|-------------|
| `setup_logging(config)` | One-time logging setup from config dict or platform GlobalConfig. |
| `get_logger(name: str, pii_redaction: bool)` | Get a configured application logger for the given module name. |
| `get_audit_logger()` | Get the singleton audit logger for security events. |
| `get_integrity_verifier()` | Get the audit integrity verifier when enabled. |

### Exports

```python
from cloud_dog_logging import (
    Actor,
    Any,
    AppLogger,
    AuditEvent,
    AuditIntegrityVerifier,
    AuditLogger,
    AuditMiddleware,
    AuditSink,
    BUILTIN_PRESETS,
    BatchingSink,
    Callable,
    ConfigurableRotatingHandler,
    DatabaseSink,
    DualHandler,
    FanOutSink,
    FileSink,
    HMACSigner,
    JSONFormatter,
    LogConfig,
    LogHealthReporter,
    RedactionEngine,
    RedactionPreset,
    SamplingFilter,
    StdoutHandler,
    StdoutSink,
    Target,
    TextFormatter,
    annotations,
    clear_correlation_id,
    format_exception,
    get_audit_logger,
    get_correlation_id,
    get_environment,
    get_integrity_verifier,
    get_logger,
    get_service_instance,
    get_service_name,
    load_presets,
    log_tool_event,
    set_correlation_id,
    set_environment,
    set_service_instance,
    set_service_name,
    setup_logger,
    setup_logging,
)
```

## Testing

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=cloud_dog_logging --cov-report=term-missing
```

### Test Structure
- `tests/unit/` — Unit tests (no external dependencies)
- `tests/integration/` — Integration tests (requires running services)

## Related Packages

| Package | Description |
|---------|-------------|
| cloud-dog-config | Layered configuration with Vault integration |
| cloud-dog-logging | Structured JSON logging with correlation IDs |
| cloud-dog-api-kit | FastAPI toolkit with middleware and routing |
| cloud-dog-idam | Identity and access management client |
| cloud-dog-jobs | Background job scheduling and execution |
| cloud-dog-llm | LLM client abstraction (OpenAI, Ollama, etc.) |
| cloud-dog-vdb | Vector database client (Infinity, pgvector) |
| cloud-dog-cache | Caching abstraction with Redis/Valkey support |
| cloud-dog-tokens | Design tokens for UI consistency |
| cloud-dog-ui | React component library |
| cloud-dog-shell | Application shell and navigation |
| cloud-dog-auth | Frontend authentication flows |
| cloud-dog-api-client | TypeScript API client |
| cloud-dog-config-fe | Frontend configuration management |
| cloud-dog-testing | Test utilities and fixtures |

## Version

0.3.4

---

## Licence

Apache 2.0

Copyright 2026 [Cloud-Dog](https://www.cloud-dog.ai), Viewdeck Engineering Limited ([viewdeck.io](https://www.viewdeck.io))

[info@cloud-dog.ai](mailto:info@cloud-dog.ai)
