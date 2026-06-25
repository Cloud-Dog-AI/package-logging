# platform-logging — Architecture

**Package:** `cloud_dog_logging`  
**Version:** 0.3.0  
**Standard:** PS-40 (Logging & Observability)  
**Status:** Implemented

---

## OV1 — Overview

`cloud_dog_logging` is a drop-in Python library that implements the PS-40 logging and observability standard. It provides two mandatory log streams (audit + application), structured JSON output, correlation ID propagation, secret redaction, and configurable rotation — all behind a simple factory interface.

### Design Goals

- **Single implementation** of the two-stream logging pattern — no per-project reimplementation.
- **Zero external dependencies** for core functionality (stdlib `logging` only).
- **Backward compatible** with existing `setup_logger()` patterns in notification-agent / expert-agent.
- **Framework-optional**: core library has no web framework dependency; FastAPI middleware is optional.
- **Async-safe**: compatible with asyncio event loops.

---

## SA1 — Module Layout

```
cloud_dog_logging/
  __init__.py                        # Public API: get_logger, get_audit_logger, setup_logger
  config.py                          # Log configuration from platform config (PS-80)
  app_logger.py                      # Application logger (structured JSON, levels)
  audit_logger.py                    # Audit logger (append-only, typed events)
  audit_schema.py                    # Audit event schema / models
  correlation.py                     # Correlation ID context (contextvars)
  redaction.py                       # Secret + PII redaction engine
  formatters/
    __init__.py
    json_formatter.py                # Structured JSON Lines formatter
    text_formatter.py                # Human-readable formatter (dev mode)
  handlers/
    __init__.py
    rotating_file.py                 # Size + time-based rotating file handler
    stdout_handler.py                # Stdout/stderr handler (containers)
    dual_handler.py                  # File + stdout simultaneously
  middleware/
    __init__.py
    fastapi.py                       # FastAPI request logging + correlation ID middleware
  health/
    __init__.py
    reporter.py                      # Log file size, rotation status, audit event count
  compat.py                          # Backward-compatible setup_logger() function
  errors.py                          # Logging-specific exceptions
  sinks/
    __init__.py
    base.py                          # AuditSink protocol (FR1.18)
    file_sink.py                     # FileSink — JSONL file output
    stdout_sink.py                   # StdoutSink — stdout output
    db_sink.py                       # DatabaseSink — DB table output (optional)
    fan_out.py                       # FanOutSink — multiple sinks simultaneously
  signing.py                         # Audit signing hooks (FR1.19)
  tool_events.py                     # log_tool_event() helper (FR1.20)
  presets.py                         # Redaction presets (FR1.21)
  sampling.py                        # Log sampling filter (FR1.22)
  batching.py                        # Audit event batching (FR1.23)
  exceptions.py                      # Structured exception serialisation (FR1.24)
  event_catalogue.py                 # Optional event catalogue validator (AU-2/AU-6)
  integrity.py                       # Audit integrity verifier (FR1.25/FR1.26)
```

---

## SA2 — Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     Service (FastAPI / CLI)                       │
│                                                                  │
│  middleware/fastapi.py ──→ inject correlation_id                  │
│         │                  log request/response                   │
│         ▼                                                        │
│  ┌──────────────┐          ┌──────────────┐                     │
│  │ get_logger() │          │ get_audit_   │                     │
│  │ → app_logger │          │ logger()     │                     │
│  │              │          │ → audit_     │                     │
│  │              │          │   logger     │                     │
│  └──────┬───────┘          └──────┬───────┘                     │
│         │                         │                              │
│         │   redaction.py ◄────────┤                              │
│         │   (applied to both)     │                              │
│         │                         │                              │
│         ▼                         ▼                              │
│  ┌──────────────┐          ┌──────────────┐                     │
│  │ formatters/  │          │ formatters/  │                     │
│  │ json or text │          │ json only    │                     │
│  └──────┬───────┘          └──────┬───────┘                     │
│         │                         │                              │
│         ▼                         ▼                              │
│  ┌──────────────┐          ┌──────────────┐                     │
│  │ handlers/    │          │ handlers/    │                     │
│  │ rotating_file│          │ rotating_file│                     │
│  │ + stdout     │          │ (append-only)│                     │
│  └──────────────┘          └──────────────┘                     │
│         │                         │                              │
│         ▼                         ▼                              │
│   logs/app.log              logs/audit.log.jsonl                │
│   (or stdout)               (or stdout)                         │
└──────────────────────────────────────────────────────────────────┘
         │
         └──→ correlation.py (contextvars: correlation_id per request)
```

---

## CC1 — Core Components

### CC1.1 Application Logger (`app_logger.py`)

Standard Python logger with structured JSON output:

```python
class AppLogger:
    """Structured application logger."""
    
    def debug(self, msg, **extra): ...
    def info(self, msg, **extra): ...
    def warning(self, msg, **extra): ...
    def error(self, msg, **extra): ...
    def critical(self, msg, **extra): ...
    def exception(self, msg, **extra): ...
