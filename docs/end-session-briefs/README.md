# End-session briefs

Briefs written when a campaign or a long governed session closes. Each brief is
evidence for the next session and for governance. It records what shipped, what is
still open, what got in the way, and what should change in the protocols so the
next run needs fewer operator approvals.

They are not authority. A recommendation here becomes binding only after a PR
lands it in the rung that owns it: `CANONICAL_LAW.md`,
`ops/autonomy/surface_profile.yaml`, `AGENTS.md`, `governance/*/MODE.yaml`, or a
skill.

## Layout

One folder per closed campaign, named `YYYY-MM-DD-<campaign-slug>/`, holding:

| File | Audience | Content |
|---|---|---|
| `SESSION_BRIEF.md` | the next session, and L CTO after hand-off | outcome, shipped PRs, live state, open items, operator decisions owed |
| `GOVERNANCE_FRICTION_BRIEF.md` | governance maintainers | friction met, observed evidence, the fix proposed for each |
| `CTO_SWARM_OPERATIONS_BRIEF.md` | the CTO-mode owner | how the swarm ran, the operator's approval cost, protocol amendments |
| other files (optional) | as named | runbooks or artifacts the briefs reference, with secrets and hostnames removed |

`reports/end-session/` keeps the machine-generated handoffs written by
`session_debt.py handoff`. This folder holds the hand-written analysis.

## Index

| Date | Campaign | Repository |
|---|---|---|
| 2026-11-16 | [Odoo ERP Catalog → Profiles → EIE](2026-11-16-odoo-erp-catalog-profiles-eie/) | cryptoxdog/IB-Odoo_19 |
