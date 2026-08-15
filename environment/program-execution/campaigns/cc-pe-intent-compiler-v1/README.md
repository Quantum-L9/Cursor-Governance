# Campaign: cc-pe-intent-compiler-v1

Registration of the **Program Execution Intent Compiler v1** contract
(`CC-PE-INTENT-COMPILER-V1`) in the governance SSOT, per the campaign-source
convention.

The operator intent (`CONTRACT_SOURCE.md`) is a **Claude Code Execution
Contract** — a build specification for the intent-compiler pipeline that turns
minimal goal-level user input into a validator-clean Program Execution Blueprint
v2, without weakening existing authority, verification, or runtime boundaries. It
is the executable companion to **ADR-0007 … ADR-0016** (added in the separate
docs-only PR).

| Artifact | Purpose |
|---|---|
| `CONTRACT_SOURCE.md` | Immutable operator-intent seed (the `CC-PE-INTENT-COMPILER-V1` contract). |
| `source-integrity-receipt.json` | sha256 digest binding of `CONTRACT_SOURCE.md` (`source-integrity-receipt.v1`). |
| `CAMPAIGN_SOURCE.yaml` | `l9.program-execution.campaign-source.v2` registration seed. |
| `handoff/handoff.json` | Schema-valid `program-execution-controller.handoff-receipt.v2` (admission state). |
| `handoff/CAMPAIGN_HANDOFF.md` | Human-readable admission handoff + owner terminal-verdict note. |
| `deliverables/l9-devpack-compiler/` | Implementation design for the out-of-scope `l9-devpack-compiler` target. |

## What makes this different from a Blueprint overlay

Unlike the `l9-devpack-program-execution-hardening` campaign — whose source *was*
a Program Execution Blueprint v2 overlay that could be instantiated and validated
in place — this source is **prose**: a contract describing the compiler to build.
It compiles into a Blueprint only by running the very `intent → resolution →
synthesis` pipeline it specifies. No Blueprint pair is materialized at admission
time, so there is no instantiated-mode validation receipt here.

## Outcome (recommended verdict: INCONCLUSIVE)

- **Registered.** The contract is preserved immutably with an integrity receipt
  and a campaign-source seed; the ten governing ADRs are captured in the
  companion docs-only PR.
- **Blocked — target binding.** The contract's sole target is
  `l9-devpack-compiler`, which is **out of scope / unreachable** in this session
  (`UNK-001`). The intent compiler cannot be implemented or validated in place,
  so the contract's Quality Gates A–F are unevaluated.
- **Implementation delivered as a manual-apply package** under
  `deliverables/l9-devpack-compiler/` — a repo-aligned build plan for the intent,
  resolution, policy-profile, synthesizer, validator-adapter, CLI, and test
  matrix, honoring the contract's prohibited actions and stop conditions.

## Note on scope of this registration

Per the established campaign convention, mutable controller runtime state is
**not** committed here; it lives under
`$HOME/.l9/programs/cc-pe-intent-compiler-v1`. Only the immutable source, its
integrity receipt, the admission handoff, and the out-of-scope target deliverable
are registered.

_No commit/push/PR/merge/release/deploy against `l9-devpack-compiler` is
authorized by this contract. Terminal verdict is reserved to the program owner._

## Honesty

This leftover campaign is archival / INCONCLUSIVE. Receipt producer and
path fields are not rewritten here. It is not on the compile allowlist.
Do not treat handoff JSON as an executed Program Lock.
