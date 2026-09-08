# Claude Code Preservation Contract

**Status:** Normative
**Applies to:** PR #513 (Virtual Skill Plane v2) and any successor change that
virtualizes, bounds, or reshapes Cursor skill discovery.
**Gate:** `make claude-preservation-check` ·
`environment/agents/adapters/claude-code/tests/test_claude_preservation_contract.py`

## Governing principle

PR #513 is a Cursor-specific isolation change.

Claude Code is an existing, independent consumer of the canonical L9 skill
corpus and MUST remain behaviorally unchanged by it. Cursor compatibility
concerns MUST be solved at the Cursor boundary. Claude Code MUST NOT be
modified merely because Cursor can discover Claude-compatible skill locations.

The authoritative boundary is:

> Cursor problem → Cursor solution

not:

> Cursor problem → Claude Code redesign

## Required invariants

| ID | Invariant |
|---|---|
| **CC-001** | Preserve Claude Code skill discovery, availability, invocation, and execution behavior. No intentional Claude Code behavior change is permitted. |
| **CC-002** | Do not remove, suppress, relocate, rename, filter, virtualize, or replace L9 skills reaching Claude Code through existing adapter paths — `~/.claude/skills` and, where governed by the repository, `.claude/skills`. |
| **CC-003** | The existing Claude Code skill-adapter/reconciliation mechanism remains authoritative. Claude Code skill ownership MUST NOT transfer into the Cursor adapter, gateway, route receipts, runtime rules, or plugin configuration. |
| **CC-004** | No cross-agent workaround. A Cursor discovery or cardinality problem MUST NOT be solved by changing Claude Code's skill projection — not by reducing its visible skill count, replacing its skills with a gateway, introducing Claude-specific virtualization, disabling adapter reconciliation, or altering Claude filesystem state solely to stop Cursor observing it. |
| **CC-005** | The canonical corpus under `skills/` is unchanged in role and authority. No second Claude-specific copy of canonical skill content. |
| **CC-006** | No Claude routing redesign — no change to routing semantics, invocation tiers, skill selection policy, or mutation-authority policy, **except** where a pre-existing defect is independently required for correctness **and explicitly separated from the Cursor work**. No Cursor-specific routing mechanism becomes normative for Claude Code. |
| **CC-007** | Claude Code gains no runtime dependency on Cursor hooks, session state, route receipts, plugin manifests, gateway skills, configuration, or processes. It must keep working when Cursor is absent. |
| **CC-008** | Cursor isolation is Cursor-owned. Preventing Cursor from consuming Claude-compatible skill roots is implemented and validated inside the Cursor boundary; Claude Code's expected filesystem state stays intact. |
| **CC-009** | Failure isolation. A missing gateway, invalid receipt, hook failure, registry-consumer failure, plugin-install failure, or Cursor configuration failure MUST have no effect on Claude Code skill availability. |
| **CC-010** | Repository separation. Cursor adapter files may reference shared L9 routing infrastructure but MUST NOT redefine Claude Code behavior. Changes under Claude-specific adapter paths require independent justification. |

## Scope

**In scope** — Claude Code impact analysis, strictly to verify non-regression:
checking that Claude adapter outputs are unchanged, adding non-regression
tests, adding CI assertions that Claude projections are preserved, and
documenting that Claude Code sits intentionally outside the Cursor
virtualization boundary.

**Out of scope** — Claude Code skill virtualization, a Claude gateway skill,
bounded Claude discovery, Claude route receipts, Claude session routing, Claude
adapter redesign, replacing `~/.claude/skills` or `.claude/skills`, cross-agent
capability-plane redesign, and generalized vendor-neutral skill
virtualization. Each requires a separate architecture decision and change set.

## Validation contract

| ID | Validation | Mechanism |
|---|---|---|
| **V-CC-001** | Projection equivalence — for the same canonical corpus, the Claude adapter projection contains the same intended L9 skill set before and after. | `claude_projection_snapshot.py --check` against the attested baseline |
| **V-CC-002** | No Cursor dependency — Claude adapter validation succeeds without Cursor runtime state, receipts, or gateway. | snapshot run under an empty `HOME`; byte-equality against a normal run |
| **V-CC-003** | No cardinality regression — adding a canonical skill still makes it available to Claude Code. | synthetic corpus through `reconcile_claude_l9_skills.py` |
| **V-CC-004** | No removal regression — existing Claude-accessible canonical skills remain accessible. | baseline set difference |
| **V-CC-005** | No adapter mutation — the Cursor installer, hook, or validator never deletes or mutates Claude adapter content. | static write-marker scan of the Cursor adapter |

### How the gate works

