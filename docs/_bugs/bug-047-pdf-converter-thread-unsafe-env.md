# BUG-047: PDF Converter Thread-Unsafe Environment Mutation

**Priority:** P1
**Status:** Open
**Found:** 2026-01-27
**Component:** `src/erdos/core/pdf/converter.py`

## Description

The PDF converter mutates `os.environ` directly to set `TORCH_DEVICE` before conversion. This is thread-unsafe and can cause race conditions in concurrent conversions.

## Steps to Reproduce

1. Run two concurrent PDF conversions with different `torch_device` settings
2. The second conversion may use the first's `TORCH_DEVICE` setting

## Evidence

```python
# src/erdos/core/pdf/converter.py:395-419
original_torch_device = os.environ.get("TORCH_DEVICE")
try:
    os.environ["TORCH_DEVICE"] = config.torch_device  # RACE CONDITION!
    # ... conversion code ...
finally:
    os.environ.pop("TORCH_DEVICE", None)
    if original_torch_device is not None:
        os.environ["TORCH_DEVICE"] = original_torch_device
```

## Expected Behavior

Each conversion should use its own `TORCH_DEVICE` setting without affecting other concurrent conversions.

## Actual Behavior

Global `os.environ` is mutated, causing race conditions between concurrent conversions.

## Root Cause

Direct mutation of global `os.environ` without synchronization. The Marker library is imported and runs **in-process** (not via subprocess), so `env=` parameter passing is not applicable.

## Recommended Fix

**Option A: Threading Lock (Recommended)**

```python
import threading

_torch_device_lock = threading.Lock()

def convert_pdf(...) -> MarkdownResult:
    # ...
    with _torch_device_lock:  # Serialize access to os.environ
        original_torch_device = os.environ.get("TORCH_DEVICE")
        try:
            if config.torch_device is not None:
                os.environ["TORCH_DEVICE"] = config.torch_device
            # ... conversion code (Marker runs here) ...
        finally:
            if config.torch_device is not None:
                if original_torch_device is None:
                    os.environ.pop("TORCH_DEVICE", None)
                else:
                    os.environ["TORCH_DEVICE"] = original_torch_device
```

**Option B: Marker Config Injection (if supported)**

Check if Marker's `ConfigParser` or `PdfConverter` accept device configuration directly, avoiding `os.environ` mutation entirely:

```python
# Check Marker API for device parameter
converter_kwargs = {"torch_device": config.torch_device}  # If supported
```

**Why subprocess.run doesn't apply:** The original fix proposal assumed subprocess usage, but Marker is imported directly:
```python
from marker.config.parser import ConfigParser
from marker.models import create_model_dict
```
The conversion happens in-process, not in a subprocess.

## Impact

- High: Could cause incorrect device selection in production
- Affects: Multi-threaded/async PDF conversion workflows
- Workaround: Run conversions sequentially (performance impact)

## Related

- DEBT-114: Hardcoded relative paths (same module)
- AUDIT-011: Thread-unsafe environment mutation
