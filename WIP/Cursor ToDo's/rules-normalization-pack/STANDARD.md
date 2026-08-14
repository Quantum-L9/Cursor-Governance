# Rule Standard - Cursor-native only

The contract every file in `rules/` must satisfy. One shape, no exceptions.
This exists so that what you do well in some rules is done in all of them.

## 1. The only three fields Cursor reads

Cursor's rules system reads exactly three frontmatter keys: `description`,
`globs`, and `alwaysApply`. Nothing else is interpreted. Any other key is
inert text that costs tokens and invites drift, because a field nobody
enforces will silently go stale.

**Remove these non-native fields** wherever they appear:

| Field found in repo | Verdict |
|---|---|
| `activation:` | Remove. Duplicates `alwaysApply`/`globs` with no enforcement. |
| `authority:` | Remove from frontmatter. If precedence matters, state it in the body. |
| `context_cost:` | Remove. Self-reported, unverified, and contradicted by actual byte counts. |
| stable ID keys | Remove unless a tool reads them. Only 8 of 65 rules had them, so they cannot be load-bearing. |

If a field is genuinely needed by your own tooling, read it from
`RULES-MANIFEST.yaml` instead. Governance metadata belongs in the manifest;
only activation metadata belongs in frontmatter.

## 2. The four activation modes

The three fields combine into exactly four behaviors:

| `alwaysApply` | `description` | `globs` | Behavior |
|---|---|---|---|
| `true` | ignored | ignored | Always included in every session |
| `false` | - | provided | Auto-attached when a matching file is in context |
| `false` | provided | omitted | Agent reads the description and pulls it in when relevant |
| `false` | omitted | omitted | Included only when you `@`-mention it |

Two consequences that matter for this repo:

- When `alwaysApply: true`, **globs and description are ignored**. Any rule
  carrying both `alwaysApply: true` and `globs: ["**/*"]` has dead metadata.
- When `alwaysApply: false` with neither description nor globs, the rule is
  manual-only. That is a valid choice, but it must be deliberate.

## 3. Canonical frontmatter shapes

Pick exactly one. Field order is fixed. No extra keys.

### A - Always (kernel tier only)

```yaml
---
description: One line, imperative, states what this constrains.
alwaysApply: true
---
```

Do not add `globs`. It is ignored.

### G - Glob-scoped

```yaml
---
description: One line stating when this applies.
globs: tests/**, **/*_test.py, **/*.test.ts
alwaysApply: false
---
```

Comma-separated string form. Do not use a YAML list; keep one shape repo-wide.

### D - Agent-selected

```yaml
---
description: One line the agent can match against. Name the trigger explicitly.
alwaysApply: false
---
```

The description is the entire retrieval signal here. Write it as a trigger
condition, not a title. `"GMP audit procedure - use when auditing governance
compliance or a wave gate fails"` beats `"GMP audit"`.

### M - Manual

```yaml
---
alwaysApply: false
---
```

Only for `@`-mentioned templates. Rare. Prefer `commands/` instead.

## 4. Body rules

- Every file uses `.mdc`. A `.md` file in the rules directory is **ignored**
  by the rules system entirely.
- Hard cap 500 lines. Split anything larger into composable rules.
- **Reference files, do not copy them.** Use `@path/to/file.ts` so the rule
  points at canonical content instead of duplicating it. Copied content is
  the primary source of drift - the code changes, the rule does not.
- One H1 matching the filename slug. Sections use H2.
- No style guides. Use a linter. The agent already knows common conventions.
- No exhaustive command catalogs. The agent knows npm, git, pytest.
- No rare edge cases. Rules are for patterns you hit frequently.

## 5. Naming

`NN-kebab-case-slug.mdc` where `NN` is a **unique** two-digit prefix.

Note: Cursor does not order rules by filename. Precedence is
**Team Rules -> Project Rules -> User Rules**, with all applicable rules
merged. Your numeric prefixes are a human organizing tool, not an
enforcement mechanism - so stop encoding precedence in them and start
encoding it in rule bodies where conflicts actually get resolved.

Reserved bands:

| Band | Purpose |
|---|---|
| 00-09 | Kernel: global, execution discipline, output |
| 10-19 | Write authority: commit, push, PR, deploy |
| 20-29 | Environment and infrastructure |
| 30-39 | Memory and state |
| 40-49 | Language and framework |
| 50-59 | QA and testing |
| 60-69 | Security, secrets, anti-patterns |
| 70-79 | Tooling, MCP, context efficiency |
| 80-89 | GMP, governance wiring, graph architecture |
| 90-99 | Autonomy tiers, session bounds, incidents |

No two files share a prefix. Ever. CI enforces it.

## 6. Budgets

| Budget | Limit |
|---|---|
| Always-apply total | 12,288 bytes (~3,000 tokens per turn) |
| Any single always-apply rule | 4,096 bytes |
| Any rule, any tier | 500 lines |
| Rules missing `description` when `alwaysApply: false` and no globs | 0 unless intentionally manual |
| Files sharing a numeric prefix | 0 |
| `.md` files in `rules/` | 0 |

## 7. Anti-drift mechanisms

Drift happens four ways. Each gets a mechanism:

1. **Metadata drift** - fields nobody reads go stale. Fix: only native fields exist.
2. **Content drift** - copied code diverges from real code. Fix: `@file` references, never copies.
3. **Duplication drift** - six memory rules disagree. Fix: one rule per subsystem, precedence stated in the body.
4. **Budget drift** - always-apply creeps upward. Fix: CI gate that ratchets down, never up.
