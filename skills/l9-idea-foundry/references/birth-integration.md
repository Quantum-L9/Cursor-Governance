<!-- L9_META
l9_schema: 1
parent: l9-idea-foundry
layer: reference
role: birth_integration
tags: [foundry, repo-template, birth]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-09-02
/L9_META -->

# l9-repo-template birth integration

`Quantum-L9/l9-repo-template` is the sole birth owner. Always inspect its current `docs/ops/REPO_BIRTH.md`, `scripts/birth-runner/README.md`, `.l9/architecture.yaml`, and payload-ownership contract before a real run.

## Placement in the Foundry pipeline

Birth happens **after** authority resolution, optional Harvest, architecture judgment, validated `l9-plan-simple` planning, code realization, exact-state validation, and `FOUNDRY_INDEX.json` generation.

Do not use repository birth as a substitute for code implementation. Do not birth a template demo product and call the idea transformed.

## Template-fit gate

The current template declares itself a non-Constellation Python template. Use it for real Python packages, Python services, or Python-rooted product monorepos. Do not invent a meaningless Python package merely to satisfy authoritative-payload shape.

For a Constellation node or Constellation dependency, follow the sibling template declared by the live `.l9/architecture.yaml`. For a genuinely non-Python product, stop with `TEMPLATE_MISMATCH` unless a legitimate alternative factory is selected.

## Current expected pattern

Before freezing, generate and validate the Foundry downstream index:

```bash
python3 scripts/emit_foundry_index.py /path/to/staging \
  --inventory-digest sha256:<64hex> \
  --plan-ref <validated-plan-ref> \
  --plan-digest sha256:<64hex>

python3 scripts/validate_foundry_payload.py /path/to/staging
```

Commit the exact staging tree, then emit the external freeze receipt:

```bash
python3 scripts/emit_freeze_receipt.py /path/to/staging \
  --inventory-digest sha256:<64hex> \
  --plan-ref <validated-plan-ref> \
  --plan-digest sha256:<64hex> \
  --out /tmp/<repo>.foundry-freeze.json

python3 scripts/validate_foundry_payload.py /path/to/staging \
  --birth-ready \
  --freeze-receipt /tmp/<repo>.foundry-freeze.json
```

Only then invoke the live template contract, conceptually:

```bash
make birth-payload \
  SOURCE=/path/to/clean/foundry-payload \
  OUT=/tmp/<repo>.payload.json

make new-repo \
  REPO=<repo> \
  PKG=<python_package> \
  DESC="<description>" \
  PAYLOAD=/path/to/clean/foundry-payload \
  PAYLOAD_CONTRACT=/tmp/<repo>.payload.json \
  NO_REMOTE=1

# Only after local birth is green and remote birth is requested/authorized:
make new-repo \
  REPO=<repo> \
  PKG=<python_package> \
  DESC="<description>" \
  PAYLOAD=/path/to/clean/foundry-payload \
  PAYLOAD_CONTRACT=/tmp/<repo>.payload.json
```

Treat these commands as examples of the current contract, not eternal syntax. Re-read the live template.

## Why authoritative payload

Foundry creates the product, not a few extra files. Authoritative payload semantics let absence be meaningful and prevent template demo product code from leaking into the newborn.

Re-read the live `payload-ownership` contract for the current repository-shape fields and chassis/product split.

## Downstream provenance rule

`docs/idea-origin/FOUNDRY_INDEX.json` must be included in the frozen product payload. It is the newborn's origin-context entrypoint, not a replacement for current repository truth.

The external freeze receipt binds the committed index by digest. Any change to the payload or index invalidates the freeze receipt and requires a new exact-state freeze before birth.

After freeze, treat the staging repository as immutable evidence. Record local/remote birth observations in the external operator/birth receipt. Do not edit `FOUNDRY_RECEIPT.yaml` merely to stamp a later birth state unless you intentionally invalidate, revalidate, recommit, and re-freeze the payload.

## Chassis rule

Do not generate copies of birth orchestration, org profile materialization, template provenance, or canonical CI distribution in the product payload. Those belong downstream.

## Remote result

Repository existence is not sufficient evidence. Use the birth engine's receipt and remote attestation. Preserve `QUARANTINED` or `PROVISIONAL` exactly when that is what the template observes.
