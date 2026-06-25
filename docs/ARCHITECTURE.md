# cloud_dog_logging Architecture

## Purpose
`cloud_dog_logging` provides shared application and audit logging utilities for Cloud-Dog Python services.

## Main responsibilities
- configure structured application logging
- emit audit events through a consistent schema
- apply redaction, correlation, batching, and sink fan-out
- support framework integration without bespoke logger setup per project

## Main components
- logger setup and compatibility helpers
- audit schema and emitters
- sinks for file, stdout, database, and fan-out delivery
- middleware and context helpers for correlation propagation
