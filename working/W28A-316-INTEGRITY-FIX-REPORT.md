# W28A-316 Integrity Fix Report

Date: 2026-03-24 UTC
Verdict: PASS

## Scope

Package:
- `/opt/iac/Development/cloud-dog-ai/cloud-dog-ai-platform-standards/packages/backend/platform-logging/`

Objective:
- fix `ValueError: I/O operation on closed file` emitted by `cloud_dog_logging.integrity` during late pytest shutdown

## Root Cause

`AuditIntegrityVerifier.stop()` writes a final shutdown integrity record.
That write path logs through `cloud_dog_logging.integrity` before appending to the dedicated integrity file.
When pytest or interpreter shutdown has already closed effective stream handlers, the logger emission path can hit a closed stream and trigger noisy shutdown errors.

## Changes Made

Files changed:
- `cloud_dog_logging/integrity.py`
- `tests/unit/UT_IntegrityVerifier/test_integrity_verifier.py`
- `pyproject.toml`

Implementation changes:
- added `_can_emit_to_logger()` to inspect effective logger handlers and skip app-log emission when handler streams are already closed
- wrapped the integrity logger write in `try/except (OSError, ValueError)` as a final shutdown safety guard
- retained dedicated integrity-file append behavior so shutdown integrity records are still persisted even if app-log handlers are gone
- added regression test `test_compute_now_skips_closed_logger_stream`
- bumped package version from `0.3.0` to `0.3.1`

## Verification

### Full package tests

Command:
```bash
source .venv/bin/activate
python3 -m pytest tests/ --env UT -q --tb=short 2>&1 | tee working/w28a-316-tests.log
```

Result:
- `226 passed in 11.80s`

Evidence:
- `working/w28a-316-tests.log`

### Closed-file shutdown noise check

Search:
```bash
grep -n "ValueError: I/O operation on closed file\|closed file" working/w28a-316-tests.log
```

Result:
- no matches

### Package build

Command:
```bash
source .venv/bin/activate
python -m build --no-isolation 2>&1 | tee working/w28a-316-build.log
```

Result:
- built successfully:
  - `dist/cloud_dog_logging-0.3.1.tar.gz`
  - `dist/cloud_dog_logging-0.3.1-py3-none-any.whl`

Evidence:
- `working/w28a-316-build.log`

## Publish

Command used:
```bash
python -m twine upload --repository-url https://pypi.cloud-dog.net/ -u "$TWINE_USERNAME" -p "$TWINE_PASSWORD" dist/cloud_dog_logging-0.3.1*
```

Result:
- published successfully:
  - `cloud_dog_logging-0.3.1-py3-none-any.whl`
  - `cloud_dog_logging-0.3.1.tar.gz`

Credential source:
- credentials resolved from `dev.repository.pypi` in the Vault-backed config content

Evidence:
- `working/w28a-316-publish.log`
- `working/w28a-316-index-check.log`

Index verification:
- `cloud-dog-logging (0.3.1)`
- `LATEST: 0.3.1`

## Pass Criteria Check

- `ValueError: I/O operation on closed file` no longer occurs in package test run: PASS
- package tests green: PASS
- report written: PASS

## Follow-up

No further package action is required for W28A-316.
