# LLM skill + rules adapters

**Maintain one skills tree:** `skills/` (== `.cursor-commands/skills`).  
**Maintain one rules SSOT:** `rules/*.mdc` (== `.cursor-commands/rules`).  
**Claude (.md) peers mount:** `environment/generated/llm-rules/` (projected; never hand-edit).

## Law

1. Governance `skills/` and `rules/*.mdc` are the SSOTs.
2. Skill adapters get **per-skill symlinks** (never copies).
3. Claude Code `.claude/rules` is a **directory symlink** to
   `environment/generated/llm-rules/` (projected `.md`), **not** raw `rules/`.
4. Cursor still loads `rules/*.mdc` via the `l9-governance` plugin (do not recreate `~/.cursor/rules`).
5. `AUTONOMY_MANIFEST.yaml` + `ops/generated/skill-registry.json` decide which skills are linked.
6. Manifest/registry/projection updates auto-refresh adapter links through:
   - `ops/scripts/sync_generated_artifacts.py` (`rules/` → manifest → project → reconcile)
   - `ops/scripts/setup_workspace_symlinks.sh`
   - `ops/scripts/run_pr_gate.sh` local-activation check
   - `ops/scripts/reconcile_llm_rule_adapters.py`
   - `ops/scripts/reconcile_llm_skill_adapters.py`

## Commands

```bash
# After editing skills/ or AUTONOMY_MANIFEST.yaml:
python3 ops/scripts/sync_generated_artifacts.py --root "$HOME/.cursor-governance" \
  --workspace "/path/to/repo" --force

# After editing rules/*.mdc:
python3 ops/scripts/project_llm_rules.py --root "$HOME/.cursor-governance"
python3 ops/scripts/reconcile_llm_rule_adapters.py \
  --root "$HOME/.cursor-governance" --workspace "/path/to/repo"

# Or reconcile skill adapters only:
python3 ops/scripts/reconcile_llm_skill_adapters.py \
  --root "$HOME/.cursor-governance" --workspace "/path/to/repo"
```

## Adapter maps

- Skills: `SKILL_ADAPTER_ROOTS.yaml`
- Rules (.md peers): `LLM_RULE_ADAPTER_ROOTS.yaml`

Cursor uses the `l9-governance` local plugin (no `~/.cursor/skills` or `~/.cursor/rules`).
