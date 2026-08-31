<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [rules, inventory, governance]
status: active
/L9_META -->

# Rules Inventory (/rules)

List all `.cursor/rules/*.mdc` with alwaysApply status.

```bash
ls .cursor/rules/*.mdc | wc -l
grep -l "alwaysApply: true" .cursor/rules/*.mdc
```

Report: total, always-applied, context-only, rules missing frontmatter.

For global L9 rules also check `.cursor-commands/rules/` when maintaining governance SSOT.
