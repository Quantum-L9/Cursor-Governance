# NORMALIZE_TASK

Three stages. Stages 1 and 2 are mechanical and safe. Stage 3 changes behavior.

## STAGE 1 - Frontmatter normalization (mechanical, no behavior change)

### 1.1 Archive before stripping

Create `docs/rules-frontmatter-archive.yaml` recording, for every file in
`rules/`, the complete original frontmatter as parsed. This is the undo
record. Do not proceed until it exists and contains an entry per file.

### 1.2 Strip non-native fields

For every `rules/*.mdc`, rewrite frontmatter to contain only, in this order:

```
description
globs
alwaysApply
```

Remove all other keys, including but not limited to `activation`,
`authority`, `context_cost`, and any stable-ID key. Report a count per
removed key name.

**Do not change any retained value.** `alwaysApply: true` stays `true`.

### 1.3 Remove dead metadata

- Where `alwaysApply: true`, delete any `globs` key. Globs are ignored when
  always-apply is set. Known cases: `99-graphiti-temporal.mdc`,
  `98-graphiti-memory-gate.mdc`, `97-graph-layer-boundary.mdc`.
- Delete empty `globs: []`. Known case: `05-ask-mode.mdc`.

### 1.4 Unify glob syntax

Convert every `globs` value to a single comma-separated string. Replace YAML
list form:

```yaml
globs:
  - "**/e2e/**/*.tsx"
  - "playwright.config.ts"
```

with:

```yaml
globs: **/e2e/**/*.tsx, playwright.config.ts
```

One shape repo-wide.

### 1.5 Backfill missing descriptions

Any rule with `alwaysApply: false` and no `globs` and no `description` is
reachable only by `@`-mention. For each, either write a trigger-style
description or flag it as intentionally manual. Report the list; do not
guess a description for a rule whose purpose is unclear.

## STAGE 2 - Mechanical fixes

### 2.1 Resurrect the dead file

`rules/93-perplexity-research-protocol.md` is a `.md` file in the rules
directory, which the rules system ignores entirely. 6.5 KB is currently
inert.

- Rename to `93-perplexity-research-protocol.mdc`.
- Add compliant frontmatter per STANDARD.md shape D (agent-selected).
- Update every reference to the old path, including `RULES-MANIFEST.yaml`.

### 2.2 Verify rule discovery path

Cursor project rules load from `.cursor/rules`. This repo stores them in
`rules/` at root. Confirm how they reach `.cursor/rules` - symlink, plugin
manifest declaration, or copy step. Report the mechanism found.

If discovery relies on convention, declare explicit component paths in
`.cursor-plugin/plugin.json` so it is deterministic.

### 2.3 Manifest reduction

- Designate `RULES-MANIFEST.yaml` the only authored manifest.
- Add `rules/RULES-MANIFEST.json` and `rules/RULES-MANIFEST.md` to
  `.cursorignore` so 69 KB of derived data stops entering agent context.
- Add a make target that regenerates both from the YAML.

### 2.4 CI gate

Create `tools/check_rules_standard.py` enforcing STANDARD.md Section 6.
Wire to `Makefile` as `rules-check` and into `.pre-commit-config.yaml`.

Set the always-apply threshold to the **current measured value** on first
commit, with a comment stating the target of 12288. The gate ratchets: each
PR may lower it, never raise it.

## STAGE 3 - Retiering (one rule per commit, approval required)

Work `MIGRATION-MAP.md` top down - largest bytes first, since that is where
the savings are.

For each rule:

1. State the current tier and proposed tier.
2. If moving to G, propose the exact glob string and justify coverage.
3. If moving to D, write the trigger-style description.
4. If X (merge or move), do not delete the source until the target exists
   and is reviewed.
5. Re-run `make rules-check` and report the new always-apply total.

### Merge targets

- `30-memory.mdc` absorbs `03-graphiti-memory`, `04-cursor-redis-session`,
  `87-cursor-memory-kernel`, `98-graphiti-memory-gate`,
  `99-graphiti-temporal`. Must open with an explicit precedence section
  resolving conflicts between the five sources. Leave `03-mcp-memory.mdc`
  glob-scoped as it already is.
- `10-write-authority.mdc` absorbs `01-git-push-prohibition`,
  `96-git-push-approval`, `99-no-auto-commit`, `94-deployment-prohibition`,
  `87-l4-local-autonomy`. Must express one authority table: operation, who
  authorizes, what gate enforces.
- `92-learned-lessons.mdc` moves to `l9-graphiti-memory` retrieval.
- `99-incident-report.mdc` moves to `commands/incident-report.md`.
- `87-cursor-subagent-orchestration.mdc` becomes real files under `agents/`.

Never batch two merges in one PR.
