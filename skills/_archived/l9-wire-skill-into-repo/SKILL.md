---
name: l9-wire-skill-into-repo
description: "deprecated — do not activate. use l9-wire-into-repo. archived out of live skills/ discovery."
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, wiring, unwire, deprecate, registry, skills, discovery, deprecated]
  owner: igor_beylin
  status: deprecated
  version: 2.1.0
  updated: 2026-09-19
  superseded_by: l9-wire-into-repo
---

# Wire Skill Into Repo (ARCHIVED)

> **Deprecated and archived.** Generic repository wiring is owned by
> `skills/l9-wire-into-repo/`. This pack is retained as history only —
> its references below describe retired machinery and are not repaired.

Do not activate. Superseded by **`l9-wire-into-repo`**. Skill-specific wiring
was absorbed into that generic topology (`wire` / `rewire` / `verify` /
`unwire`) in PR #435.

## Purpose

A skill is **not complete** until agents can discover it — and a retired skill is
**not complete** until agents **cannot**. This skill owns both directions:

| Mode | Outcome |
|------|---------|
| **wire** | Pack is discoverable and registered |
| **unwire** | Pack is archived out of live `skills/` and deregistered everywhere |

Deprecation without archive/unwire is a protocol violation. Do not leave
`status: deprecated` packs under live discovery paths.

## Mode selection (automatic)

| Signal | Mode |
|--------|------|
| New/updated pack; “wire” / “register” / post-`l9-skill-compiler` | **wire** |
| “deprecate” / “retire” / “unwire” / “deregister” / “archive” / “supersede” | **unwire** |
| Live `skills/<name>/` with `status: deprecated` or name `*-deprecated` | **unwire** (mandatory) |

Unwire procedure: [references/unwire-deprecate.md](references/unwire-deprecate.md).

## Core Contract — wire

| Step | Action | Load |
|------|--------|------|
| 1 | Confirm pack + metadata | inputs table below |
| 2 | Detect registry layout | [references/layout-detection.md](references/layout-detection.md) |
| 3 | Apply project adapter | `.claude/adapters/*-repo-wiring.md` |
| 4 | Update registries | [references/registry-templates.md](references/registry-templates.md) |
| 5 | Validate | [references/validation-checklist.md](references/validation-checklist.md) |
| 6 | Report | wiring complete markdown |

## Core Contract — unwire

| Step | Action | Load |
|------|--------|------|
| 1 | Confirm name, path, `superseded-by` | [references/unwire-deprecate.md](references/unwire-deprecate.md) |
| 2 | Freeze frontmatter (`status: deprecated`, disable invocation) | same |
| 3 | `git mv` live pack → `skills/_archived/<name>/` | same |
| 4 | Clear tiers, docs, preloads, routing; sync generated artifacts | [references/registry-templates.md](references/registry-templates.md) |
| 5 | Prove absence from every live discovery surface | [references/validation-checklist.md](references/validation-checklist.md) § Unwire |
| 6 | Report | unwire complete markdown |

## Authority Order

1. Explicit skill name, path, scope, invocation tier (wire) or superseding skill (unwire).
2. Repo / governance registry ground truth — `skills/AUTONOMY_MANIFEST.yaml`,
   `.claude/README.md`, `AGENTS.md`, generated skill-registry, adapter symlinks.
3. `CANONICAL_LAW.md` skill wiring + deprecate-archive law.
4. Project adapter when present.
5. This skill's references.
6. `Unknown` — STOP if mandatory registry or archive destination is missing.

## Inputs (gather first)

### Wire

| Field | Required | Notes |
|-------|----------|-------|
| `skill-name` | yes | Must match directory name and frontmatter `name` |
| `skill-path` | yes | Absolute or repo-relative path to skill folder |
| `description` | yes | Lowercase what + when (same text in all registries) |
| `scope` | yes | `global` or `project` |
| `invocation` | yes (L9 global) | `auto` or `explicit` — sets `AUTONOMY_MANIFEST.yaml` tier |
| `preload-subagents` | no | Subagents that preload via `skills:` frontmatter |

### Unwire

| Field | Required | Notes |
|-------|----------|-------|
| `skill-name` | yes | Pack being retired |
| `skill-path` | yes | Current live path |
| `superseded-by` | yes if replacement exists | Canonical live skill |
| `scope` | yes | `global` or `project` |

If any required field is missing, stop and ask — do not guess registry rows.

## Scope rules

| Scope | Skill location (SSOT) | Repo / adapter wiring |
|-------|----------------------|------------------------|
| **global (L9)** | `~/.cursor-governance/skills/l9-{name}/` (== `.cursor-commands/skills/`) | `AUTONOMY_MANIFEST.yaml` + generated registry + LLM adapter symlinks; `AGENTS.md` when maintaining agent docs |
| **project** | `.claude/skills/` or repo-local skills root | Project Skills table + `AGENTS.md` |

L9 universal skills use the `l9-` prefix. Do not duplicate L9 packs into consumer
`.claude/skills/` as real directories — adapters receive symlinks via reconcile.

**Deprecated global packs** live only at
`~/.cursor-governance/skills/_archived/<name>/`.

## Resource Map

- [references/layout-detection.md](references/layout-detection.md) — profile A/B detection.
- [references/registry-templates.md](references/registry-templates.md) — table row and manifest templates.
- [references/unwire-deprecate.md](references/unwire-deprecate.md) — archive + deregister protocol.
- [references/validation-checklist.md](references/validation-checklist.md) — fail-closed wire/unwire checks.

## Validation

Report `Validation: FAIL` if any mandatory checklist item applies.

- **Wire:** trigger text MUST be identical across registries; L9 global skills MUST
  appear in exactly one `AUTONOMY_MANIFEST.yaml` tier.
- **Unwire:** pack MUST NOT remain under live `skills/`; MUST be absent from both
  autonomy tiers, skill-registry, and adapter symlinks. `status: deprecated` alone
  is FAIL.

## Failure Handling

- Missing `SKILL.md` or empty pack → FAIL; do not register.
- Duplicate registry row → dedupe before reporting PASS.
- Ambiguous layout → load layout-detection ref; ask user if still ambiguous.
- `agents/openai.yaml` present → rename to `agents/meta.yaml`; wire via this skill only.
- Skill pack under `.claude/` but not under `.claude/skills/` → move/symlink into `.claude/skills/{name}/` then re-reconcile.
- Deprecated pack still at live `skills/<name>/` → mandatory unwire; do not “fix” by docs-only edits.
- Sync reports live deprecated skills → archive + deregister before any other skill work.

## Daisy-chain contract

| Upstream / sibling | When |
|--------------------|------|
| `l9-skill-compiler` | After build, before validation sign-off → **wire** |
| `l9-update-agent-docs` | After wire/unwire changes skill indexes → refresh agent docs if those files list skills |
| Replacement skill | When deprecating → **wire** canonical pack (if needed), then **unwire** old pack in the same session |
