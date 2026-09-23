# ADR Catalog Alignment Invariants

This reference **adapts the repository alignment kernel to the ADR compiler's bounded role**. It is not a second ADR-authoring specification and must not duplicate the ADR skill's semantic template.

## Objective and ownership

The compiler proves that a repository delta has a deterministic, evidence-bound decision-record disposition. `l9-update-agent-docs` owns catalog observation, evidence, receipt compatibility, and CI admission. `l9-architecture-decision-records` retains every authoring, revision, supersession, and deletion decision. A confirmed active defect is therefore a `HANDOFF`, never a compiler-authored repair.

## Convergence invariants

| Invariant | Enforcement seam | Evidence of closure |
|---|---|---|
| **Bind before assess** | `compile_adr_catalog()` only accepts declared ADR directories and Git change paths | Catalog records and digest bind the evaluated revision. |
| **No change may disappear** | Active paths come from the delta; a missing current-worktree record becomes `adr.record.presence` | The deleted path remains an external-owner obligation. |
| **No external read** | Every discovered source must resolve under the audited root before bytes are read | Escaping symlinks are `BLOCKED` with no content digest. |
| **Repository convention is preserved** | Both established filename forms, `ADR-NNN[-slug].md` and `NNN[-slug].md`, map to the same numeric identity | The compiler accepts compatible records without historical rewrites. |
| **Contract parsing is exact** | The Date field is a calendar date matching `YYYY-MM-DD` and validated by `date.fromisoformat` | Datetime, timezone, and malformed values receive an evidence-bound finding. |
| **Historical debt is not scope creep** | Only active findings make the catalog `FAIL`; historical findings remain `PARTIAL` evidence | Unrelated changes do not require a history rewrite. |
| **Receipt evolution is explicit** | New output is `l9.repo-docs.receipt.v4`; v3 validation remains dispatched through its preserved schema | Stored v3 receipts and newly emitted v4 receipts both validate. |
| **CI aligns the gate to materiality** | Governance CI fails closed for nonzero `active_finding_count` and retains advisory treatment for unrelated pilot debt | An active ADR violation cannot pass as a generic warning. |

## Required validation

Run the focused ADR and receipt regressions, the full `skills/l9-update-agent-docs/tests` suite, `scripts/self_test.py`, the governance-workflow regression, and the repository gate before release. If any invariant cannot be proven from the evaluated revision, retain an explicit `BLOCKED` or `HANDOFF` disposition rather than inferring a successful repair.

## Non-goals

This component never invokes the ADR skill, executes Markdown, follows external symlinks, performs an LLM assessment, creates an ADR, rewrites history, renumbers a record, or accepts a receipt schema change under an existing schema identity.
