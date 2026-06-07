---
name: l9-wire-skill-into-repo
description: registers new or updated agent skills into repo discovery tables, subagent preload lists, and related agent docs after skill creation. use immediately after l9-skill-compiler finishes, when the user asks to wire or register a skill, or when a skill pack exists but is not yet discoverable.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, wiring, registry, skills, discovery]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
---

# Wire Skill Into Repo (L9)

## Purpose

A skill is **not complete** until agents can discover it. Run as the **final step** after `l9-skill-compiler` delivers a skill pack.

## Core Contract

| Step | Action | Load |
|------|--------|------|
| 1 | Confirm pack + metadata | inputs table below |
| 2 | Detect registry layout | [references/layout-detection.md](references/layout-detection.md) |
| 3 | Apply project adapter | `.claude/adapters/*-repo-wiring.md` |
| 4 | Update registries | [references/registry-templates.md](references/registry-templates.md) |
| 5 | Validate | [references/validation-checklist.md](references/validation-checklist.md) |
| 6 | Report | wiring complete markdown |

## Authority Order

1. Explicit skill name, path, scope, and invocation tier.
2. Repo registry ground truth — `.claude/README.md`, `AGENTS.md`, `AUTONOMY_MANIFEST.yaml`.
3. Project adapter when present.
4. This skill's references.
5. `Unknown` — STOP if mandatory registry missing.

## Inputs (gather first)

| Field | Required | Notes |
|-------|----------|-------|
| `skill-name` | yes | Must match directory name and frontmatter `name` |
| `skill-path` | yes | Absolute or repo-relative path to skill folder |
| `description` | yes | Lowercase what + when (same text in all registries) |
| `scope` | yes | `global` or `project` |
| `invocation` | yes (L9 global) | `auto` or `explicit` — sets `AUTONOMY_MANIFEST.yaml` tier |
| `preload-subagents` | no | Subagents that preload via `skills:` frontmatter |

If any required field is missing, stop and ask — do not guess registry rows.

## Scope rules

| Scope | Skill location | Repo wiring |
|-------|----------------|-------------|
| **global** | `~/.cursor/skills/l9-{name}/` | L9 Global Skills table + `AGENTS.md` when maintaining agent docs |
| **project** | `.cursor/skills/` or `.claude/skills/` | Project Skills table + `AGENTS.md` |

L9 universal skills use the `l9-` prefix. Do not duplicate L9 packs into `.claude/skills/`.

## Resource Map

- [references/layout-detection.md](references/layout-detection.md) — profile A/B detection.
- [references/registry-templates.md](references/registry-templates.md) — table row and manifest templates.
- [references/validation-checklist.md](references/validation-checklist.md) — fail-closed wiring checks.

## Validation

Report `Validation: FAIL` if any mandatory checklist item applies. Trigger text MUST be identical across registries. L9 global skills MUST appear in exactly one `AUTONOMY_MANIFEST.yaml` tier.

## Failure Handling

- Missing `SKILL.md` or empty pack → FAIL; do not register.
- Duplicate registry row → dedupe before reporting PASS.
- Ambiguous layout → load layout-detection ref; ask user if still ambiguous.
- `agents/openai.yaml` present → remove; wire via this skill only.

## Daisy-chain contract

| Upstream | When |
|----------|------|
| `l9-skill-compiler` | After build, before validation sign-off |
