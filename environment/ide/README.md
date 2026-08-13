# IDE profile (Cursor)

Declarative desired state for the **editor** in every governed workspace: which
extensions are installed machine-wide, and which `.vscode/settings.json` keys the
profile owns. Reconciled by `ops/scripts/install_ide_profile.sh`.

> **Peer adapter:** `environment/agents/adapters/claude-code/` is the Claude Code environment
> (CLI · Web · Mobile). It renders the **same** `policy.json` through a different
> target — see `render.claude.json` there. For Claude Code, formatter ownership is
> carried by the `agentdocs` `CLAUDE.md` block (git-tracked, survives a clone),
> not by `.vscode/` (which never reaches a Web/Mobile sandbox).

> **Not to be confused with `profiles/`.** `profiles/*.md` (`dev_mode`,
> `reasoning_l9`, …) are *agent reasoning* profiles — Markdown that shapes how the
> LLM thinks. This directory is *IDE* configuration — extensions and editor
> settings. They share a word and nothing else.

## Files

| File | Purpose |
|---|---|
| `policy.json` | **Ownership authority.** Which tool owns which language, per class. IDE-neutral |
| `render.cursor.json` | Cursor rendering map: tool name → extension ID and code-action IDs |
| `extensions.core.json` | Extensions installed in every governed workspace |
| `extensions.eslint_owned.json` | Extra extensions for ESLint-owned workspaces (adds Prettier) |
| `settings.base.json` | Editor hygiene keys applied everywhere |
| `settings.python.json` | Python type-check mode (Pyright basic) — no formatter keys |
| `settings.node.json` | Superseded by `policy.json`; kept for reference, read by nothing |
| `exceptions.yaml` | Repos and heuristics that classify a workspace as `eslint_owned` |

## Policy vs rendering

`policy.json` says *"Biome owns TypeScript in `biome_default`"*. `render.cursor.json`
says *"the Biome formatter is `biomejs.biome`"*. The installer joins the two into
`[typescript]: { editor.defaultFormatter: … }`. Extension IDs and `editor.*` keys
appear only on the rendering side, so a second IDE gets its own
`render.<ide>.json` and `policy.json` never changes.

Ownership entries carry an `authority`: `governance` means this profile declares the
binding, `repo` means the project's own config decides and the adapter must render
nothing. That is how `eslint_owned` gets no JS/TS formatter key.

**To change which formatter owns a language, edit `policy.json`.** Editing a
`settings.*.json` payload cannot do it — those files no longer carry ownership.

## Workspace classes

| Class | JS/TS formatter | Python formatter |
|---|---|---|
| `biome_default` | Biome (JS/TS/JSON); built-in JSON language features (JSONC) | Ruff (governance) |
| `eslint_owned` | none written — repo's ESLint/Prettier config wins | Ruff (governance) |

Classification order (first match wins): workspace basename matches
`eslint_owned_repos` → any path segment matches → `eslint.config.*`/`.eslintrc*`
present within depth 2 **and** no `biome.json`. Otherwise `biome_default`.

This is what **formatter exclusivity** means in practice: exactly one formatter is
ever declared per language, and in `eslint_owned` repos the profile declares none
so it cannot fight the project's own config.

## Dispatcher and adapters

`install_ide_profile.sh` classifies the workspace and dispatches; nothing
editor-specific lives in it. Each adapter renders `policy.json` for one target and
prints `key=value` state so the dispatcher can summarize.

| Adapter | Renders | Reaches |
|---|---|---|
| `ops/scripts/adapters/cursor.sh` | extensions (machine) + `.vscode/settings.json` (repo) | desktop Cursor only — both paths are untracked |
| `ops/scripts/adapters/agentdocs.sh` | ownership block in `AGENTS.md` / `CLAUDE.md` | **git-tracked**, so cloud agents see it after a clone |

The agentdocs branch exists because `.vscode/` never survives a clone into a Claude
Code mobile or Cursor cloud sandbox. It only edits files that already exist — it will
not create `AGENTS.md` in a repo that has none.

There are three stamps, at three scopes, and they stay separate on purpose:
`$HOME/.cursor/.l9-ide-desired-hash` (extensions, machine),
`<ws>/.vscode/.l9-ide-desired-hash` (settings, repo),
`<ws>/.vscode/.l9-agentdocs-hash` (docs block, repo).

No adapter exists for Zed or JetBrains. Add one the first time a governed repo is
actually opened in that editor.

## Managed-key merge

The profile never rewrites `settings.json` wholesale. On each run it writes a key
only if the key is **absent**, or if the previous run's stamp
(`.vscode/.l9-ide-desired-hash`) records that key as managed by the profile. Keys
you or the repo set are left alone permanently. Keys the profile used to manage but
no longer declares are removed. A `settings.json` containing comments (JSONC) is
detected and skipped untouched rather than reformatted.

Commit `.vscode/settings.json` if the repo wants the settings shared; add it to
`.gitignore` if not. Either works — the merge is driven by the stamp file, not by
git state. The stamp itself (`.vscode/.l9-ide-desired-hash`) is machine state and
should be gitignored.

## Commands

```bash
make ide-profile                      # reconcile the current workspace
make ide-profile-test                 # fixture selftest (no writes outside TMPDIR)
bash ops/scripts/install_ide_profile.sh --dry-run /path/to/repo
bash ops/scripts/install_ide_profile.sh --force /path/to/repo
```

Automatic activation: `session_start_bootstrap.sh` (backgrounded, `--quiet`) and
`setup_workspace_symlinks.sh`.

## Changing the desired state

Edit the JSON/YAML here and commit. The hash stamp changes, so the next session in
each workspace re-reconciles. Removing a key from a settings file removes it from
workspaces where the profile owned it.

## Claude Code CLI hygiene

The IDE profile assumes a single Claude Code install. If `claude` was ever
installed through npm globally, that stale copy shadows the native one in
`~/.local/bin` and rejects current marketplace schemas, which makes
`setup_claude_code_plugins.sh` fail in confusing ways. Remove it once:

```bash
npm uninstall -g @anthropic-ai/claude-code   # no-op if never installed
which -a claude                              # expect only ~/.local/bin/claude
```

Both `session_start_bootstrap.sh` and `setup_claude_code_plugins.sh` prepend
`~/.local/bin` to PATH to defend against this, but removing the stale copy is the
real fix.
