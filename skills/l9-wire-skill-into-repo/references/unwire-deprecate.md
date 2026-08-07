<!-- L9_META
l9_schema: 1
parent: l9-wire-skill-into-repo
layer: reference
role: unwire_deprecate_protocol
tags: [wiring, unwire, deprecate, archive, registry]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-06
/L9_META -->

# Unwire / Deprecate / Deregister (L9)

**Law:** A deprecated skill must not remain under live `skills/` discovery.
Marking `status: deprecated` in place is **not** sufficient. Archive + unregister
is mandatory and automatic whenever this skill is invoked for retirement.

## When this mode applies (no user re-prompt needed)

Enter **unwire mode** if any of these are true:

- User says deprecate, retire, unwire, deregister, archive, or supersede a skill
- Frontmatter has `status: deprecated` (or equivalent) while the pack still lives
  at a live discovery path
- Pack directory is named `*-deprecated` under live `skills/`
- A canonical replacement skill exists and the old pack is reference-only

Do **not** wait for the user to restate the archive law.

## Authority order (unwire)

1. Explicit skill name + superseding skill (if any)
2. Live discovery roots — governance `skills/` SSOT, adapter symlinks, manifests
3. `CANONICAL_LAW.md` §6 (deprecated skills cannot remain in live `skills/`)
4. This reference
5. `Unknown` — STOP if archive destination or registry ownership is ambiguous

## Inputs

| Field | Required | Notes |
|-------|----------|-------|
| `skill-name` | yes | Current pack / frontmatter name |
| `skill-path` | yes | Current live path (must be under discoverable `skills/`) |
| `superseded-by` | yes if replacement exists | Canonical live skill name |
| `scope` | yes | `global` (governance SSOT) or `project` |
| `retain-history` | no | default `true` — `git mv` to archive, never hard-delete |

## Live discovery roots (must be cleared)

| Surface | What “registered” means |
|---------|-------------------------|
| Governance SSOT | Top-level `skills/<name>/SKILL.md` (not under `_archived/`) |
| `skills/AUTONOMY_MANIFEST.yaml` | Any `tiers.auto_invoke` or `tiers.explicit_only` row |
| Skill registry | `environment/claude-code/generated/skill-registry.json` (or current generated path) |
| Adapter symlinks | `~/.claude/skills/<name>`, `<workspace>/.claude/skills/<name>` |
| Docs indexes | README / `AGENTS.md` / `.claude/README.md` skill tables |
| Subagent preload | `skills:` frontmatter lists |
| Routing notes | `reasoning_routing`, `claude_routing`, adapters that name the pack |

Archived packs under `skills/_archived/<name>/` are **not** live discovery.

## Procedure (fail-closed, ordered)

### 1. Freeze identity

- Confirm `SKILL.md` frontmatter `name` matches folder name.
- Set / keep `status: deprecated`.
- Set `disable-model-invocation: true`.
- Set `superseded_by: <canonical>` when a replacement exists.
- Description must say deprecated / do not activate / use replacement.

### 2. Archive out of live `skills/`

Governance / L9 global:

```bash
mkdir -p skills/_archived
git mv "skills/<name>" "skills/_archived/<name>"
```

Project scope: move to the repo’s archive convention if one exists; otherwise
`<skills-root>/_archived/<name>/`. Prefer `git mv` (history-preserving).

**Forbidden:** leave the pack at `skills/<name>/` with only a deprecated badge.
**Forbidden:** hard-delete without archive when `retain-history` is true.

### 3. Deregister

Remove the skill from every live surface:

1. Delete `AUTONOMY_MANIFEST.yaml` tier rows (`auto_invoke` and `explicit_only`).
2. Add / update `do_not_migrate_to_skills` to the **archived** path:

   ```yaml
   - item: "skills/_archived/<name>/"
     reason: "superseded by skills/<canonical>/; archived out of live skills/ discovery — never auto-invoke or reconcile"
   ```

3. Strip README / `AGENTS.md` / `.claude/README.md` live skill rows; point at
   `skills/_archived/` only if a historical index is maintained.
4. Remove from subagent `skills:` preload lists.
5. Rewrite routing notes that treat the pack as active.
6. Run generated sync so registry + adapter symlinks drop the name:

   ```bash
   make -C "$HOME/.cursor-governance" sync-generated
   # or: python3 ops/scripts/sync_generated_artifacts.py --root "$HOME/.cursor-governance"
   ```

### 4. Prove absence

Live tree must satisfy all of:

- [ ] No `skills/<name>/` (top-level)
- [ ] Pack exists only under `skills/_archived/<name>/` (if retained)
- [ ] Name absent from both AUTONOMY tiers
- [ ] Name absent from generated skill-registry
- [ ] No adapter symlink `*/.claude/skills/<name>`
- [ ] `sync_generated_artifacts` / `assert_no_live_deprecated_skills` would PASS
- [ ] Docs do not list the pack as activatable

Any miss → `Validation: FAIL` — do not report unwire complete.

## Report template (unwire)

```markdown
## Unwire complete: {skill-name}

- Mode: deprecate / archive / deregister
- From: `skills/{name}/`
- To: `skills/_archived/{name}/`
- Superseded by: `{canonical or n/a}`
- Registries cleared: AUTONOMY tiers, skill-registry, adapter symlinks, docs, subagent preloads
- Validation: PASS | FAIL
- Residual references (non-discovery only): …
```

## Relationship to wire mode

| Mode | Outcome |
|------|---------|
| **wire** | Pack is discoverable and registered |
| **unwire** | Pack is not discoverable; archived + deregistered |

Wiring a replacement (`superseded-by`) is a separate **wire** pass on the
canonical pack. Unwire the old pack in the same session whenever deprecation
is the user intent.
