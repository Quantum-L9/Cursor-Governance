---
name: l9-repo-birth
description: route an explicit repository-birth handoff for a verified local PE/PEC source commit to the factory-owned packager in Quantum-L9/l9-repo-template. Use when an explicit repository-birth request or a validated Idea Execute REQUEST_BIRTH_HANDOFF graph stage requires factory packaging; never invoke after PE by default.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: lifecycle_boundary
  role: factory_handoff_control
  tags: [l9, birth, factory, program-execution, explicit]
  status: active
  version: 2.0.0
---
# L9 Repository Birth Handoff (control surface)

## Purpose

Route an explicit request to package an **already verified, clean PE/PEC
commit** to the factory that owns repository birth,
`Quantum-L9/l9-repo-template`. This skill is explicit-only and holds no birth
implementation or schema. A successful PEC receipt is not an activation trigger.

## Ownership

| Concern | Owner |
|---|---|
| Packaging (`birth-payload.json`, `birth-contract.json`, `product-birth-binding.json`) | `l9-repo-template` — `scripts/birth-runner/package_birth_handoff.py` |
| `l9.repo-birth-contract/v1` schema | `l9-repo-template` — `scripts/birth-runner/schemas/birth-contract.schema.json` |
| Admission of the bundle | `l9-repo-template` — `scripts/birth-runner/l9_birth_adapter.py` |
| Remote repository birth | `l9-repo-template` — `make birth` (`scripts/birth-runner/birth_frontdoor.py`) |
| When a handoff is legal | this skill and `l9-idea-execute` (`birth_handoff` stage) |

The factory documents the packager in `docs/ops/REPO_BIRTH.md` ("Packaging the
bundle"). Read the factory's current contract before invoking it; do not restate
or re-implement it here.

## Authority boundary

- Run packaging only from a clean checkout of the factory whose `origin` is
  `Quantum-L9/l9-repo-template`. The packager takes the running checkout as the
  factory; there is no separate factory argument.
- The ProductManifest and its semantic ref are explicit inputs owned upstream.
  Never derive a manifest ref, ProductKind, or archetype from a product id,
  repository name, topology, or path.
- Do not mutate product source, create a repository, calculate a factory state,
  or hand-author a birth payload or birth contract.
- **Packaging is not birth.** A passing package, with either
  `--operation local_validation` or `--operation remote_birth`, uploads nothing
  and creates nothing. Remote birth is a separately authorized request run
  through the factory's public front door, `make birth`, and requires its own
  explicit user authorization; authority to package never implies it.

## Invocation

From the factory checkout:

```bash
python3 scripts/birth-runner/package_birth_handoff.py \
  --source /path/to/clean/pec-source \
  --evidence PE_BIRTH_EVIDENCE.json \
  --manifest product-manifest.json \
  --manifest-ref l9.product-manifest/<product>@<version> \
  --out-dir /path/outside/source-and-factory \
  --operation local_validation
```

The evidence must bind Idea Execute lineage, GAR, Plan, campaign-source v2, PE
receipt, exact commit/tree, and acceptance evidence. The packager exits 0 with a
PASS document only when the factory adapter admits the bundle; any refusal is
the factory's verdict and is reported as-is.

## Validation

The implementation and its tests live in the factory:

```bash
python3 scripts/birth-runner/package_birth_handoff.py --help
python3 -m pytest tests/unit/test_birth_handoff_packager.py
```
