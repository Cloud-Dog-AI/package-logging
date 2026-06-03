# cloud_dog_logging PS-40 v2 Gaps

Source lane: W28A-619  
Status: Documentation-only gap note. No source changes made in this lane.

The full package gap matrix is recorded at:

```text
cloud-dog-ai-platform-standards/working/evidence/W28A-619-log-standards-review/02-cloud-dog-log-gap-matrix.md
```

## Summary

- Total reviewed rows: 47
- Block rows: 5
- Major rows: 34
- Minor rows: 4
- Present/no-gap rows: 4

## Blockers Before PS-40 v2 Runtime Adoption

| Gap | Evidence | Required fix lane |
|---|---|---|
| No canonical `span_id` context model/formatter/schema. | `audit_schema.py:138-160`, `json_formatter.py:251-260`, `correlation.py:32-58` | W28A-XYZ |
| No per-surface API/WebUI/MCP/A2A handler/file configuration. | `config.py:56-93`, `__init__.py:198-223`, `__init__.py:359-382` | W28A-XYZ |
| No `<service>.<surface>.log` path derivation from `log.dir`. | `config.py:61-63`, `__init__.py:200-223`, `__init__.py:364-375` | W28A-XYZ |
| No outbound `X-Correlation-Id` / W3C `traceparent` injection helper. | `correlation.py:32-58` plus package source inspection | W28A-XYZ |
| No job envelope helper for lifecycle correlation inheritance. | `correlation.py:32-58` plus package source inspection | W28A-XYZ |

## Follow-on W28A-XYZ Must Cover

1. Emit the complete PS-40 v2 canonical field set in both application and audit entries.
2. Add per-surface file topology and `log.dir`-based path derivation.
3. Add W3C trace context support including `trace_id`, `span_id`, inbound parsing, outbound forwarding, and job inheritance.
4. Add explicit redaction presets for JWT, Vault token, OAuth token, API key, password, session cookie, and PII classes.
5. Add automatic audit sub-channel routing for SECURITY/AUDIT/auth/rbac/config/security/denied/error events.
6. Add forbidden-pattern lint helper and PS-40 v2 conformance tests.
7. Update README, REQUIREMENTS, TESTS, and usage docs, then build/test/publish with evidence.
