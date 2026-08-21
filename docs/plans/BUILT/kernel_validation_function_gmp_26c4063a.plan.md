---
name: Kernel Validation Function GMP
overview: Add the `validate_packet_protocol_rules()` function to kernel_loader.py and export it from runtime module, without changing any existing file paths.
todos:
  - id: add-function
    content: Add validate_packet_protocol_rules() function to runtime/kernel_loader.py
    status: completed
  - id: export-kernel-loader
    content: Add function to __all__ in kernel_loader.py
    status: completed
  - id: export-runtime-init
    content: Add import and export in runtime/__init__.py
    status: completed
  - id: verify
    content: Test the function loads and validates kernels correctly
    status: completed
---

# Add Kernel Packet Protocol Validation Function

## Objective

Add `validate_packet_protocol_rules()` function to validate that the runtime kernel load order matches the authoritative `10_packet_protocol_kernel.yaml` specification. This addresses the Codex audit finding about missing kernel order enforcement.

## Scope

| File | Action |

|------|--------|

| [runtime/kernel_loader.py](runtime/kernel_loader.py) | Add function + add to `__all__` |

| [runtime/__init__.py](runtime/__init__.py) | Add to imports and `__all__` exports |

## What Will NOT Change

- `DEFAULT_KERNEL_PATH` stays as `"private"` (kernels exist at `private/kernels/00_system/`)
- No file moves or path changes
- No changes to existing kernel loading logic

## Implementation Details

### 1. Add function to kernel_loader.py (after line ~950)

```python
def validate_packet_protocol_rules() -> dict[str, Any]:
    """
    Validate kernel load order against 10_packet_protocol_kernel.yaml.

    Returns:
        dict with keys: valid (bool), expected_order (list), actual_order (list), mismatches (list)
    """
    kernel_path = Path(DEFAULT_KERNEL_PATH) / "kernels" / "00_system" / "10_packet_protocol_kernel.yaml"

    if not kernel_path.exists():
        return {
            "valid": False,
            "error": f"Packet protocol kernel not found at {kernel_path}",
            "expected_order": [],
            "actual_order": list(KERNEL_ORDER),
            "mismatches": []
        }

    with open(kernel_path, "r") as f:
        protocol_data = yaml.safe_load(f)

    expected_order = protocol_data.get("load_sequence", {}).get("order", [])
    actual_order = list(KERNEL_ORDER)

    mismatches = []
    for i, (expected, actual) in enumerate(zip(expected_order, actual_order)):
        if expected != actual:
            mismatches.append({"position": i, "expected": expected, "actual": actual})

    return {
        "valid": len(mismatches) == 0 and len(expected_order) == len(actual_order),
        "expected_order": expected_order,
        "actual_order": actual_order,
        "mismatches": mismatches
    }
```



### 2. Add to `__all__` in kernel_loader.py

Add `"validate_packet_protocol_rules"` to the Validation section of `__all__`.

### 3. Add to runtime/**init**.py imports and exports

Add `validate_packet_protocol_rules` to both the import block and `__all__` list.

## Validation

After implementation:

1. Run `python -c "from runtime import validate_packet_protocol_rules; print(validate_packet_protocol_rules())"` to verify function works
