# platform-logging — Requirements

**Package:** `cloud_dog_logging`  
**Version:** 0.3.0  
**Standard:** PS-40 (Logging & Observability)  
**Status:** Implemented

---

## Scope / Vision

### SV1.1
The package SHALL provide a single, reusable logging library for all Cloud-Dog Python services, implementing the two-stream logging standard defined in PS-40.

### SV1.2
The package SHALL eliminate per-project logger reimplementation — services import `cloud_dog_logging` and receive consistent structured logging, audit event emission, correlation ID propagation, and secret redaction.

---

## Business Objectives

### BO1.1
Reduce logging inconsistencies by enforcing a single, tested logging configuration across all services.

### BO1.2
Enable consistent audit trails for compliance and security across all services.

### BO1.3
Provide correlation ID propagation for request tracing across service boundaries.

---

## Functional Requirements

### FR1.1 — Two Log Streams
The package MUST produce two distinct log streams per service:
1. **Audit log** — security/compliance trail (who did what, when, outcome).
2. **Application log** — operational/diagnostic (runtime behaviour, errors, performance).

### FR1.2 — Structured JSON Logging
Both log streams MUST output structured JSON Lines (one JSON object per line):
- Audit: append-only semantics.
- Application: standard Python log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL).

### FR1.3 — Audit Event Schema
The audit log MUST use a mandatory event schema:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `timestamp` | ISO 8601 UTC | Yes | |
| `event_type` | string | Yes | e.g., `user.login`, `config.reload`, `tool_call` |
| `actor` | object | Yes | `{type, id, roles?}` |
| `action` | string | Yes | e.g., `create`, `update`, `delete`, `login` |
| `target` | object | Conditional | `{type, id}` — what was acted upon |
| `outcome` | string | Yes | `success`, `failure`, `error` |
| `correlation_id` | string | Yes | Request/trace correlation |
| `service` | string | Yes | Originating service name |
| `details` | object | No | Additional context (no secrets) |
| `duration_ms` | integer | No | Operation duration |

### FR1.4 — Application Log Schema
Application log entries MUST include:

| Field | Type | Required |
|-------|------|----------|
| `timestamp` | ISO 8601 UTC | Yes |
| `level` | string | Yes |
| `logger` | string | Yes |
| `message` | string | Yes |
| `correlation_id` | string | Yes (if in request context) |
| `service` | string | Yes |
| `extra` | object | No |

### FR1.5 — Correlation ID Propagation
The package MUST support correlation ID propagation:
- Generate a new correlation ID if none present in incoming request.
- Propagate via `X-Request-Id` header (configurable header name).
- Attach to all log entries (audit and application) within the request scope.
- Provide context-local storage (e.g., `contextvars`) for correlation ID.

### FR1.6 — Secret Redaction
The package MUST redact secrets from all log output:
- Pattern-based redaction (key names containing `secret`, `password`, `key`, `token`, `credential`).
- Configurable patterns (additional project-specific patterns).
- Redaction applied to: log messages, extra fields, audit event details.
- PII redaction hooks (optional, configurable).

### FR1.7 — Log Destinations
The package MUST support configurable log destinations:
- File (with rotation) — default.
- Stdout/stderr (for containerised deployments).
- Both simultaneously.
- Separate destinations for audit and application logs.

### FR1.8 — Log Rotation
The package MUST support parameterised log rotation:
- Size-based rotation (configurable max size).
- Time-based rotation (daily, hourly — configurable).
- Retention policy (configurable max files / max age).
- Rotation MUST NOT lose log entries.

### FR1.9 — Logger Factory
The package MUST provide a logger factory:

```python
def get_logger(name: str, pii_redaction: bool = True) -> Logger:
    """Get a configured logger for the given module name."""

def get_audit_logger() -> AuditLogger:
    """Get the audit logger for security events."""
```

### FR1.10 — Audit Event Helpers
The package MUST provide typed audit event helpers:

```python
class AuditLogger:
    def log_login(self, actor, outcome, **details): ...
    def log_crud(self, actor, action, target, outcome, **details): ...
    def log_config_change(self, actor, diff_summary, outcome, **details): ...
    def log_tool_call(self, actor, tool, params, outcome, duration_ms, **details): ...
    def log_security(self, actor, action, target, outcome, **details): ...
```

### FR1.11 — Log Level Configuration
Log levels MUST be configurable via the platform config system (PS-80):
- Per-logger level overrides (e.g., `log.levels.sqlalchemy=WARNING`).
- Runtime level change support (via hot reload).

### FR1.12 — Health / Observability Endpoints
The package SHOULD provide helpers for health/observability:
- Log file size and rotation status.
- Audit event count since startup.
- Last audit event timestamp.

### FR1.13 — No Secrets in Logs (Enforcement)
The package MUST enforce that secrets never appear in log output:
- Redaction applied before writing.
- Audit events: details field scanned for secret patterns.
- Application logs: extra field scanned.

### FR1.14 — Append-Only Audit Semantics
The audit log MUST be append-only:
- No rewriting or deletion outside retention policy.
- Tamper-evident where feasible (optional hash chaining).

### FR1.15 — FastAPI Middleware
The package MUST provide optional FastAPI middleware:
- Request logging (method, path, status, duration, client IP, correlation ID).
- Automatic correlation ID injection/propagation.
- Exception logging with correlation ID.

### FR1.16 — Configuration via Platform Config
The package MUST consume configuration via `cloud_dog_config` (PS-80):
- All log settings in config namespace (e.g., `log.*`).
- Settings: level, format, file paths, rotation policy, console output, redaction patterns.
- This package MUST NOT read `os.environ` for credentials or config values (except for graceful standalone fallback when `cloud_dog_config` is not installed), import `hvac`, navigate Vault JSON, or implement its own secret resolution logic.

