---
name: Repository Contract Loader Integration
overview: Add Repository Contract Loader as a new validation step in the existing adr-compliance job, leveraging current CI infrastructure without creating new engines.
todos:
  - id: create-dirs
    content: Create config/contracts/ directory
    status: completed
  - id: copy-loader
    content: Copy _repository_contract_loader.py to tests/ci/
    status: completed
  - id: copy-scan-utils
    content: Copy _scan_utils.py to tests/ci/
    status: completed
  - id: copy-tests
    content: Copy test_repository_contract_loader.py and test_repository_contract_calls.py to tests/ci/
    status: completed
  - id: copy-config
    content: Copy repository_contract_pairs.yaml and contract_baseline_counts.json to config/contracts/
    status: completed
  - id: update-ci-yml
    content: Add repository contract validation step to adr-compliance job in ci.yml
    status: completed
  - id: local-test
    content: Run contract tests locally to verify integration
    status: completed
isProject: false
---

# Repository Contract Loader Integration

## Objective

Add the Repository Contract Loader as a new validation check in the **existing `adr-compliance` job** in GitHub Actions. No new jobs, no new engines - leverage what exists.

## What We're Adding

The Repository Contract Loader provides **AST-based method/param validation** that enforces:

- `PacketEnvelopeIn.packet_type` must be from known registry
- `emit_packet.packet_type` must be from known registry
- `save_memory.scope` must be from known enumeration
- `add_governance_block.block_type` must be known
- And more contracts defined in YAML

This catches **invalid string literals** at CI time before they cause runtime errors.

## File Operations

### Step 1: Create Directory

```bash
mkdir -p config/contracts
```

### Step 2: Copy Files


| Source                                                                                   | Target                                                                                             |
| ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `current_work/02-15-2026/_repository_contract_loader/_repository_contract_loader.py`     | [tests/ci/_repository_contract_loader.py](tests/ci/_repository_contract_loader.py)                 |
| `current_work/02-15-2026/_repository_contract_loader/_scan_utils.py`                     | [tests/ci/_scan_utils.py](tests/ci/_scan_utils.py)                                                 |
| `current_work/02-15-2026/_repository_contract_loader/test_repository_contract_loader.py` | [tests/ci/test_repository_contract_loader.py](tests/ci/test_repository_contract_loader.py)         |
| `current_work/02-15-2026/_repository_contract_loader/test_repository_contract_calls.py`  | [tests/ci/test_repository_contract_calls.py](tests/ci/test_repository_contract_calls.py)           |
| `current_work/02-15-2026/_repository_contract_loader/repository_contract_pairs.yaml`     | [config/contracts/repository_contract_pairs.yaml](config/contracts/repository_contract_pairs.yaml) |
| `current_work/02-15-2026/_repository_contract_loader/contract_baseline_counts.json`      | [config/contracts/contract_baseline_counts.json](config/contracts/contract_baseline_counts.json)   |


### Step 3: Update ci.yml

Add this step to [.github/workflows/ci.yml](.github/workflows/ci.yml) in the `adr-compliance` job (after line ~520):

```yaml
      - name: Repository contract validation
        run: |
          echo "📋 Validating repository method/param contracts..."
          python -m pytest tests/ci/test_repository_contract_calls.py -v --tb=short
```

### Step 4: Local Validation

```bash
python -m pytest tests/ci/test_repository_contract_loader.py tests/ci/test_repository_contract_calls.py -v
```

## Summary

- **6 files copied** to proper locations
- **1 step added** to existing `adr-compliance` job
- **No new jobs** created
- **No new engines** created
- Leverages existing CI infrastructure
