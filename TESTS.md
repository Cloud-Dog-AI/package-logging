# platform-logging — TESTS.md

**Package:** `cloud_dog_logging`  
**Version:** 0.3.0  
**Standard:** PS-40, PS-95  
**Status:** Implemented

---

## Test Strategy

### Overview

Tests organised per PS-95 hierarchy:

- **UT** — Unit tests for individual components (formatters, handlers, redaction, correlation, audit schema)
- **ST** — System tests for end-to-end logging with real file I/O and rotation
- **IT** — Integration tests with FastAPI middleware and real HTTP requests
- **AT** — Application tests simulating real service logging patterns

### Test Principles

- `--env` mandatory for all test runs.
- Zero hardcoded values.
- UT tests use temp dirs for log files.
- ST tests use real file I/O with rotation validation.
- IT tests use FastAPI TestClient for middleware.
- Stop on failure.

---

## Test Directory Structure

```
tests/
  conftest.py
  env-UT
  env-ST
  env-IT
  env-AT
  unit/
    UT1.1_JSONFormatter/
      test_json_formatter.py
    UT1.2_TextFormatter/
      test_text_formatter.py
    UT1.3_RedactionEngine/
      test_redaction.py
    UT1.4_CorrelationID/
      test_correlation.py
    UT1.5_AuditSchema/
      test_audit_schema.py
    UT1.6_AuditLogger/
      test_audit_logger.py
    UT1.7_AppLogger/
      test_app_logger.py
    UT1.8_LoggerFactory/
      test_logger_factory.py
    UT1.9_HealthReporter/
      test_health_reporter.py
    UT1.10_BackwardCompat/
      test_setup_logger.py
    UT1.11_SecretScanGuard/
      test_secret_scan.py
    UT1.12_AuditSinkInterface/
      test_audit_sink.py
    UT1.13_FileSink/
      test_file_sink.py
    UT1.14_StdoutSink/
      test_stdout_sink.py
    UT1.15_FanOutSink/
      test_fan_out_sink.py
    UT1.16_AuditSigning/
      test_signing.py
    UT1.17_ToolEventHelper/
      test_tool_events.py
    UT1.18_RedactionPresets/
      test_presets.py
    UT1.19_LogSampling/
      test_sampling.py
    UT1.20_AuditBatching/
      test_batching.py
    UT1.21_ExceptionSerialisation/
      test_exception_format.py
    UT_NIST_AU3/
      test_nist_au3_fields.py
    UT_IntegrityVerifier/
      test_integrity_verifier.py
  system/
    ST1.1_TwoStreamOutput/
      test_two_streams.py
    ST1.2_FileRotation/
      test_rotation.py
    ST1.3_AppendOnlyAudit/
      test_append_only.py
    ST1.4_LogLevelConfig/
      test_log_levels.py
    ST1.5_DualDestination/
      test_file_plus_stdout.py
    ST1.6_RotationNoLoss/
      test_rotation_no_loss.py
    ST_IntegrityVerifier/
      test_integrity_periodic.py
    ST_RotationEnforcement/
      test_rotation_enforcement.py
  integration/
    IT1.1_FastAPIMiddleware/
      test_fastapi_middleware.py
    IT1.2_CorrelationPropagation/
      test_correlation_propagation.py
    IT1.3_RequestResponseLogging/
      test_request_logging.py
  application/
    AT1.1_ServiceStartupPattern/
      test_service_startup.py
    AT1.2_AuditEventCoverage/
      test_audit_coverage.py
    AT1.3_HighVolumeLogging/
      test_high_volume.py
    AT1.4_DatabaseSinkPattern/
      test_db_sink_pattern.py
    AT1.5_SignedAuditChain/
      test_signed_audit.py
```

---

## Env File Mapping

| Suite | Non-secret env | Secrets env | Notes |
|-------|---------------|-------------|-------|
| UT* | tests/env-UT | — | No secrets needed |
| ST* | tests/env-ST | — | File-system tests |
| IT* | tests/env-IT | — | FastAPI middleware tests |
| AT* | tests/env-AT | — | Full service simulation |

---

## Coverage Map (Requirements → Tests)

