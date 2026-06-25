# cloud_dog_logging Configuration

## Typical inputs
Consumer services configure this package through their own config models.
Common settings include:
- application log level
- audit log path
- JSON formatting enablement
- retention and rotation limits
- redaction presets
- sink selection

## Guidance
- keep log destinations outside the package source tree
- redact secrets before persistence
- separate audit and application streams
