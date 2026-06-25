# Changelog

## 0.4.0 - 2026-05-04

Added the public extension surface that lets services delete bespoke
`logger.py` wrappers (RULES §1.4 closure path):

- **LogRecord factory hook** — exported `register_log_field_provider`,
  `unregister_log_field_provider`, `clear_log_field_providers`,
  `get_registered_field_providers`, and the `FieldProvider` type alias from
  the package root. The previous behaviour (which lived in
  `cloud_dog_logging.field_providers` but was unreachable through the public
  API) is now first-class. Reserved-name collision protection and idempotent
  factory installation are unchanged.
- **JSONFormatter field hook** — added
  `cloud_dog_logging.add_json_field(name, provider)`,
  `remove_json_field(name)`, `clear_json_fields()`, and
  `get_registered_json_fields()`. Registered providers receive the
  `LogRecord` and contribute additional top-level fields to every JSON line
  produced by `JSONFormatter`. Stable schema field names cannot be
  overridden. Provider exceptions are swallowed and the field is omitted —
  a faulty provider can never break the logging path.
- **HandlerType enum** — re-exported `cloud_dog_logging.HandlerType`
  (`FILE`, `CONSOLE`, `DUAL`, `ROTATING`). `setup_logging` now honours
  `LogConfig.handlers` (declarative list of `HandlerType` members or their
  string values) — when supplied, the listed kinds drive handler creation
  while the legacy `app_log_file` / `console_output` knobs still apply as
  guards. `LogConfig.from_dict` now correctly threads the `handlers` and
  `extra_fields` keys through to the dataclass instance (previously read
  from config but silently dropped before reaching the constructor).
- `setup_logging` also now passes `LogConfig.extra_fields` to the
  `JSONFormatter` constructor so per-service top-level promotion of
  field-provider attributes is configurable purely through the platform
  config.

Backwards-compatibility: every change is purely additive. Existing services
that do not supply `log.handlers` or `log.extra_fields` see identical
behaviour to 0.3.4.

## 0.3.4 - 2026-04-05
- Added `trace_id` and `request_id` emission in the audit schema and audit logger defaults.
- Normalised audit middleware actor roles from `roles` and `groups`, propagated `user-agent`, and enforced default actor role/IP fields in package-managed audit payloads.
- Bound integrity verifier app-log emissions to the configured service name, service instance, and environment.
- Enforced `0700` permissions on log directories and `0600` on audit and integrity files, while preserving `0644` for application log files.

## 0.3.1 - 2026-03-25
- Added public publication documentation set for package release readiness.
- Normalised package ignore rules for working, private, archive, logs, dist, and database artefacts.
- Reviewed source for publish-safety blockers.