### FR1.17 — Backward Compatibility
The package MUST provide a `setup_logger()` function compatible with the pattern used in existing projects (notification-agent, expert-agent):

```python
def setup_logger(name, log_file, log_level, log_format, console) -> Logger:
```

### FR1.18 — Pluggable Audit Sink
The package MUST support a pluggable `AuditSink` interface:
- Backends: `stdout`, `file` (default), `db` (optional).
- `AuditSink` protocol: `emit(event: AuditEvent) -> None`, `flush() -> None`, `close() -> None`.
- `FileSink` — writes to JSONL file (existing behaviour, now explicit).
- `StdoutSink` — writes to stdout.
- `DatabaseSink` — writes to a database table via a repository protocol (optional dependency).
- Multiple sinks may be active simultaneously (fan-out).
- **Sources**: expert-agent (DB audit sink), notification-agent (custom signed audit).

### FR1.19 — Audit Signing Hooks
The package SHOULD support optional signing hooks for tamper-evident audit records:
- `pre_persist(event: AuditEvent) -> AuditEvent` — invoked before writing (e.g. add HMAC hash).
- `post_persist(event: AuditEvent) -> None` — invoked after writing (e.g. update hash chain).
- Signing is optional and configurable; disabled by default.
- **Sources**: expert-agent (signature hook), notification-agent (custom audit signatures).

### FR1.20 — Tool Event Helper
The package MUST provide a `log_tool_event()` convenience helper:
- Parameters: `tool`, `profile`, `duration_ms`, `paths` (list), `outcome`, `correlation_id`, plus `**details`.
- Generates an `AuditEvent` with `event_type="tool_call"` and structured `details` including tool metadata.
- Use case: MCP tool operations in file-mcp, expert-agent tool calls.
- **Source**: file-mcp (file-operation audit helper).

### FR1.21 — Redaction Presets
The package MUST provide configurable redaction presets:
- Default preset: keys matching `token|secret|password|api_key|credential`.
- `file_tools` preset: additionally masks nested keys in tool payloads matching `token|secret|password|api_key|authorization`.
- Custom presets loadable from config (`log.redaction.presets`).
- Presets are composable (multiple presets can be active).
- **Source**: file-mcp (built-in redaction presets for file-tool params).

### FR1.22 — Log Sampling
The package SHOULD support configurable log sampling for high-volume DEBUG logs:
- Sampling rate configurable per logger name (e.g. `log.sampling.httpx=0.1` → 10% of DEBUG entries).
- Sampling MUST NOT affect WARNING/ERROR/CRITICAL or audit events.
- Sampled-out entries MUST still be counted (metric hook).
- **Source**: foresight (high-throughput services).

### FR1.23 — Audit Event Batching
The package SHOULD support optional batch flush for high-throughput audit sinks:
- Configurable batch size and flush interval.
- Flush on shutdown / signal.
- Ordering preserved within batch.
- Only applicable to `DatabaseSink`; `FileSink` and `StdoutSink` flush immediately.
- **Source**: foresight (DB audit sink throughput).

### FR1.24 — Structured Exception Logging
The package MUST provide a standard exception serialisation helper:
- `format_exception(exc) -> dict` returning `type`, `message`, `stack_hash` (SHA-256 of traceback), `traceback` (list of frame strings).
- `stack_hash` enables deduplication of repeated exceptions.
- Used by `AppLogger.exception()` and audit event `details`.
- **Source**: foresight (exception dedup and alerting).

### FR1.25 — Audit Integrity Verification
The package MUST provide periodic integrity verification for audit logs:
- Compute a hash of the active audit log file at configurable intervals.
- Write integrity records to both application logs and a dedicated integrity log file.
- Support startup baseline, periodic checks, manual checks, rotation checks, and shutdown final record.

### FR1.26 — Integrity Configuration
The package MUST expose integrity verifier configuration:
- `log.integrity.enabled`
- `log.integrity.interval_seconds`
- `log.integrity.log_file`
- `log.integrity.hash_algorithm` (`sha256`, `sha512`, `crc32`)

### FR1.27 — Rotation Event Logging
The package MUST emit explicit rotation events:
- Rotation event includes `old_file`, `new_file`, `reason`, and `file_size_bytes`.
- Rotation configuration is sourced from config (`log.rotation.*`) rather than hardcoded values.
- Audit rotation triggers a fresh integrity baseline computation.

---

## Non-Functional Requirements

### NF1.1
Zero non-stdlib runtime dependencies beyond: standard `logging` module. Optional: `python-json-logger` (for structured output).

### NF1.2
Logging overhead MUST be < 1ms per log entry (excluding I/O flush).

### NF1.3
The package MUST be thread-safe and async-safe (safe for use with asyncio).

### NF1.4
The package MUST work with Python 3.10+.

---

## Cyber Security

### CS1.1
Secrets MUST NEVER appear in any log stream.

### CS1.2
Audit logs MUST be append-only.

### CS1.3
Correlation IDs MUST NOT contain sensitive information.

### CS1.4
PII handling MUST follow configurable redaction policy.

---

## Acceptance Criteria

A project is compliant when:
- It uses `cloud_dog_logging` for all logging.
- Two log streams are active (audit + application).
- Audit events follow the mandatory schema.
- Correlation IDs are propagated across all log entries.
- Secrets are redacted from all output.
- Log rotation is configured and tested.
- No direct `os.environ`, `hvac`, or Vault reads for credentials — all config via `cloud_dog_config` (PS-80).
