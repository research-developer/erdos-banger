# DEBT-036: Marker PDF Converter Not Configured for MPS

**Status:** Open
**Severity:** Low (performance optimization)
**Found:** 2026-01-21
**Found By:** Post-Ralph adversarial audit

---

## Summary

The SPEC-019 PDF conversion implementation uses Marker but does not configure it to use Apple Silicon MPS (Metal Performance Shaders) GPU acceleration. On Mac M1/M2/M3/M4 machines, Marker defaults to CPU, leaving significant performance on the table.

## Current State

`src/erdos/core/pdf_converter.py` does not set `TORCH_DEVICE=mps` or configure Marker's GPU settings.

## Evidence

From [marker-pdf PyPI documentation](https://pypi.org/project/marker-pdf/):

> On ARM Macs (M1+), you need to set the `TORCH_DEVICE` setting to `mps` for a speedup.

From [PyTorch MPS documentation](https://developer.apple.com/metal/pytorch/):

> MPS backend enables GPU acceleration on Apple Silicon through Apple's Metal framework.

## Fix Required

### Option A: Environment Variable (Recommended)

Document that users should set:
```bash
export TORCH_DEVICE=mps  # For Apple Silicon
export INFERENCE_RAM=16  # Adjust to your unified memory
```

### Option B: Runtime Detection

Add auto-detection in `pdf_converter.py`:

```python
import platform
import torch

def _get_torch_device() -> str:
    """Detect best available torch device."""
    if torch.cuda.is_available():
        return "cuda"
    if platform.system() == "Darwin" and platform.processor() == "arm":
        # Apple Silicon - check MPS availability
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    return "cpu"
```

### Option C: CLI Flag

Add `--device` option to `erdos convert`:
```bash
erdos convert paper.pdf --device mps
```

## Caveats

Per [PyTorch MPS documentation](https://pytorch.org/blog/introducing-accelerated-pytorch-training-on-mac/):

1. **FP16 not supported** - MPS does not support 16-bit floating-point; Marker may need `fp16=False`
2. **Experimental** - Not all PyTorch ops are MPS-optimized
3. **Memory requirements** - 16GB+ unified memory recommended, 32GB+ preferred

## Acceptance Criteria

1. [ ] Document MPS configuration in CLAUDE.md or README
2. [ ] Add `--device` option to `erdos convert` command
3. [ ] Test on Apple Silicon machine with `TORCH_DEVICE=mps`
4. [ ] Handle graceful fallback if MPS fails

## Testing

```bash
# On Apple Silicon Mac
TORCH_DEVICE=mps uv run erdos convert test.pdf -o test.md
# Should complete faster than CPU
```

---

## References

- [marker-pdf PyPI](https://pypi.org/project/marker-pdf/)
- [PyTorch MPS Backend](https://developer.apple.com/metal/pytorch/)
- [Accelerated PyTorch on Mac](https://pytorch.org/blog/introducing-accelerated-pytorch-training-on-mac/)