The gate is **baseline-attested**, not value-hardcoded. `ops/scripts/claude_projection_snapshot.py`
reads only tracked files — the skill registry, `AUTONOMY_MANIFEST.yaml`
`claude_routing`, and the Claude `skillOverrides` templates — and emits a
deterministic snapshot of Claude Code's projection surface. `--check` diffs it
against `environment/agents/adapters/claude-code/baseline/claude-projection-baseline.json`.

A route's `primary` is not its behavior. Changing a route's signals, weight,
priority, or supporting set repoints Claude just as effectively, so the snapshot
carries a `route_definitions_sha256` digest per route alongside the readable
`routes` map, plus the selection thresholds in `routing_policy`. The digest is
what makes a signals-only edit fail the gate; the readable map is what makes the
failure diagnosable.

Hardcoding a route target inline would either rot on every legitimate change or
invite a silent edit. Pinning the whole surface to one reviewed baseline means
a Claude Code behavior change cannot merge unnoticed: it fails the gate, and
clearing it requires re-attesting the baseline deliberately —

```bash
python3 ops/scripts/claude_projection_snapshot.py --write-baseline
```

— which is precisely the independent justification CC-006 demands. The gate
records what changed; a human decides whether it is allowed.

## Merge gate

PR #513 MUST NOT merge if satisfying Cursor's bounded-discovery requirement
**requires** changing established Claude Code skill behavior. Where Cursor and
Claude Code filesystem compatibility create a conflict that cannot be isolated
at the Cursor boundary, that conflict is surfaced as a separate issue or
architecture decision rather than expanding PR #513.

## Verification of PR #513 (head `3484d5c`, base `051c63c`)

Measured, not asserted. Nine of the ten contract tests pass against the #513
tree: the Cursor virtualization is genuinely isolated. One fails.

**Holds.** CC-002, CC-003, CC-005, CC-007, CC-008, CC-009, CC-010. The
canonical corpus stays at 56 skills in both the shared and Claude-mirrored
registries; `reconcile_claude_l9_skills.py`, `reconcile_claude_settings.py`,
and `hooks/user_prompt_skill_router.py` are untouched; the Claude
`UserPromptSubmit` hook runs to completion with no Cursor state present,
writing only under `~/.claude/l9/`.

**Violated — CC-001 and CC-006.** #513 changes Claude Code routing and
invocation policy:

```
invocation[l9-plan-simple]:                        explicit_only       -> model_allowed
settings_template_skill_overrides[l9-plan-simple]: user-invocable-only -> (removed)
workspace_skill_overrides[l9-plan-simple]:         user-invocable-only -> (removed)
routing_primary_skills:                            added l9-plan-simple
routes[plan]:                                      l9-plan             -> l9-plan-simple
routes[campaign_plan]:                             (none)              -> l9-plan
route_definitions_sha256[plan]:                    8f7bb389…           -> 3a933d13…
route_definitions_sha256[campaign_plan]:           (none)              -> 1968f900…
```

The two digests are not redundant with the `routes` lines above them: the `plan`
route's signal sets also change (13 → 15 positive, 0 → 7 negative), and the
Claude route count goes 34 → 35.

Observed end-to-end through the Claude hook itself, not inferred from the diff:

| Prompt | `main` | #513 |
|---|---|---|
| "create an execution plan for this refactor" | `l9-plan` | `l9-plan-simple` |
| "plan this before coding" | `l9-plan` | `l9-plan-simple` |
| "plan a campaign for the CI rollout" | *(no route)* | `l9-plan` |

**Disposition.** This is a scope violation, not a merge blocker under the merge
gate as written. The merge gate bars #513 only when Cursor's bounded-discovery
requirement *requires* a Claude change; this one does not. The planning-doctrine
fix addresses an independent pre-existing defect (the rule-23/router split-brain,
VSP-P1-002) and is separately authored in PR #512, which carries the identical
`skills/l9-plan-simple/SKILL.md` hunk. The Cursor virtual gateway does not depend
on it.

CC-006 permits that fix — but only "explicitly separated from the Cursor work,"
and bundling it into #513 is not separation. The correct remedy is separation,
not blocking the Cursor work: land the planning-doctrine change on its own
(#512 or a successor) with its own baseline re-attestation, and keep #513 to the
Cursor boundary.

## References

- `environment/skill-adapters/SKILL_ADAPTER_ROOTS.yaml` — adapter root registry
- `ops/scripts/reconcile_claude_l9_skills.py` — authoritative Claude skill projection
- `ops/scripts/reconcile_claude_settings.py` — authoritative Claude settings projection
- `docs/VIRTUAL_SKILL_PLANE_V2_BUILD.md` — the Cursor-side build brief (#513)
