# DEBT-036: Marker PDF Converter Device Selection Not Exposed

**Status:** Open
**Severity:** P3 (performance/DevX; not a correctness bug)
**Found:** 2026-01-21
**Found By:** Post-Ralph adversarial audit

---

## Summary

The SPEC-019 PDF conversion implementation uses Marker but does not provide a first-class way to select the underlying torch device (CPU/CUDA/MPS). This is primarily a **performance/DevX** issue for contributors on Apple Silicon or GPU machines.

## Current State

`src/erdos/core/pdf_converter.py` does not set `TORCH_DEVICE` and the CLI does not expose a `--torch-device` (or equivalent) knob. Users must discover/remember the environment-variable override themselves.

## Evidence

From Marker’s upstream docs (repo README):

> The torch device will be automatically detected, but you can override this by setting the `TORCH_DEVICE` environment variable.

From [PyTorch MPS documentation](https://developer.apple.com/metal/pytorch/):

> MPS backend enables GPU acceleration on Apple Silicon through Apple's Metal framework.

## Fix Required

### Option A: Documentation-only (Lowest effort)

Document that users should set:
```bash
export TORCH_DEVICE=mps  # Apple Silicon (if supported by your PyTorch build)
export TORCH_DEVICE=cuda # NVIDIA
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

### Option C: CLI Flag (Best DX)

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

1. [ ] Document `TORCH_DEVICE` configuration in README (or vendor docs link)
2. [ ] (Optional) Add `--device` option to `erdos convert` (maps to `TORCH_DEVICE`)
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

- [Marker docs](https://github.com/datalab-to/marker)
- [PyTorch MPS Backend](https://developer.apple.com/metal/pytorch/)
- [Accelerated PyTorch on Mac](https://pytorch.org/blog/introducing-accelerated-pytorch-training-on-mac/)
