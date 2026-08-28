<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: reference
role: build-quality-kernel
version: 2.1.0
status: active
-->

# Build Quality Kernel

Build the requested pack fully, validate it, package it when requested, and return the actual artifact.

## Hard rules

- Inspect all supplied inputs first.
- Build complete production-usable files in one execution path.
- Use source and repository evidence when available.
- Label missing or unverifiable values `Unknown`.
- Do not invent credentials, tools, connectors, paths, tests, licenses, approvals, or external facts.
- Do not defer required work, create decorative files, or duplicate responsibilities.
- A large pack with more than ten files requires README, RUNBOOK, MANIFEST, and VALIDATION.

## Stop conditions

Stop before packaging when a required file is shallow, a reference is missing, a deterministic script cannot run, validation evidence is absent, or the ZIP cannot be created and inspected.