### Functional Requirements
- **FR1.1** → ST1.1 (two log streams)
- **FR1.2** → UT1.1 (JSON formatter)
- **FR1.3** → UT1.5 (audit event schema), UT1.6 (audit logger)
- **FR1.4** → UT1.7 (app logger schema)
- **FR1.5** → UT1.4 (correlation ID), IT1.2 (propagation)
- **FR1.6** → UT1.3 (redaction engine), UT1.11 (secret scan guard)
- **FR1.7** → ST1.5 (dual destination)
- **FR1.8** → ST1.2 (rotation), ST1.6 (rotation no loss)
- **FR1.9** → UT1.8 (logger factory)
- **FR1.10** → UT1.6 (audit event helpers)
- **FR1.11** → ST1.4 (log level config)
- **FR1.12** → UT1.9 (health reporter)
- **FR1.13** → UT1.11 (secret scan), UT1.3 (redaction)
- **FR1.14** → ST1.3 (append-only audit)
- **FR1.15** → IT1.1 (FastAPI middleware), IT1.3 (request logging)
- **FR1.16** → AT1.1 (config via platform config)
- **FR1.17** → UT1.10 (backward compat setup_logger)
- **FR1.18** → UT1.12 (audit sink interface), UT1.13 (file sink), UT1.14 (stdout sink), UT1.15 (fan-out sink), AT1.4 (database sink pattern)
- **FR1.19** → UT1.16 (audit signing), AT1.5 (signed audit chain)
- **FR1.20** → UT1.17 (tool event helper)
- **FR1.21** → UT1.18 (redaction presets)
- **FR1.22** → UT1.19 (log sampling)
- **FR1.23** → UT1.20 (audit batching)
- **FR1.24** → UT1.21 (exception serialisation)
- **FR1.25** → UT_IntegrityVerifier (hash computation and records), ST_IntegrityVerifier (periodic runtime checks)
- **FR1.26** → ST_RotationEnforcement (config parsing), UT_IntegrityVerifier (algorithm variants)
- **FR1.27** → ST_RotationEnforcement (rotation event + compression), ST_IntegrityVerifier (rotation trigger baseline)

### Non-Functional
- **NF1.1** → Dependency audit (stdlib only for core)
- **NF1.2** → AT1.3 (high volume — logging overhead benchmark)
- **NF1.3** → UT1.4 (async-safety of contextvars correlation)
- **NF1.4** → CI matrix (Python 3.10, 3.11, 3.12)

### Cyber Security
- **CS1.1** → UT1.3 (redaction), UT1.11 (secret scan)
- **CS1.2** → ST1.3 (append-only)
- **CS1.3** → UT1.4 (correlation ID contains no secrets)
- **CS1.4** → UT1.3 (PII redaction patterns)

---

## Unit Tests (UT) — Selected Detail

### UT1.1: JSON Formatter
- **Scope**: Structured JSON Lines output
- **What is being tested**: All required fields present; one JSON object per line; exception serialisation; extra fields included; no secrets in output
- **Related Requirements**: FR1.2
- **Related Architecture**: CC1.6

### UT1.3: Redaction Engine
- **Scope**: Secret and PII redaction
- **What is being tested**: Default patterns (password, key, token, secret, credential); custom patterns; nested dict scanning; list scanning; value replacement with `***REDACTED***`; PII patterns
- **Related Requirements**: FR1.6, FR1.13, CS1.1, CS1.4
- **Related Architecture**: CC1.5

### UT1.4: Correlation ID
- **Scope**: Context-local correlation ID
- **What is being tested**: Generate new ID; set/get in same context; propagate across async tasks; isolation between requests; header extraction
- **Related Requirements**: FR1.5, NF1.3, CS1.3
- **Related Architecture**: CC1.4

### UT1.5: Audit Event Schema
- **Scope**: Audit event validation
- **What is being tested**: All required fields enforced; optional fields accepted; invalid events rejected; timestamp format; actor structure; outcome enum
- **Related Requirements**: FR1.3
- **Related Architecture**: CC1.3

### UT1.6: Audit Logger
- **Scope**: Typed audit event emission
- **What is being tested**: log_login, log_crud, log_config_change, log_tool_call, log_security — each generates correct event_type; details field redacted before writing; correlation_id attached
- **Related Requirements**: FR1.3, FR1.10
- **Related Architecture**: CC1.2

### UT1.10: Backward Compatibility
- **Scope**: setup_logger() compatibility
- **What is being tested**: Function signature matches existing pattern; returns stdlib Logger; respects log_file, log_level, log_format, console params; JSON and text format modes
- **Related Requirements**: FR1.17
- **Related Architecture**: CC1.9

### UT1.11: Secret Scan Guard
- **Scope**: Ensure no secrets in log output
- **What is being tested**: Inject known secret patterns into log calls → verify they are redacted in output; test with nested dicts; test with audit event details
- **Related Requirements**: FR1.13, CS1.1
- **Related Architecture**: CC1.5

### UT1.12: Audit Sink Interface
- **Type**: UT
- **Scope**: AuditSink protocol compliance
- **What is being tested**: Protocol defines emit/flush/close; custom sink implementing protocol works with AuditLogger; invalid sink rejected
- **Related Requirements**: FR1.18
- **Related Architecture**: CC1.11

