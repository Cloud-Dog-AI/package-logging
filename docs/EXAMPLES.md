# cloud_dog_logging Examples

## Configure logging
```python
from cloud_dog_logging import setup_logging

setup_logging(config)
```

## Emit an audit event
```python
from cloud_dog_logging import get_audit_logger

audit = get_audit_logger()
audit.log_event("login", outcome="success")
```
