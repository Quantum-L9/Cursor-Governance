# IDE profile (Cursor)

Declarative desired state for the **editor** in every governed workspace: which
extensions are installed machine-wide, and which `.vscode/settings.json` keys the
profile owns. Reconciled by `ops/scripts/install_ide_profile.sh`.

> **Not to be confused with `profiles/`.** `profiles/*.md` (`dev_mode`,
> `reasoning_l9`, …) are *agent reasoning* profiles — Markdown that shapes how the
> LLM thinks. This directory is *IDE* configuration — extensions and editor
> settings. They share a word and nothing else.

## Files

| File | Purpose |
|---|---|
| `extensions.core.json` | Extensions installed in every governed workspace |
| `extensions.eslint_owned.json` | Extra extensions for ESLint-owned workspaces (adds Prettier) |
| `settings.base.json` | Editor hygiene keys applied everywhere |
| `settings.python.json` | Ruff as formatter, Ruff fix/organize-imports on save, Pyright basic |
| `settings.node.json` | Biome as `defaultFormatter` for JS/TS/JSON — **`biome_default` only** |
| `exceptions.yaml` | Repos and heuristics that classify a workspace as `eslint_owned` |

## Workspace classes

| Class | JS/TS formatter | Applied settings |
|---|---|---|
| `biome_default` | Biome | base + python + node |
| `eslint_owned` | none written — repo's ESLint/Prettier config wins | base + python |

Classification order (first match wins): workspace basename matches
`eslint_owned_repos` → any path segment matches → `eslint.config.*`/`.eslintrc*`
present within depth 2 **and** no `biome.json`. Otherwise `biome_default`.

This is what **formatter exclusivity** means in practice: exactly one formatter is
ever declared per language, and in `eslint_owned` repos the profile declares none
so it cannot fight the project's own config.

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
