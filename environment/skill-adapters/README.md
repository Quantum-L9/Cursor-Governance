# LLM skill + rules adapters

**Maintain one skills tree:** `skills/` (== `.cursor-commands/skills`).  
**Maintain one rules tree:** `rules/` (== `.cursor-commands/rules`).

## Law

1. Governance `skills/` and `rules/` are the SSOTs.
2. Skill adapters get **per-skill symlinks** (never copies).
3. Claude Code `.claude/rules` is a **directory symlink** to governance `rules/`.
4. Cursor still loads `rules/` via the `l9-governance` plugin (do not recreate `~/.cursor/rules`).
5. `AUTONOMY_MANIFEST.yaml` + generated `skill-registry.json` decide which skills are linked.
6. Manifest/registry updates auto-refresh adapter links through:
   - `ops/scripts/sync_generated_artifacts.py` (skills/ changes)
   - `ops/scripts/setup_workspace_symlinks.sh`
   - `ops/scripts/run_pr_gate.sh` local-activation check
   - `ops/scripts/reconcile_claude_rules.py`

## Commands

```bash
# After editing skills/ or AUTONOMY_MANIFEST.yaml:
python3 ops/scripts/sync_generated_artifacts.py --root "$HOME/.cursor-governance" \
  --workspace "/path/to/repo" --force

# Or reconcile adapters only:
python3 ops/scripts/reconcile_llm_skill_adapters.py \
  --root "$HOME/.cursor-governance" --workspace "/path/to/repo"
```

## Adapter map

See `SKILL_ADAPTER_ROOTS.yaml`. Cursor uses the `l9-governance` local plugin (no `~/.cursor/skills`).
