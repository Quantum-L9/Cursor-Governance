# Claude Code Mobile environment — superseded planning snapshots

The plan of record for this workstream is **[`docs/plans/claude-code/`](../../docs/plans/claude-code/)**.
Read that first. Nothing here is authoritative.

## What is in this directory

| File | Status |
|---|---|
| `claude-code-mobile-environment.plan.json` | Superseded snapshot (2026-08-20, PR #232) |
| `claude-code-mobile-environment.plan.md` | Superseded snapshot — the PE projection of the above |
| `claude-code-mobile-remediation.contract.v3.1.yaml` | **Live.** Execution contract, not a plan. Keep. |

## Why this note exists

Three planning artifacts for one initiative landed within 72 hours — #232 and
#233 into `WIP/`, then #239 into `docs/plans/claude-code/` — with nothing saying
which was authoritative. A 72h audit flagged the ambiguity (finding F-07). The
convention #239 established is the answer: `l9-plan` PLAN_DOCUMENTs live under
`docs/plans/`, version-controlled, `.plan.json` authoritative and `.plan.md`
regenerated from it.

The two `claude-code-mobile-environment.plan.*` files are kept as the record of
what was understood on 2026-08-20. They are not maintained, and divergence from
`docs/plans/claude-code/` should be resolved in favour of the latter. Do not
extend them; add todos to the plan of record instead.

`claude-code-mobile-remediation.contract.v3.1.yaml` is a different kind of
artifact — a policy-as-code execution contract consumed at runtime, not a
planning document — so it is unaffected by the consolidation and stays here.

`make wip-hygiene` / `make wip-inventory` own this corpus's lifecycle; nothing
here is deleted by hand.