```

- All entries include: `timestamp`, `level`, `logger`, `message`, `correlation_id`, `service`, `extra`.
- Extra fields are redacted before output.
- Built on stdlib `logging.Logger` — compatible with existing Python logging ecosystem.

### CC1.2 Audit Logger (`audit_logger.py`)

Typed audit event logger with mandatory schema:

```python
class AuditLogger:
    """Append-only audit event logger."""
    
    def emit(self, event: AuditEvent) -> None:
        """Emit a raw audit event."""
    
    def log_login(self, actor: Actor, outcome: str, **details) -> None: ...
    def log_crud(self, actor: Actor, action: str, target: Target, outcome: str, **details) -> None: ...
    def log_config_change(self, actor: Actor, diff_summary: dict, outcome: str, **details) -> None: ...
    def log_tool_call(self, actor: Actor, tool: str, params: dict, outcome: str, duration_ms: int, **details) -> None: ...
    def log_security(self, actor: Actor, action: str, target: Target, outcome: str, **details) -> None: ...
```

- All events validated against `AuditEvent` schema before writing.
- Details field scanned for secrets and redacted.
- Append-only: handler configured to not truncate/overwrite.

### CC1.3 Audit Event Schema (`audit_schema.py`)

```python
@dataclass
class Actor:
    type: str          # "user" | "service" | "system"
    id: str            # Stable user/service identifier
    roles: list[str] | None = None

@dataclass
class Target:
    type: str          # "user" | "session" | "config" | "api_key" | etc.
    id: str            # Target entity identifier

@dataclass
class AuditEvent:
    timestamp: str     # ISO 8601 UTC
    event_type: str    # e.g., "user.login", "config.reload"
    actor: Actor
    action: str        # "create" | "update" | "delete" | "login" | etc.
    outcome: str       # "success" | "failure" | "error"
    correlation_id: str
    service: str
    target: Target | None = None
    details: dict | None = None
    duration_ms: int | None = None
```

### CC1.4 Correlation ID (`correlation.py`)

```python
# Context-local correlation ID using contextvars
correlation_id_var: ContextVar[str]

def get_correlation_id() -> str:
    """Get current correlation ID (generates new if none set)."""

def set_correlation_id(cid: str) -> None:
    """Set correlation ID for current context."""

def correlation_id_middleware(header_name: str = "X-Request-Id"):
    """Extract or generate correlation ID from request header."""
```

- `contextvars.ContextVar` ensures async-safety.
- All loggers automatically read from context.

### CC1.5 Redaction Engine (`redaction.py`)

```python
class RedactionEngine:
    """Redact secrets and PII from log data."""
    
    def __init__(self, patterns: list[str] | None = None): ...
    def redact(self, data: dict) -> dict: ...
    def redact_string(self, value: str) -> str: ...
```

- Default patterns: keys containing `secret`, `password`, `key`, `token`, `credential`, `api_key`.
- Configurable additional patterns per project.
- Recursive dict/list scanning.
- Values replaced with `***REDACTED***`.

### CC1.6 JSON Formatter (`formatters/json_formatter.py`)

```python
class JSONFormatter(logging.Formatter):
    """Structured JSON Lines formatter for both log streams."""
    
    def format(self, record: LogRecord) -> str: ...
```

- One JSON object per line.
- Includes all required fields from FR1.3/FR1.4.
- Handles exceptions (serialises traceback as string).

### CC1.7 Rotating File Handler (`handlers/rotating_file.py`)

```python
class ConfigurableRotatingHandler(logging.Handler):
    """Size + time-based rotation with retention."""
    
    def __init__(
        self,
        filename: str,
        max_bytes: int = 10_485_760,  # 10MB
        backup_count: int = 5,
        when: str = "midnight",       # time-based trigger
        interval: int = 1,
    ): ...
```

- Combines `RotatingFileHandler` and `TimedRotatingFileHandler` behaviour.
- Configurable via platform config (`log.rotation.*`).
- Rotation MUST NOT lose log entries.

### CC1.8 FastAPI Middleware (`middleware/fastapi.py`)

```python
class LoggingMiddleware:
    """FastAPI middleware for request logging and correlation ID."""
    
    async def dispatch(self, request, call_next):
        # 1. Extract or generate correlation ID
        # 2. Set in contextvars
        # 3. Log request start
        # 4. Call next
        # 5. Log request end (status, duration, client IP)
        # 6. Add X-Request-Id to response headers
```

### CC1.9 Backward Compatibility (`compat.py`)

```python
def setup_logger(
    name: str,
    log_file: str,
    log_level: str = "INFO",
    log_format: str = "json",
    console: bool = True,
) -> logging.Logger:
    """Backward-compatible setup matching existing project patterns."""
```

Drop-in replacement for the `setup_logger()` function used in notification-agent and expert-agent.

### CC1.10 Health Reporter (`health/reporter.py`)

```python
class LogHealthReporter:
    """Observability data for log subsystem."""
    
    def get_status(self) -> dict:
        """Returns: file sizes, rotation status, audit event count, last audit timestamp."""
```

### CC1.11 Audit Sink Interface (`sinks/base.py`)

```python
class AuditSink(Protocol):
    def emit(self, event: AuditEvent) -> None: ...
    def flush(self) -> None: ...
    def close(self) -> None: ...
