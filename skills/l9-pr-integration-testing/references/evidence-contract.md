<!-- L9_META
schema: 1
parent: l9-pr-integration-testing
layer: reference
role: versioned-integration-evidence
version: 0.1.0
status: active
-->

# Evidence and integration verdict contract

Four JSON documents and one hash seal comprise one evaluation. All require fixed schemas and exact source revisions. `scripts/validate_evidence.py` validates the evidence graph and the tamper-evident hash index. The hash index is an integrity receipt only, **not an independent signature**.

| Document | Contract and ownership |
|---|---|
| `integration_manifest.json` | `l9.integration.manifest/v1`: repository/base and PR source SHAs, order, candidate revision per phase, environment/image, dependencies, overlap candidates, cleanup status. |
| `integration_evidence.json` | `l9.integration.evidence/v1`: stable evidence IDs, exact argv, status, timing, logs (with SHA256), failure identities, source signals, negative probes. |
| `integration_findings.json` | `l9.integration.findings/v1`: finding IDs, severity/classification, evidence IDs, scope, cause confidence, corrective obligation. |
| `integration_verdict.json` | `l9.integration.verdict/v1`: readiness state, blockers, scope, execution coverage, remaining uncertainty. |
| `evidence-index.json` | `l9.integration.index/v1`: SHA256 for each JSON and retained log; no self-hash. |

## Execution semantics

- `PASS` is returned by an executed command on a known synthetic revision. A path, symbol, or green CI badge cannot turn a `NOT_EXECUTED` result into a passing result.
- `KILLED` means the mutation made a procedure fail that passed on the unmutated combined candidate, or added failure identities it did not have, **only** for that mutation; each probe records its `basis`. A failure the candidate already had is not a kill: on a red candidate without a `failure_parser` the probe is `INCONCLUSIVE`. `SURVIVED` proves targeted tests failed to reject the altered candidate, but this is a correctness finding only if the mutation's expected-wrong behavior is backed by target authority. `INCONCLUSIVE` is never a pass.
- `REGRESSION` requires a demonstrated clean baseline or a verified new failure identity against an existing red baseline. With both baseline and candidate red but unparseable failure identities, attribution remains `UNKNOWN`. Failure identity parsers are test-runner specific.
- `MERGE_CONFLICT` is actual Git conflict; an overlap cue without conflict or runtime failure is a review candidate, not a confirmed bug.
- `INTEGRATION_ONLY` requires baseline green, each component PR green, combined failing; a semantic conflict that is not exercised by tests may still escape, so independent review and probes remain mandatory.
- `ENVIRONMENT` means Docker, pinned image, or required isolated service missing; do not attribute this to code. `AUTHORITY` means the governing source, permissions, command provenance or integration order cannot be established.

## Decision rules

`INTEGRATION_READY` requires Docker code execution on the exact reconstructed revision, successful combined tests, baseline disposition, positive and meaningful negative behavioral witnesses, complete independent source review, and source/contract authority closure. It means only that the **stated integration scope** was demonstrated, never permission to merge or production readiness.

`NOT_INTEGRATION_READY` requires confirmed material source, merge, regression, or false-green defects. `INCOMPLETE_EVIDENCE` means a material correctness/coverage conclusion remains unproved despite usable execution. `BLOCKED` means a prerequisite, environment or authority prevents safely executing a required portion.

After edits to any source, evidence or verdict, regenerate the seal and rerun `scripts/validate_evidence.py`. Never relabel `BLOCKED` as `PASS` after changing the manifest without rerunning the actual operation. The output may contain proprietary source/tests or logs; inspect for sensitive records before distribution.

## Canonical compiler enforcement-gates

The source pack must preserve executed fixture witness outputs and demonstrate a positive and negative case for material actions. A structural validator or archive checksum cannot certify Docker isolation. This source pack preserves actual Git and test fixture results separately; Docker execution remains explicitly unverified until a real Docker-host witness runs. The canonical compiler provenance is pinned in the source receipt; release tier must reflect this gap.

## Two-phase source review

The first Docker run produces `INCOMPLETE_EVIDENCE` until a reviewer inspects the exact integrated patch and its coupled source. `scripts/apply_review.py` accepts a `l9.integration.source-review/v1` JSON receipt with `integrated_sha`, `reviewer`, `decision`, every changed `paths[]` with source coordinate/disposition/rationale/evidence IDs, `contract_obligations[]` with authority and evidence, `test_discrimination[]` for each executed test procedure, and material `findings[]`. It refuses a different SHA or missing path. Findings remain in the ledger with a resolution evidence ID when closed. A reviewed database/Odoo target does not magically establish unsupported service tests.
