<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: output-bundle
version: 2.0.0
status: active
-->

# Audit Output Bundle

## Canonical truth

`audit.json` is the authoritative audit artifact. `remediation-handoff.json`, Markdown projections, and the PR Remediation Contract are deterministic projections of canonical audit truth plus the explicit bundle run-control value.

Structural contracts:

- `schemas/audit-output.schema.json` for canonical audit input;
- `schemas/remediation-handoff.schema.json` for the downstream machine handoff;
- `schemas/bundle-manifest.schema.json` for package integrity.

Correct `audit.json` and rebuild. Never hand-edit a projection into newer truth.

## Required output

```bash
python scripts/build_audit_bundle.py --audit audit.json --change-ledger pr-123-change-ledger.json --output-dir ./audit-output
```

`autoremediate` defaults to zero:

```bash
python scripts/build_audit_bundle.py --audit audit.json --change-ledger pr-123-change-ledger.json --output-dir ./audit-output --autoremediate 0
```

The outer ZIP filename is generated once with non-colliding save tags:

```text
l9-pr-audit__<repo>__<pr-scope>__<utc-build-tag>__<unique-tag>.zip
```

Do not rename it to add versions or dates. The generated name is already save-safe and prevents repeated audit exports from overwriting older files.

The internal file set is exact:

```text
00_READ_FIRST.md
change-ledger.json
audit.json
audit.md
remediation-handoff.json
PR_REMEDIATION_CONTRACT.md
MANIFEST.json
```

Extra bundle files fail verification. The verifier re-derives the handoff and all projections from canonical `audit.json` plus the manifest-bound `autoremediate` value.

## File roles

- `00_READ_FIRST.md`: cold-start identity, run control, coverage/convergence status, file map, and stale-head gate.
- `change-ledger.json`: exact packaged deterministic census set bound to audited PR heads; provenance for machine changed-symbol, claim-seed, falsification-seed, CI/review, and change-discipline enumeration. It is not a competing semantic verdict.
- `audit.json`: canonical machine-readable audit and evidence SSOT, including intent provenance, canonical domain assessments, architecture-policy adapter resolution, boundary ownership, exact changed-file inventory, deterministic-census binding, changed-symbol ledger, claim-validation matrix, falsification ledger, finding provenance/blocking basis, change discipline/control adequacy, and the audit obligation ledger.
- `audit.md`: human projection of coverage, verdicts, findings, ownership, preservation, and Unknowns.
- `remediation-handoff.json`: schema-validated downstream work units, `autoremediate`, mandatory audit/CI/review convergence requirements, `merge_authorized=false`, publication contract metadata, mutation eligibility, finding provenance/blocking basis, governing authority and mismatch semantics, write surfaces, dependency order, preservation, validation, architecture-policy/boundary context, adversarial-assurance summary, and Unknowns.
- `PR_REMEDIATION_CONTRACT.md`: cold-start execution contract whose primary mission is closing audit findings, with mandatory current-CI and all-current-review-thread convergence, SSOT `make pr` publication, and `MERGE=False`.
- `MANIFEST.json`: schema version, builder version/hash, audit ID, `autoremediate`, exact source bindings, canonical audit hash, bound change-ledger-set hash, schema hashes, and packaged-file hashes.

## Publication law

The remediation contract publishes with `make pr` from the canonical SSOT Makefile publication surface, not from the audited target repository. Failure to resolve that SSOT surface yields `PUBLICATION_BLOCKED`; the executor must not substitute a target-repo Makefile, raw `gh pr`, or replacement PR. The contract converges the affected PR to audit-closed, CI-resolved, review-resolved merge-ready state and then stops. Merge is explicitly unauthorized.

## Freshness

The bundle is valid only for bound PR source heads. The remediation executor must independently observe each head before editing. Moved or unprovable heads are non-mutation states.

CI/test/runtime evidence may use a different tested revision, such as a merge commit. Preserve that identity rather than rewriting it as source head.

## Packaging law

Do not include source dumps, full CI logs, cloned repository files, secret values, or unrelated artifacts. The bundle carries exact locators and minimal proof, not a second repository.

## v2.0 canonical closure state

`audit.json` additionally owns `deterministic_closure_ledger` and `post_judgment_closure`. These are canonical audit state, not report decoration. `audit_passes[*].observed_closure_ids` proves recursive re-observation. The packaged `change-ledger.json` remains the immutable source for machine closure seeds.
