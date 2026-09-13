---
name: l9-repo-birth
description: package a verified local PE/PEC source commit into the current l9-repo-template factory payload and a digest-bound birth contract. Use when an explicit repository-birth request or a validated Idea Execute REQUEST_BIRTH_HANDOFF graph stage requires factory packaging; never invoke after PE by default.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: lifecycle_boundary
  role: factory_handoff
  tags: [l9, birth, factory, program-execution, explicit]
  status: active
  version: 1.0.0
---
# L9 Repository Birth Handoff

## Purpose

Package an **already verified, clean PE/PEC commit** for the existing
`Quantum-L9/l9-repo-template` factory. This skill is explicit-only. A successful
PEC receipt is not an activation trigger.

## Authority boundary

- Validate source/evidence bindings and invoke the factory's own
  `compile_birth_payload.py`.
- Emit `l9.repo-birth-contract/v1`, which references the factory-emitted
  `l9.birth-payload/v1` manifest.
- Do not mutate product source, create a repository, calculate a factory state,
  or hand-author a birth payload.
- For a local factory proof use `--operation local_validation`; remote birth
  requires a separately authorized `remote_birth` request and must be run by
  the factory's public front door.

## Invocation

```bash
python3 scripts/package_birth_handoff.py \
  --source /path/to/clean/pec-source \
  --evidence PE_BIRTH_EVIDENCE.json \
  --factory /path/to/l9-repo-template \
  --out-dir /tmp/birth-handoff \
  --source-repository Quantum-L9/future-product \
  --operation local_validation
```

The evidence must bind Idea Execute lineage, GAR, Plan, campaign-source v2,
PE receipt, exact commit/tree, and acceptance evidence. The script rejects drift
before the factory compiler runs.

## Validation

```bash
python3 scripts/package_birth_handoff.py --help
python3 scripts/self_test.py
```