### UT1.13: File Sink
- **Type**: UT
- **Scope**: FileSink JSONL output
- **What is being tested**: Events written as JSONL; append-only; flush writes to disk; close finalises file; rotation compatible
- **Related Requirements**: FR1.18
- **Related Architecture**: CC1.11

### UT1.14: Stdout Sink
- **Type**: UT
- **Scope**: StdoutSink output
- **What is being tested**: Events written to stdout; JSON format; captured in test; flush is no-op
- **Related Requirements**: FR1.18
- **Related Architecture**: CC1.11

### UT1.15: Fan-Out Sink
- **Type**: UT
- **Scope**: FanOutSink dispatches to multiple sinks
- **What is being tested**: Event dispatched to all registered sinks; one sink failure does not block others; flush/close propagated to all
- **Related Requirements**: FR1.18
- **Related Architecture**: CC1.11

### UT1.16: Audit Signing
- **Type**: UT
- **Scope**: HMAC signing hooks
- **What is being tested**: pre_persist adds signature field; post_persist updates hash chain; disabled by default; HMAC-SHA256 signature verifiable; signing with no key raises error
- **Related Requirements**: FR1.19
- **Related Architecture**: CC1.12

### UT1.17: Tool Event Helper
- **Type**: UT
- **Scope**: log_tool_event convenience function
- **What is being tested**: Generates audit event with event_type="tool_call"; tool, profile, duration_ms, paths in details; correlation_id attached; details redacted
- **Related Requirements**: FR1.20
- **Related Architecture**: CC1.13

### UT1.18: Redaction Presets
- **Type**: UT
- **Scope**: Composable redaction presets
- **What is being tested**: Default preset masks standard keys; file_tools preset masks additional keys; custom preset from config; multiple presets compose; unknown preset name raises error
- **Related Requirements**: FR1.21
- **Related Architecture**: CC1.14

### UT1.19: Log Sampling
- **Type**: UT
- **Scope**: Per-logger DEBUG sampling
- **What is being tested**: DEBUG entries sampled at configured rate; WARNING+ always passes; audit events unaffected; sampled-out entries counted; rate=1.0 passes all; rate=0.0 drops all DEBUG
- **Related Requirements**: FR1.22
- **Related Architecture**: CC1.15

### UT1.20: Audit Batching
- **Type**: UT
- **Scope**: BatchingSink flush semantics
- **What is being tested**: Events buffered until batch_size reached; flush_interval triggers flush; shutdown flushes remaining; ordering preserved; inner sink receives correct batches
- **Related Requirements**: FR1.23
- **Related Architecture**: CC1.16

### UT1.21: Exception Serialisation
- **Type**: UT
- **Scope**: format_exception utility
- **What is being tested**: Returns type, message, stack_hash, traceback; stack_hash is SHA-256; same exception produces same hash; different exceptions produce different hashes; nested exceptions handled
- **Related Requirements**: FR1.24
- **Related Architecture**: CC1.17

---

## System Tests (ST)

### ST1.1: Two Stream Output
- **Scope**: Verify audit and application logs are separate streams
- **What is being tested**: App log writes to app.log; audit writes to audit.log.jsonl; no cross-contamination; both in JSON Lines format
- **Related Requirements**: FR1.1

### ST1.2: File Rotation
- **Scope**: Size and time-based rotation
- **What is being tested**: File rotated at configured size; backup files created; retention policy enforced (old files deleted); configured via env
- **Related Requirements**: FR1.8

### ST1.3: Append-Only Audit
- **Scope**: Audit log append-only semantics
- **What is being tested**: Audit handler opens in append mode; writing multiple events preserves all; rotation preserves older entries; no truncation
- **Related Requirements**: FR1.14, CS1.2

### ST1.4: Log Level Configuration
- **Scope**: Per-logger level overrides
- **What is being tested**: Global level from config; per-logger override (e.g., sqlalchemy=WARNING); level change via reload
- **Related Requirements**: FR1.11

### ST1.5: Dual Destination
- **Scope**: File + stdout simultaneously
- **What is being tested**: Entries appear in both file and captured stdout; format consistent; configurable per stream
- **Related Requirements**: FR1.7

### ST1.6: Rotation No Loss
- **Scope**: No log entries lost during rotation
- **What is being tested**: Write 10,000 entries; trigger rotation mid-stream; count total entries across all files = 10,000
- **Related Requirements**: FR1.8

---

## Integration Tests (IT)

### IT1.1: FastAPI Middleware
- **Scope**: Request logging middleware with FastAPI
- **What is being tested**: Request logged with method, path, status, duration, client IP; correlation ID injected; response header X-Request-Id set
- **Related Requirements**: FR1.15

