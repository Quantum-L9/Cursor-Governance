# Plugin profile (Cursor + Claude Code)

Declarative desired state for which **AI-tooling plugin capabilities** load in
each governed workspace. This is the plugin-axis sibling of
[`environment/ide/`](../ide/README.md) — same policy/rendering split, same
`exceptions.yaml` classification pattern — applied to a different axis (rules,
skills, commands, and third-party marketplace plugins, not editor
extensions/formatters).

> **Not the same problem as `environment/ide/`.** That directory governs
> *editor* settings (which formatter owns which language). This directory
> governs which *plugin bundles* (Cursor local plugins, Claude Code marketplace
> plugins) load into a given repo's agent context at all.

## Files

| File | Purpose |
|---|---|
| `policy.json` | **Capability ownership.** Which capabilities each workspace class gets. Tool-neutral |
| `render.cursor.json` | Cursor rendering map: capability → local plugin path (or `null` + a documented reason) |
| `render.claude.json` | Claude Code rendering map: capability → `plugin@marketplace` id + install scope |
| `exceptions.yaml` | Repos and heuristics that classify a workspace as `odoo_plasticos` / `aws_infra` / `zep_memory` |

## Policy vs rendering

`policy.json` says *"every workspace gets `docs-lookup`; `aws_infra`
workspaces additionally get `aws-infra-guidance`."* `render.claude.json` says
*"`docs-lookup` is `context7@claude-plugins-official` at `-s user` scope, and
`aws-infra-guidance` is `aws-core@claude-plugins-official` at `-s project`
scope."* `render.cursor.json` renders both of those to `null` today, because no
Cursor-side artifact exists for either capability outside the always-on
`l9-governance` plugin. Each adapter joins policy + its own render file;
capability names never change, only how (or whether) a given tool satisfies
them.

**To change which capability a class gets, edit `policy.json`.** To change how
a tool satisfies an existing capability, edit that tool's `render.*.json`.
Editing a render file cannot add or remove a capability from a class — that is
policy's job, same separation `environment/ide/policy.json` already
established for formatters.

## Honest gaps, not placeholders

`render.cursor.json` renders `aws-infra-guidance` and `zep-memory-guidance` to
`null` with an explicit note. There is no Cursor-side artifact for either
capability today — no bundle was authored, so none is declared. When one is
authored (a real `plugins/<name>-addon/` directory with its own
`.cursor-plugin/plugin.json`), update `render.cursor.json` to point at it. Do
not invent a bundle path here to make the table look complete.

## Workspace classes

| Class | Cursor artifact | Claude artifact |
|---|---|---|
| `core_default` | `l9-governance` local plugin (`rules/`, `skills/`, `commands/`), loaded unconditionally via `~/.cursor/plugins/local/l9-governance` | `context7`, `desktop-commander`, `hookify`, `pr-review-toolkit` at `-s user` |
| `odoo_plasticos` | none, by design — see below | unchanged (no Claude-side addon modeled) |
| `aws_infra` | unchanged (no Cursor-side addon exists) | + `aws-core@claude-plugins-official` at `-s project` |
| `zep_memory` | unchanged (no Cursor-side addon exists) | + `building-with-zep@zep` at `-s project` |

**`odoo_plasticos` note:** an earlier plan for this profile called for a
`plugins/odoo-plasticos-addon` local plugin bundling the three Odoo/PlasticOS
rule files, loaded conditionally via `workspaceOpen`. Before that addon was
built, commit `bbc74c3` ("cursor rules stabilization", 2026-07-22) already
deleted `rules/30-odoo-native.mdc`, `rules/95-plasticos-equipment-policy.mdc`,
and `rules/98-odoo-sh-staging.mdc` from this repo and moved that content to the
consumer repo's own repo-owned `.cursor/rules/` overlay instead — a different,
already-committed resolution to the same problem. Per
`91-existing-code-source-of-truth.mdc`, the established decision wins:
`render.cursor.json` renders `odoo-plasticos-rules` to `null` rather than
resurrecting the deleted files into a competing governance-side addon. The
classification in `exceptions.yaml` and the `workspaceOpen` hook's lookup logic
still exist, so a future cross-repo addon (if one is ever justified) only needs
a `render.cursor.json` update, not new classification plumbing.

Classification order (first match wins), from `exceptions.yaml`: `odoo_plasticos`
→ `aws_infra` → `zep_memory` → otherwise `core_default`. Each category checks an
explicit repo-name list first, then a marker-file heuristic at depth ≤ 2, the
same two-step pattern `environment/ide/exceptions.yaml` uses for
`eslint_owned`.

## Adapters

| Adapter | Renders | Mechanism |
|---|---|---|
| `ops/scripts/setup_workspace_symlinks.sh` | `render.cursor.json` (core capabilities only — always on) | `~/.cursor/plugins/local/l9-governance` symlink to the governance repo root |
| `ops/hooks/workspace_open_plugin_loader.py` | `render.cursor.json` (class-gated capabilities) | Cursor `workspaceOpen` hook → `{"pluginPaths": [...]}` |
| `ops/scripts/setup_claude_code_plugins.sh` | `render.claude.json` | `claude plugin install -s user\|project <plugin>` |

`setup_workspace_symlinks.sh` handles the *unconditional* Cursor plugin load
(same for every repo, does not depend on classification). The `workspaceOpen`
hook handles the *conditional* addon load and is the only piece of this
profile with an unverified reliability caveat — see the root plan's Risks
section. If the hook never fires on a given Cursor build, the addon simply
never loads; `core_default` capabilities are unaffected either way.

## Changing the desired state

Edit `policy.json` / `exceptions.yaml` / a `render.*.json` and let the next
session's reconcilers pick it up — `setup_claude_code_plugins.sh`'s
`STAMP_FILE`/`DESIRED_HASH` mechanism re-runs automatically when the desired
set changes; the Cursor side has no content hash today (it is a static
symlink plus a hook that re-evaluates every workspace open), so a `plugin.json`
or addon content change takes effect the next time Cursor reloads the plugin.
