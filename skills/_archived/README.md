# Archived skills

Retired skill packs live here — **not** under the live `skills/` discovery root.

## Law

Deprecated skills **must not** remain as top-level `skills/<name>/` directories.
They must be:

1. Moved here via `git mv skills/<name> skills/_archived/<name>`
2. Removed from `AUTONOMY_MANIFEST.yaml` tiers (never auto- or explicit-invoke)
3. Dropped from adapter reconcile / skill-registry generation
4. Referenced only as historical comparison under `skills/_archived/`

Live discovery surfaces (`skills/*/SKILL.md`, Cursor plugin skills root, Claude
adapter symlinks) must never see archived packs.

**Operating skill:** `l9-wire-skill-into-repo` owns unwire/deprecate/deregister
(`references/unwire-deprecate.md`). Do not invent a parallel retirement path.

## Contents

| Pack | Superseded by |
|---|---|
| `l9-pr-remediation-deprecated/` | `skills/l9-pr-remediation/` |
| `l9-structured-reasoning-deprecated/` | `skills/l9-structured-reasoning/` |