### IT1.2: Correlation ID Propagation
- **Scope**: Correlation ID flows through request lifecycle
- **What is being tested**: Incoming X-Request-Id used; missing header → generated; all log entries in request share same ID; nested async calls share ID
- **Related Requirements**: FR1.5

### IT1.3: Request/Response Logging
- **Scope**: Full request/response logging cycle
- **What is being tested**: Success request logged; error request logged with exception; duration_ms accurate; no secrets in logged headers
- **Related Requirements**: FR1.15

---

## Application Tests (AT)

### AT1.1: Service Startup Pattern
- **Scope**: Simulate real service startup using cloud_dog_logging
- **What is being tested**: setup_logging(config) → two streams active; get_logger returns configured logger; get_audit_logger returns audit logger; config from GlobalConfig

### AT1.2: Audit Event Coverage
- **Scope**: Verify audit events for all critical actions
- **What is being tested**: Simulate login, CRUD, config change, tool call → verify each generates audit event with correct schema

### AT1.3: High Volume Logging
- **Scope**: Performance under load
- **What is being tested**: 10,000 log entries in < 5 seconds; logging overhead < 1ms per entry; no entries lost; rotation handles volume

### AT1.4: Database Sink Pattern
- **Type**: AT
- **Scope**: Simulate DB audit sink usage
- **What is being tested**: DatabaseSink with mock repository; events persisted to mock DB; fan-out with FileSink + DatabaseSink; batching with DatabaseSink; failure in DB sink does not lose events (logged to fallback)
- **Related Requirements**: FR1.18, FR1.23
- **Related Architecture**: CC1.11, CC1.16

### AT1.5: Signed Audit Chain
- **Type**: AT
- **Scope**: End-to-end signed audit trail
- **What is being tested**: Enable signing in config; emit multiple audit events; verify each has signature field; verify hash chain is intact; tampered event detected
- **Related Requirements**: FR1.19
- **Related Architecture**: CC1.12

---

## Test Run History

| Date (UTC) | Scope | Command | Status | Notes |
|------------|-------|---------|--------|-------|
| 2026-02-18 | Uplift targeted scope | `pytest tests/unit/UT1.12_AuditSinkInterface tests/unit/UT1.13_FileSink tests/unit/UT1.14_StdoutSink tests/unit/UT1.15_FanOutSink tests/unit/UT1.16_AuditSigning tests/unit/UT1.17_ToolEventHelper tests/unit/UT1.18_RedactionPresets tests/unit/UT1.19_LogSampling tests/unit/UT1.20_AuditBatching tests/unit/UT1.21_ExceptionSerialisation tests/application/AT1.4_DatabaseSinkPattern tests/application/AT1.5_SignedAuditChain --env tests/env-UT -q` | PASS | 33 passed, 0 failed, 0 skipped |
| 2026-02-18 | Full package matrix (UT env) | `pytest tests --env tests/env-UT -q` | PASS | 201 passed, 0 failed, 0 skipped |
| 2026-02-18 | Full package matrix (IT env) | `pytest tests --env tests/env-IT -q` | PASS | 201 passed, 0 failed, 0 skipped |
| 2026-02-18 | Lint | `ruff check cloud_dog_logging tests` | PASS | All checks passed |
| 2026-02-18 | Format check | `ruff format --check cloud_dog_logging tests` | PASS | 68 files already formatted |
| 2026-02-18 | Build artefacts | `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/packages/backend/platform-config/.venv/bin/python -m build --no-isolation` | PASS | `cloud_dog_logging-0.3.0.tar.gz` + `cloud_dog_logging-0.3.0-py3-none-any.whl` |
| 2026-02-17 | Full package matrix | `pytest tests --env tests/env-IT -q` | PASS | 168 passed, 0 failed, 0 skipped |
| 2026-02-17 | Lint | `ruff check cloud_dog_logging tests` | PASS | All checks passed |
| 2026-02-17 | Format check | `ruff format --check cloud_dog_logging tests` | PASS | 44 files already formatted |
| 2026-02-17 | Build artefacts | `python -m build` | PASS | sdist + wheel produced in `dist/` |
| 2026-02-17 | Wheel install + import | `python3 -m venv /tmp/cloud_dog_ai_log_wheel_<id> && pip install dist/cloud_dog_logging-0.1.1-py3-none-any.whl && python -c "import cloud_dog_logging"` | PASS | Wheel installs and package imports successfully in isolated venv |

---

## Latest Verified Run

| Date (UTC) | Scope | Command | Status | Notes |
|------------|-------|---------|--------|-------|
| 2026-02-18 | Full package matrix (IT env) | `pytest tests --env tests/env-IT -q` | PASS | 201 passed, 0 failed, 0 skipped |