```

Built-in implementations:
- `FileSink` — writes JSONL to file (existing behaviour, extracted).
- `StdoutSink` — writes to stdout.
- `DatabaseSink` — writes to DB table via repository protocol (optional dependency).
- `FanOutSink` — dispatches to multiple sinks simultaneously.

### CC1.12 Audit Signing (`signing.py`)

```python
class AuditSigner(Protocol):
    def pre_persist(self, event: AuditEvent) -> AuditEvent: ...
    def post_persist(self, event: AuditEvent) -> None: ...

class HMACSigner:
    """HMAC-SHA256 signing for tamper-evident audit records."""
    def __init__(self, secret_key: str): ...
```

- Invoked by `AuditLogger` before/after sink emit.
- Disabled by default; enabled via config (`log.audit.signing.enabled`).

### CC1.13 Tool Event Helper (`tool_events.py`)

```python
def log_tool_event(
    tool: str,
    profile: str | None = None,
    duration_ms: int | None = None,
    paths: list[str] | None = None,
    outcome: str = "success",
    **details,
) -> None:
    """Convenience helper for MCP/tool audit events."""
```

### CC1.14 Redaction Presets (`presets.py`)

```python
class RedactionPreset:
    name: str
    patterns: list[str]

BUILTIN_PRESETS: dict[str, RedactionPreset] = {
    "default": RedactionPreset(name="default", patterns=[...]),
    "file_tools": RedactionPreset(name="file_tools", patterns=[...]),
}

def load_presets(config: dict) -> list[RedactionPreset]:
    """Load and compose redaction presets from config."""
```

### CC1.15 Log Sampling (`sampling.py`)

```python
class SamplingFilter(logging.Filter):
    """Per-logger sampling for high-volume DEBUG logs."""
    
    def __init__(self, rates: dict[str, float]): ...
    def filter(self, record: LogRecord) -> bool: ...
```

- Only applies to DEBUG level; WARNING+ always passes.
- Counted metrics for sampled-out entries.

### CC1.16 Audit Batching (`batching.py`)

```python
class BatchingSink:
    """Wraps a sink with batch flush semantics."""
    
    def __init__(self, sink: AuditSink, batch_size: int = 100, flush_interval_s: float = 5.0): ...
    def emit(self, event: AuditEvent) -> None: ...
    def flush(self) -> None: ...
    def close(self) -> None: ...
```

- Flush on batch size reached, interval elapsed, or shutdown signal.
- Ordering preserved within batch.

### CC1.17 Structured Exception Serialisation (`exceptions.py`)

```python
def format_exception(exc: BaseException) -> dict:
    """Serialise exception with type, message, stack_hash, traceback."""
```

- `stack_hash` = SHA-256 of normalised traceback string (for dedup).
- Used by `AppLogger.exception()` and audit event details.

### CC1.18 Audit Integrity Verifier (`integrity.py`)

```python
class AuditIntegrityVerifier:
    """Periodic hash verification for audit log files."""

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def compute_now(self, trigger: str = "manual") -> dict: ...
```

- Computes `sha256` (default), `sha512`, or `crc32` hashes over full audit log content.
- Writes integrity records to both application logs and `logs/audit-integrity.log`.
- Emits records on `startup`, `periodic`, `rotation`, `manual`, and `shutdown`.

---

## DM1 — Data Model

No persistent database. Logs are file-based or stdout-based.

### Log File Convention

```
logs/
  app.log                # Application log (current)
  app.log.1              # Rotated application logs
  app.log.2
  audit.log.jsonl        # Audit log (current, append-only)
  audit.log.jsonl.1      # Rotated audit logs
  audit-integrity.log    # Integrity verification JSONL records
```

File paths configurable via platform config (`log.app_log`, `log.audit_log`).

---

## DP1 — Dependency Policy

| Dependency | Status | Notes |
|-----------|--------|-------|
| stdlib `logging` | Required | Core logging framework |
| `python-json-logger` | Optional | Enhanced JSON formatting (falls back to built-in) |

No web framework dependency. No database dependency. No external service dependency.

---

## SE1 — Security Architecture

- Secret redaction applied to all log output paths before writing.
- Audit log is append-only — handlers configured to not truncate.
- Correlation IDs contain no sensitive information (UUID or hex token).
- PII redaction configurable per project.
- Log files SHOULD have restricted filesystem permissions (configurable).

---

## Integration Pattern

Services consume the package as follows:

```python
from cloud_dog_logging import get_logger, get_audit_logger, setup_logging
from cloud_dog_logging.audit_schema import Actor, Target

# At startup (once)
setup_logging(config)  # Reads log.* from GlobalConfig

# In application code
logger = get_logger(__name__)
logger.info("Processing request", extra={"user_id": user.id})

# For security events
audit = get_audit_logger()
audit.log_login(
    actor=Actor(type="user", id=str(user.id)),
    outcome="success",
    ip=request.client.host,
)

# For FastAPI
from cloud_dog_logging.middleware.fastapi import LoggingMiddleware
app.add_middleware(LoggingMiddleware)
```
