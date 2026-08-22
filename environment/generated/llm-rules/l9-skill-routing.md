---
description: Proactive L9 skill selection — Read the matching skill before non-trivial work; honor Cursor skill-route hints; fail closed if skipped.
---

# L9 skill routing (Cursor)

Rules SSOT: this folder (`rules/` / `.cursor-commands/rules`) as `.mdc`. Claude Code
mounts the projected `.md` tree at `.claude/rules` →
`environment/generated/llm-rules/` (alias `l9-skill-routing.md`). Skills SSOT:
`.cursor-commands/skills` via the `l9-governance` plugin — not a second copy under
`.cursor/skills`.

**Selecting a skill is not optional theater.** For non-trivial work, load the
skill contract before improvising.

## Authority split (SSOT — do not restate conflicting rules elsewhere)

| Layer | Meaning | Mutation authority |
|-------|---------|-------------------|
| `auto_invoke` | Model may select; router may force Read (`source: route`) | Per skill contract |
| `explicit_only` + route `hint_allowed: true` | Router may recommend Read/attach (`source: explicit_hint`) | Still needs user / `/autonomy` / packet / human approve |
| `explicit_only` (no hint) | Never proactive | Manual `/` or explicit user request only |

**A router hint is routing evidence, not mutation authority.** Never treat
`explicit_hint` as push/merge/deploy/UI-run permission.

## Mandatory — first action on non-trivial tasks

1. Scan available L9 skills for the closest match to the user request.
2. **Read that skill's `SKILL.md` immediately** (first tool action) and follow it.
3. Use **one primary** skill. Add at most **two supporting** skills when each supplies
   a capability the primary does not own.
4. Prefer a domain skill over `l9-structured-reasoning`; use structured reasoning as
   support for architecture, planning, debugging, trade-offs, corpus analysis, or
   material uncertainty.
5. Honor `explicit_hint` by **Reading** the named skill; do **not** auto-execute its
   mutating steps without the skill's required authority (packet / approve / explicit user).
6. Skip skill load only for trivial edits / direct factual lookups where no skill
   would improve correctness or evidence.
7. **Planning deliverables:** when producing an ordinary execution plan/spec
   (including Cursor Plan mode), follow `l9-plan-simple` →
   `references/plan-workflow-simple.md` (shared canonical template, Build execute)
   even if the skill was not attached and even if `~/.cursor/l9/skill-route.json`
   is stale/absent. Campaign / program-execution / `make campaign` / `/l9-plan`
   still follow `l9-plan` → `references/plan-workflow-pe-autonomy.md`.

## Fail-closed

- Non-trivial task + no skill loaded → load a skill before irreversible edits.
- Domain skill vs general reasoning → domain skill wins.
- Irreversible action without evidence → block or bounded probe.
- Explicit-only without `hint_allowed` → never auto-select via Skill tool / ambient discovery.

## Live route hint (hook)

`beforeSubmitPrompt` runs `ops/hooks/before_submit_skill_router.py`, which writes:

`~/.cursor/l9/skill-route.json`

When that file exists and `recommended_at` is **within the last 2 minutes**, treat
`primary` / `supporting` as the high-confidence route and Read those skills first.
If `source` is `explicit_hint`, Read but do not mutate from the hint alone.
If the file is stale or absent, still select from available skills yourself.

## Common triggers → primary skill

| User intent | Read first |
|---|---|
| Plan / unclear scope / decompose / Cursor Plan mode | `l9-plan-simple` |
| Campaign / PE / `make campaign` / `/l9-plan` | `l9-plan` |
| Run e2e / clear e2e blockers / local-proof | `l9-e2e-blocker-resolution` |
| Campaign / `/autonomy` / PR poll while continuing | `l9-bounded-autonomy` (hint; packet required) |
| SaaS admin UI / cartridge / API insufficient | `l9-ui-operator` (hint; human approve for run) |
| PR review / merge blockers / readiness | `l9-pr-remediation` (hint; Diagnose only unless mutate intent) |
| Explore unfamiliar code / map flows | `l9-code-analysis` |
| Gaps / readiness / % complete | `l9-gap-analysis` |
| Library/SDK/API docs before coding | `l9-context7-docs` |
| Compile SOP/prompt into a skill | `l9-skill-compiler` |
| Register/wire a new skill | `l9-wire-skill-into-repo` |
| Harden/converge packs or skill usage | `l9-recursive-optimization` |
| Graphiti / memory prefetch / health | `l9-graphiti-memory` |
| Deep trade-offs / architecture / debug / corpus | `l9-structured-reasoning` |
| What should I do next | `l9-ynp` |
| CI bootstrap | `l9-setting-up-ci` |
| Security / secrets exposure | `l9-auditing-security` |
| Performance / slow app | `l9-auditing-performance` |
| Active incident | `l9-incident-response` |

Authority: `skills/AUTONOMY_MANIFEST.yaml` (`claude_routing`) +
`ops/generated/skill-registry.json`. Shared scorer: `ops/skill_routing/`.
Claude projection: `environment/generated/llm-rules/l9-skill-routing.md`
(generated; do not hand-edit).

<!-- generated-from: rules/23-l9-skill-routing.mdc; do-not-edit -->
