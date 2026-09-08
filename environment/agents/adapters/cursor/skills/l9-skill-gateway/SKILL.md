---
name: l9-skill-gateway
description: Cursor adapter gateway to the canonical L9 skill corpus. use when a task is non-trivial and you must load the routed canonical skill, when the conversation route receipt is missing, degraded, or stale, or when you need to resolve which canonical skill applies. do not use as a skill inventory — the corpus is not listed here.
metadata:
  skill_schema: 1
  layer: adapter
  role: cursor_native_gateway
  surface: cursor
  owner: governance-control-plane
  status: active
  version: 1.0.0
  updated: 2026-09-06
---

# L9 skill gateway (Cursor native adapter)

This is the **only** skill Cursor discovers natively. It is an adapter, not a
capability: it owns no routing, no scoring, and no inventory.

## What this skill is not

- The native Cursor skill roster is **not** the canonical L9 inventory. Seeing
  only this skill tells you nothing about which L9 capabilities exist.
- Canonical inventory lives in the generated registry:
  `~/.cursor-governance/ops/generated/skill-registry.json`
  (source of truth: `skills/AUTONOMY_MANIFEST.yaml`).
- Canonical resources live under `~/.cursor-governance/skills/<name>/SKILL.md`.
- This file never enumerates the corpus. Do not infer availability, count, or
  names of canonical skills from anything Cursor lists natively.

## Normal operation — consume the scoped route receipt

Every prompt writes one receipt for **this conversation** (the sessionStart
banner `### Route locator` names the path; it is
`~/.cursor/l9/routes/<conversation-key>/current.json`). Read it first.

| Receipt `status` | Action |
|---|---|
| `routed` | Load exactly `decision.primary.skill_md`, then at most the two `decision.supporting[].skill_md` paths. Follow that contract. Do not re-route or re-discover. |
| `no_route` | Proceed without a canonical skill. Do not borrow an earlier route. |
| `disabled` | Proactive routing is off; use the fallback below only if the task needs a skill contract. |
| `degraded`, missing, invalid, or a `generation_id` that does not match the registry | Fallback below. |

## Fallback — invoke the shared resolver

```bash
"$HOME/.cursor-governance/.venv/bin/python" \
  "$HOME/.cursor-governance/ops/skill_routing/resolve.py" --prompt "<the user request>"
```

The resolver runs the same deterministic router and materializer the hook
runs and prints exact `SKILL.md` paths. Load what it names (one primary, at
most two supporting). If it prints `no_route`, proceed without a skill.

## Invariants (binding)

1. Exactly **one primary** skill; at most **two supporting** skills.
2. Routing evidence — routed receipt or resolver output — is **never**
   mutation authority. `source: explicit_hint` means Read/attach only; the
   skill's own contract, an explicit user invoke, a campaign packet, or human
   approval grants action.
3. Never duplicate route scoring here or in chat. The brain is
   `ops/skill_routing/route_prompt.py`; the inventory is the registry.
4. Never enumerate, mirror, copy, or symlink canonical skills into the Cursor
   native projection. Adding canonical skills never changes this roster.
5. A canonical `SKILL.md` that the receipt or resolver names is the contract to
   follow; a skill that neither names is not "available" because Cursor did or
   did not list it.
