# Moved — do not edit

Claude `.claude/rules` is a directory symlink to the **generated** mount:

`environment/generated/llm-rules/`

Skill routing for Claude is projected from `rules/23-l9-skill-routing.mdc` as
`l9-skill-routing.md` in that generated tree.

Author only `rules/*.mdc`. Regenerate with:

```bash
python3 ops/scripts/project_llm_rules.py --root "$HOME/.cursor-governance"
python3 ops/scripts/reconcile_llm_rule_adapters.py --root "$HOME/.cursor-governance"
```
