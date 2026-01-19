# TODO: Update Extractors with Packet Validation

**Created:** 2026-01-14
**Source:** Codex patches review (Patches 4-8)
**Priority:** Medium
**Status:** Deferred

---

## Summary

Apply Template Method pattern to extractors with PacketValidator integration. Currently extractors don't return packets, so validation would be no-op. Apply when extractors need to create packets for memory ingestion.

---

## Patches to Apply

| Patch | File | Change |
|-------|------|--------|
| 4 | `memory/extractor/base_extractor.py` | Add Template Method + PacketValidator |
| 5 | `memory/extractor/agent_config_extractor.py` | Rename `extract` → `_do_extraction` |
| 6 | `memory/extractor/code_extractor.py` | Rename `extract` → `_do_extraction` |
| 7 | `memory/extractor/memory_extractor.py` | Rename `extract` → `_do_extraction` |
| 8 | `memory/extractor/module_schema_extractor.py` | Rename `extract` → `_do_extraction` |

**Source file:** `current_work/Patches-Memory Substrate Audit & Cross-Substrate Alignment.md`

---

## Changes Required

### 1. Update `base_extractor.py`

```python
# Add imports
from memory.substrate_models import PacketEnvelopeIn
from memory.validators.packet_validator import PacketValidator, PacketValidationError

# Add to __init__
self._validator = PacketValidator()

# Rename abstract method
@abstractmethod
def _do_extraction(self, input_path: Path, output_root: Path) -> Dict[str, Any]:
    pass

# New public extract() with validation wrapper
def extract(self, input_path: Path, output_root: Path) -> Dict[str, Any]:
    result = self._do_extraction(input_path, output_root)
    raw_packets = result.get("packets", [])
    validated = []
    dropped = 0
    
    for packet in raw_packets:
        try:
            self._validator.validate(packet)
            validated.append(packet)
        except PacketValidationError as exc:
            self.logger.warning(f"Extracted packet invalid, dropping: {exc}")
            dropped += 1
    
    if raw_packets:
        result["packets"] = validated
        result["packets_dropped"] = dropped
        result["packets_validated"] = len(validated)
    
    return result
```

### 2. Update All Subclasses

Rename `def extract(...)` → `def _do_extraction(...)` in:
- `agent_config_extractor.py`
- `code_extractor.py`
- `memory_extractor.py`
- `module_schema_extractor.py`

### 3. (Optional) Add Packet Returns

Update at least one extractor to return packets:

```python
def _do_extraction(self, input_path: Path, output_root: Path) -> Dict:
    # ... existing logic ...
    
    packets = [
        PacketEnvelopeIn(
            packet_type="extracted_config",
            payload={"content": data, "source": str(input_path)},
        )
        for data in extracted_items
    ]
    
    return {
        "success": True,
        "files_extracted": count,
        "packets": packets,  # NEW
    }
```

---

## Why This Matters

- **Security:** Validates packets from untrusted sources before memory ingestion
- **Consistency:** All extracted data goes through same validation pipeline
- **Future-proof:** Infrastructure ready when extractors need to create packets

---

## When to Apply

Apply when:
- [ ] An extractor needs to ingest packets to memory
- [ ] Processing untrusted input files
- [ ] Building extraction → memory pipeline

---

## Related

- `memory/validators/packet_validator.py` — PacketValidator class
- `current_work/Patches-Memory Substrate Audit & Cross-Substrate Alignment.md` — Full patches
- GMP-78: Memory Substrate Audit (patches 1-3 applied)
