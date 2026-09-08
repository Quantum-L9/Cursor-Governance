<!-- L9_META
l9_schema: 1
parent: l9-idea-foundry
layer: reference
role: birth_integration
tags: [foundry, repo-template, birth]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-09-07
/L9_META -->

# l9-repo-template birth integration

`Quantum-L9/l9-repo-template` is the sole birth owner. Always inspect its current `docs/ops/REPO_BIRTH.md`, `scripts/birth-runner/README.md`, `.l9/architecture.yaml`, and payload-ownership contract before a real run.

Live factory: https://github.com/Quantum-L9/l9-repo-template

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

## Payload shape and compiled contract

`repository_shape` is `pyproject.toml`, `.l9/architecture.yaml`, `src/`, `tests/`, and `scripts/inventory_check.py`. Presence of that shape means **authoritative**: absence of template demo surfaces is meaningful. A fragment without that shape is **additive**.

An authoritative payload **must** have a compiled `l9.birth-payload/v1`. Write the contract **outside** the source tree (or pass a dispatch `payload_contract_path` that is outside `payload_subpath`). Putting the JSON inside the compiled source makes `files[]` circular.

If a pack is only an overlay on an older tree, reformat it to repository shape before birth. Do not invent product modules just to satisfy imports, and do not birth a headerless fragment as authoritative.

A payload that overlays `scripts/inventory_check.py` must already name `src/<pkg>/`. The chassis checker still lists `src/l9_example_pkg/` until rename.

## Desktop vs App dispatch

Desktop `gh` can `POST /orgs/{org}/repos`. Claude Code on the web/mobile cannot — that is why dispatch exists. This Cursor surface is not blocked the same way.

| Path | When | Entry |
|------|------|--------|
| Local / no-remote | Prove the payload before publication | `make new-repo … NO_REMOTE=1` |
| Desktop remote | This machine, after local green | `make new-repo` (same engine) |
| App dispatch | Surface with no create-repo authority | `workflow_dispatch` `.github/workflows/repo-birth-dispatch.yml` on **`main` only** |

Dispatch inputs: `repo_name`, `package_name`, `description`, `visibility`, optional `payload_repo` (same org), `payload_ref` (pin a SHA), `payload_subpath`, `payload_contract_path`. A bare dispatch births the template.

The runner calls `make new-repo`. It does not reimplement stages. The workflow is template-owned and is **not** copied into a newborn (`TEMPLATE_EXCLUDE_PATHS`).

## GitHub App and environment

Authority is the **`repo-birth`** GitHub App (id `4831302`), installed on **all** Quantum-L9 repositories so a newborn can be named before it exists.

Credentials live in the template environment **`repo-birth`**, restricted to `main`:

| Name | Where | Role |
|------|--------|------|
| `BIRTH_APP_ID` | environment **variable** | App id (`4831302`) |
| `BIRTH_APP_PRIVATE_KEY` | environment **secret** | PKCS#1 PEM (`BEGIN RSA PRIVATE KEY` / `END RSA PRIVATE KEY`) |

Operator-local aliases (gitignored `.env.local`, never git):

- `BIRTH_SOURCE_APP_ID` — same id as a repo variable
- `BIRTH_SOURCE_APP_PRIVATE_KEY` — the same PEM

A 40-character hex line is a fingerprint, not the key. A headerless base64 body will fail `actions/create-github-app-token` with `Invalid keyData` / `asn1 encoding routines`. Do not print, export, or paste the PEM. Update the environment secret with `gh secret set BIRTH_APP_PRIVATE_KEY --repo Quantum-L9/l9-repo-template --env repo-birth` from a 0600 file.

Birth ends at **PROVISIONAL**. `BORN` is the first passing PR, not repository existence.

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
