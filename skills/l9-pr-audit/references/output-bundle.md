<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: output-bundle
version: 1.3.0
status: active
-->

# Audit Output Bundle

## Canonical truth

`audit.json` is the only authoritative run artifact. Markdown, remediation handoff, Fable prompt, read-first file, and manifest are deterministic projections.

Structural contracts:

- `schemas/audit-output.schema.json` for canonical input;
- `schemas/remediation-handoff.schema.json` for the downstream machine handoff;
- `schemas/bundle-manifest.schema.json` for package integrity.

Correct `audit.json` and rebuild. Never hand-edit a projection into newer truth.

## Required output

```bash
python scripts/build_audit_bundle.py --audit audit.json --output-dir ./audit-output
```

Output file set is exact:

```text
l9-pr-audit-output.zip
  00_READ_FIRST.md
  audit.json
  audit.md
  remediation-handoff.json
  FABLE_REMEDIATION.md
  MANIFEST.json
```

Extra bundle files fail verification. The verifier also re-derives the handoff and all rendered projections from canonical `audit.json`; re-hashing a hand-edited projection does not make it valid.

## File roles

- `00_READ_FIRST.md`: cold-start identity, coverage/convergence status, file map, stale-head gate.
- `audit.json`: canonical machine-readable audit and evidence SSOT.
- `audit.md`: human projection of coverage, verdicts, findings, ownership, preservation, and Unknowns.
- `remediation-handoff.json`: schema-validated downstream work units with mutation eligibility, strict write surfaces, dependency order, preservation, validation, and Unknowns.
- `FABLE_REMEDIATION.md`: Claude Code/Fable execution contract generated from the handoff. It is instructions, never authorization.
- `MANIFEST.json`: schema version, builder version and builder-byte hash, audit ID, exact source bindings, canonical audit hash, all schema hashes, and packaged-file hashes.

## Freshness

The bundle is valid only for bound PR source heads. Fable must independently observe each head before editing. Moved or unprovable heads are non-mutation states.

CI/test/runtime evidence may use a different tested revision, such as a merge commit. Preserve that identity rather than rewriting it as source head.

## Packaging law

Do not include source dumps, full CI logs, cloned repository files, secret values, or unrelated artifacts. The bundle carries exact locators and minimal proof, not a second repository.
