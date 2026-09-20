# L9 Update Agent Docs

**Path:** `skills/l9-update-agent-docs` | **Kind:** skill

## Purpose

compile repository changes into typed documentation and operational-contract obligations, assess Makefile/pyproject surfaces, and emit repo-docs receipts

## Responsibilities

- `l9-update-agent-docs` owns documentation topology, impact qualification, target resolution, obligation compilation, deterministic materiality assessment for explicitly registered operational surfaces, freshness semantics, admission of semantic evidence…
- `DocumentationObligation` remains the only durable work unit. `assessment` is evidence attached to an obligation, never a second findings ledger or second obligation system.
- `l9-update-agent-docs` must not absorb Make/Python semantic ownership merely because it detects a material defect.
- `ops/config/root-file-protection.json` remains the canonical mutation-protection contract.
- `l9-intelligence-harvest` owns semantic discovery and qualification. The compiler consumes canonical `harvest.json`; it never copies Harvest reasoning or mutates the donor through Harvest.
- `l9-update-agent-docs` owns the root `filetree.md` inventory (`scripts/doc_filetree.py`) and README compilation (`scripts/generate_module_readmes.py` over `readme_model.py`, `readme_evidence.py`, `readme_renderers.py`, `readme_quality.py`). `filetree.md` is…

## Key components

- [`contracts/`](contracts/)
- [`references/`](references/)
- [`scripts/`](scripts/)

## Authority

`SKILL.md` in this directory is the authoritative operating contract. This README is a navigation projection of it and never outranks it.

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=skill -->
