# 12 — Security Policy

This document defines the core security mechanisms, sandboxing strategies, and configurations required to protect data and execution logic.

---

## 1. Plugin Subprocess Sandboxing

Plugins running custom Python scripts execute inside a restricted subprocess runner to isolate execution bounds:

```python
# Conceptual implementation of plugin subprocess containment
import subprocess
import sys

def execute_plugin_sandboxed(handler_path: str, payload_json: str):
    # Run helper script with reduced process privileges using preexec_fn (e.g., setuid/setgid to nobody user)
    # Redirect stdin/stdout/stderr for JSON communication
    proc = subprocess.Popen(
        [sys.executable, "-m", "app.engines.sandbox_executor", handler_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=drop_privileges
    )
    stdout, stderr = proc.communicate(input=payload_json, timeout=10)
    return stdout, stderr
```
* **Sandbox Restrictions**:
  - Drops POSIX process permissions to user `nobody`.
  - Disables standard system builtins (`open`, `eval`, `exec`, `importlib`) by injecting a custom import hook.
  - Resource usage is capped at 50MB RAM and 2 seconds of CPU runtime.

---

## 2. File Upload Validation

All user-submitted uploads must comply with verification logic:
1. **Size check**: Capped per MIME-type in `system_config` (e.g. 10MB images, 50MB PDFs).
2. **MIME type detection**: Validated using content-header signatures (not file extensions).
3. **Malware scanning**: Submissions are routed to ClamAV via a local unix socket.
4. **Failsafe Storage**: Files are saved with a UUID name outside the web server document root directory.

---

## 3. Webhook HMAC Validation

Third-party endpoints receiving callbacks from the platform verify payload origin using an HMAC header:

```python
import hmac
import hashlib

def compute_signature(payload_bytes: bytes, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
```
The client verifies the payload is authentic by comparing this signature with the value in the `X-FBP-Signature` HTTP header.
