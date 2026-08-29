# Campaign: bounded-replanning-v1

Registration of the **Program Execution Bounded Replanning Layer** campaign in
the governance SSOT, per the campaign-source convention. This is the
operator-supplied canonical `CAMPAIGN_SOURCE.yaml` (corrected), rendered to valid
YAML and preserved as the immutable source.

The campaign extends the existing Cursor-Governance Program Execution subsystem
with the bounded-replanning architecture accepted in **ADR-0011 … ADR-0016**
(registered in PR #91): evidence-triggered, digest-bound Replan Revisions that
adapt *future* work **inside** the immutable Program Lock, projected through the
existing registry/adapter/conformance topology to **every** registered execution
peer under one canonical semantic revision.

| Artifact | Purpose |
|---|---|
| `CAMPAIGN_SOURCE.yaml` | Immutable operator-intent seed (`l9.program-execution.campaign-source.v2`), corrected canonical version. |
| `source-integrity-receipt.json` | sha256 digest binding of `CAMPAIGN_SOURCE.yaml` (`source-integrity-receipt.v1`). |

## Status

- **complete** — live closeout in `handoff/CLOSEOUT.yaml` and
  `../../CAMPAIGN_STATUS.yaml`. Evidence: PR #149 merged to `main`
  (`63efde4f`). Do not resume this campaign.
- Immutable source `metadata.status` remains `operator_intake` (seed is
  sealed). Agents read the live ledger, not that field.
- Governing decisions **ADR-0011 … ADR-0016** are present and accepted
  (`docs/decisions/`, PR #91).
- **Target is in-scope:** unlike the devpack campaigns, `TARGET-001` is
  `Quantum-L9/Cursor-Governance` itself (`environment/program-execution`), so the
  work is repo-local and reversible when admitted — but admission, evidence
  binding (`EVID-001…005`), and the W0 authority/current-state lock are **not**
  performed here.

## Source integrity

| Field | Value |
|---|---|
| Digest algorithm | sha256 |
| Digest | `9528abeaf8117dd0598036216784593a62e88948800636c2eced9dc6262ae010` |
| Bytes | `50453` |

> Note on canonicalization: the operator-supplied source arrived with paste
> artifacts (smart quotes, `*` bullets, flattened indentation). It was rendered
> to valid, parseable YAML with **no change to field values or semantics**; all
> cross-references (tasks↔gates↔evidence↔decisions↔unknowns↔waves↔authorities)
> resolve. The digest above binds this canonical rendering.

## Note on scope of this registration

Per the established campaign convention, mutable controller runtime state is
**not** committed here; it lives under
`$HOME/.l9/programs/bounded-replanning-v1`. Only the immutable source and its
integrity receipt are registered.

_AUTH-001 declared owner terminal verdict CONVERGED and expanded the
authorization ceiling to commit/push/pull_request. Merge, release, and deploy
remain denied. Engineering admission (Blueprint instantiate, Program Lock, W0)
is still not performed by this registration._

## Honesty

`definition_status` remains `draft`. This overlay does not accept the
program. `CAMPAIGN_SOURCE.yaml` bytes and
`source-integrity-receipt.json` are immutable. Compile through
`scripts/compile_campaign_source.py`; do not treat an ad-hoc
`$HOME/.l9/blueprints` compiler as SSOT. Instantiated Blueprint
validation stays FAIL while evidence is planned.
