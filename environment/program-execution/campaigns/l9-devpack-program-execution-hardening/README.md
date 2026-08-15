# Campaign: l9-devpack-program-execution-hardening

Registration of the **L9 Devpack Compiler Program Execution v2 Hardening**
program in the governance SSOT, per the campaign source's `intended_drop_path`.

The operator intent (`PROGRAM_SOURCE.md`) is a Program Execution Blueprint v2
overlay that hardens `l9-devpack-compiler` into a provenance-safe compiler /
intermediate representation which emits Blueprint v2 authority **without**
becoming a competing runtime authority.

| Artifact | Purpose |
|---|---|
| `PROGRAM_SOURCE.md` | Immutable operator-intent seed (the uploaded Program Execution Blueprint v2 overlay). |
| `source-integrity-receipt.json` | sha256 digest binding of `PROGRAM_SOURCE.md` (`source-integrity-receipt.v1`). |
| `CAMPAIGN_SOURCE.yaml` | `l9.program-execution.campaign-source.v2` registration seed. |
| `VALIDATION_EVIDENCE.md` | Reproducible receipts: blueprint + controller instantiated validation both **PASS**. |
| `handoff/handoff.json` | Schema-valid `program-execution-controller.handoff-receipt.v2` (admission state). |
| `handoff/CAMPAIGN_HANDOFF.md` | Human-readable admission handoff + owner terminal-verdict note. |
| `deliverables/l9-devpack-compiler/` | Hand-off for the out-of-scope `l9-devpack-compiler` target (W1–W7 remediation design that could not be pushed to that repo). |

## Outcome (recommended verdict: INCONCLUSIVE)

- **Definition materialized and validated GREEN.** The native Blueprint v2 +
  Controller pair was instantiated from this repo's
  `environment/program-execution/core` and both sides pass **instantiated-mode**
  validation with zero errors (see `VALIDATION_EVIDENCE.md`).
- **Admission locked to W0.** The Blueprint permits inspection only in W0;
  W1–W3 permit reversible local writes **after** their gates pass.
- **Blocked — target binding.** `TASK-001` cannot bind
  `repository_id=l9-devpack-compiler` to an exact base SHA because that
  repository is **out of scope / unreachable** in this session. `UNK-001`
  remains **open** and blocks `TASK-002`–`TASK-007` by design (scoped, not
  global, blocking). No controller runtime lock, ledger, or per-run receipts
  were produced.
- **Reachable engineering delivered as a manual-apply package.** The W1–W7
  remediation design for `l9-devpack-compiler` is delivered under
  `deliverables/l9-devpack-compiler/` for manual application (or attach the repo
  and re-run to execute it in place).

## Note on scope of this registration

Per the established campaign convention (see `l9-ecosystem-fix-plan`), mutable
controller runtime state — the instantiated blueprint/controller pair, any
SQLite ledger, per-run workspaces, and receipts — is intentionally **NOT**
committed here. It lives under the external program root
`$HOME/.l9/programs/l9-devpack-program-execution-hardening`. Only the immutable
source, its integrity receipt, the admission handoff, the reproducible
validation evidence, and the out-of-scope target deliverable are registered in
the SSOT.

_Terminal verdict is reserved to the program owner (AUTH-001); the controller
only recommends._

## Honesty

This leftover campaign is archival / INCONCLUSIVE. Receipt producer and
path mismatches are not rewritten here. It is not on the compile
allowlist. Instantiated-mode claims in `VALIDATION_EVIDENCE.md` are
historical notes, not a live Program Lock.
