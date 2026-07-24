# Manifest

## Package identity

* Repository: `Quantum-L9/l9-assurance`
* Package role: root architecture contract plus repository-local AI Coding Control Plane
* Base archive: `l9-assurance-root-contract-with-roadmap.zip`
* Top-level directory: `l9-assurance/`

## Governing source disposition

| Uploaded source | Disposition | Final artifact | Reason |
|---|---|---|---|
| `Agent & Readme.md` | Split, polished, and repository-aligned | `AGENTS.md`; `docs/AI_CODING_CONTROL_PLANE.md`; updates to `README.md` | Preserves the canonical machine-facing contract and human guide without replacing the product README. |
| `Audit (before plan).md` | Included and renamed | `ai-control-plane/AUDIT.md` | Canonical read-only audit stage. |
| `Plan (after audit).md` | Included and renamed | `ai-control-plane/PLAN.md` | Canonical planning stage. |
| `Build (after plan).md` | Included and renamed | `ai-control-plane/BUILD.md` | Canonical new-deliverable build stage. |
| `Change (after build).md` | Included and renamed | `ai-control-plane/CHANGE.md` | Canonical established-target mutation stage. |
| `Done.md` | Included and renamed | `ai-control-plane/DEFINITION_OF_DONE.md` | Canonical terminal completion contract. |
| `Release (after Change).md` | Included and renamed | `ai-control-plane/RELEASE.md` | Canonical lifecycle stage. |
| `Validate & Repair.md` | Excluded | None | Conflicts with the original AGENTS contract by combining mutation and validation. VALIDATION must remain non-mutating; repair belongs to CHANGE. |

A dedicated `ai-control-plane/VALIDATION.md` is derived from the non-mutating VALIDATION rules in the governing `Agent & Readme.md` source. It is not a renamed copy of the excluded hybrid upload.

## Final file responsibilities

| Path | Responsibility |
|---|---|
| `README.md` | Human-facing L9 Assurance identity, boundaries, status, and navigation. |
| `AGENTS.md` | Repository-wide AI agent authority, routing, invariants, and L9 Assurance architectural lock. |
| `ARCHITECTURE.md` | Trust-plane architecture and constellation boundaries. |
| `SPECIFICATION.md` | Normative protocol and integration contract. |
| `ROADMAP.md` | Phased evolution from the current repository to the target trust-plane architecture. |
| `SECURITY.md` | Threat model, trust-boundary controls, and security review triggers. |
| `CONTRIBUTING.md` | Contribution ownership and change requirements. |
| `CHANGELOG.md` | Architectural and packaging change record. |
| `ai-control-plane/` | Canonical stage kernels. |
| `docs/AI_CODING_CONTROL_PLANE.md` | Human operating guide for the stage model. |
| `package.json` | Node workspace metadata and package file inclusion. |
| `pyproject.toml` | Python metadata and documentation build inclusion. |
| `MANIFEST.md` | Source disposition and final package map. |
| `MANIFEST.sha256` | SHA-256 inventory of every delivered file except itself. |

## Uploaded source checksums

| Source | SHA-256 |
|---|---|
| `Agent & Readme.md` | `60accd9923f8995b70e31d61073156e0d66b3351a4ba3159c2ce65274f7d17cd` |
| `Audit (before plan).md` | `e82a95b736e3456b0e6f4e49e43e5e2acaf012c382db37d7c7a24d552fcc7aa1` |
| `Build (after plan).md` | `283a7b82db96ff3fdc06aa2a58341a375ce7a04186f2f6090c07f65ce696a541` |
| `Change (after build).md` | `057e4f9300a280906ec11304542b2d9fa5662690792d1a7ec02aeb7c99d034d6` |
| `Done.md` | `c04807590427032203c6735a474d79961ad196114b38061cfcd5507e3f36d195` |
| `Plan (after audit).md` | `b5a85bd93db6c036c6fc4cbba02073efa56c2a96ee113200c6de2f5c0cecc914` |
| `Release (after Change).md` | `6d611bcc11176c4010b2da57a9c9cf3c30ac2f78c14481218e1c30b757143022` |
| `Validate & Repair.md` | `1f4fb6d981c31f8f778b148be00412124f86f0f43096b666b571925e1fbcd611` |

## Packaging rules

* Raw upload filenames are not retained in the final tree.
* The excluded hybrid validation-and-repair source is not packaged.
* No implementation packages, schemas, workflows, generated bindings, or test results are fabricated.
* The archive contains one top-level `l9-assurance/` directory.
