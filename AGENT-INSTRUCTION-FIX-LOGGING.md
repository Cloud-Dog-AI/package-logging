# Agent Instruction — Fix cloud_dog_logging (v0.2.0)

**Package:** `cloud_dog_logging`
**Target version:** 0.2.0
**Date:** 2026-02-18 (updated with full gap analysis)
**Scope:** 7 new features (FR1.18–FR1.24) — **ALL DELIVERED AND VERIFIED**

---

## Status: ✅ COMPLETE

All 7 issues from cross-project impact assessment have been implemented, tested, and verified. This document is retained for reference and future maintenance.

**Verified on 2026-02-18:**
- 201 tests passed (IT env), 0 failed, 0 skipped
- Uplift scope: 33 passed (targeted v0.2.0 tests)
- Lint and format clean (`ruff check` + `ruff format --check`)
- Build produces `cloud_dog_logging-0.2.0.tar.gz` + `cloud_dog_logging-0.2.0-py3-none-any.whl`
- All 32 SA1 modules present
- All 35 test directories present and matching TESTS.md (21 UT + 6 ST + 3 IT + 5 AT)
- Zero config-delegation violations (no `os.environ`/`hvac`/Vault reads)

**Governing documents:**
1. `platform-logging/REQUIREMENTS.md` (v0.2.0) — FR1.18–FR1.24
2. `platform-logging/ARCHITECTURE.md` (v0.2.0) — CC1.11–CC1.17
3. `platform-logging/TESTS.md` (v0.2.0) — UT1.12–UT1.21, AT1.4–AT1.5
4. `packages/backend/AGENT-INSTRUCTION.md` — Integrity Warranty and Config Delegation — ZERO TOLERANCE (MANDATORY)

---

## Delivery Summary

### Issue 1 — Pluggable Audit Sink ✅ DELIVERED

**FR:** FR1.18 | **Architecture:** CC1.11 | **Tests:** UT1.12–UT1.15, AT1.4

- `cloud_dog_logging/sinks/base.py` — `AuditSink` protocol (`emit`, `flush`, `close`) + `AuditRepository` protocol for DB sinks
- `cloud_dog_logging/sinks/file_sink.py` — `FileSink` JSONL file output
- `cloud_dog_logging/sinks/stdout_sink.py` — `StdoutSink` stdout output
- `cloud_dog_logging/sinks/db_sink.py` — `DatabaseSink` via `AuditRepository` protocol
- `cloud_dog_logging/sinks/fan_out.py` — `FanOutSink` multi-sink dispatch (one failure doesn't block others)
- `audit_logger.py` refactored to accept `sink` and `signer` parameters
- `__init__.py` → `_build_audit_sink()` wires sinks from `LogConfig`

---

### Issue 2 — Audit Signing Hooks ✅ DELIVERED

**FR:** FR1.19 | **Architecture:** CC1.12 | **Tests:** UT1.16, AT1.5

- `cloud_dog_logging/signing.py` — `AuditSigner` protocol + `HMACSigner` (HMAC-SHA256 with hash chaining)
- `pre_persist`: adds `_signature` and `_prev_signature` to event details
- `post_persist`: updates chain with latest signature
- Integrated into `AuditLogger` via `signer` parameter; `_build_signer()` in `__init__.py`

---

### Issue 3 — Tool Event Helper ✅ DELIVERED

**FR:** FR1.20 | **Architecture:** CC1.13 | **Tests:** UT1.17

- `cloud_dog_logging/tool_events.py` — `log_tool_event(tool, profile, duration_ms, paths, outcome, **details)`
- Generates `AuditEvent` with `event_type="tool_call"`, auto-attaches correlation ID and service name
- Exported from `__init__.py`

---

### Issue 4 — Redaction Presets ✅ DELIVERED

**FR:** FR1.21 | **Architecture:** CC1.14 | **Tests:** UT1.18

- `cloud_dog_logging/presets.py` — `RedactionPreset` frozen dataclass, `BUILTIN_PRESETS` dict (`default` + `file_tools`), `load_presets(config)` with config-driven composition
- `RedactionEngine` accepts `presets` parameter
- `setup_logging()` resolves presets from config via `_resolve_redaction_presets()`

---

### Issue 5 — Log Sampling ✅ DELIVERED

**FR:** FR1.22 | **Architecture:** CC1.15 | **Tests:** UT1.19

- `cloud_dog_logging/sampling.py` — `SamplingFilter(logging.Filter)` with per-logger rates, hierarchical name lookup, `sampled_out_count` metric
- WARNING+ always passes; audit events unaffected
- Wired into `setup_logging()` via `LogConfig.sampling_rates`

---

### Issue 6 — Audit Event Batching ✅ DELIVERED

**FR:** FR1.23 | **Architecture:** CC1.16 | **Tests:** UT1.20

- `cloud_dog_logging/batching.py` — `BatchingSink` wrapping any `AuditSink` with configurable `batch_size` (default 100) and `flush_interval_s` (default 5.0)
- Thread-safe with `threading.Lock`; ordering preserved; flush on batch full/interval/close
- Supports `emit_batch()` on underlying sink if available

---

### Issue 7 — Structured Exception Logging ✅ DELIVERED

**FR:** FR1.24 | **Architecture:** CC1.17 | **Tests:** UT1.21

- `cloud_dog_logging/exceptions.py` — `format_exception(exc)` returning `type`, `message`, `stack_hash` (SHA-256), `traceback` (list of frame strings)
- Stable `stack_hash` enables deduplication across identical exceptions
- Exported from `__init__.py`

---

## Public API Exports

All new APIs exported from `cloud_dog_logging/__init__.py`:
- `log_tool_event`, `format_exception`
- `AuditSink`, `FileSink`, `StdoutSink`, `DatabaseSink`, `FanOutSink`
- `BatchingSink`, `HMACSigner`
- `RedactionPreset`, `BUILTIN_PRESETS`, `load_presets`
- `SamplingFilter`

---

## Verification — Full Suite

```bash
pytest tests --env tests/env-IT -q
ruff check cloud_dog_logging tests
ruff format --check cloud_dog_logging tests
python -m build --no-isolation
find cloud_dog_logging -name '*.py' -not -path '*__pycache__*' | sort
```

## pyproject.toml version

```toml
version = "0.2.0"
```
