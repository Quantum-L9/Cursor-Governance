# Cursor plans store

Machine-global Cursor plans for every workspace on this Mac.

`~/.cursor/plans` is a symlink here. Each consumer workspace still uses
`.cursor/plans` → `~/.cursor/plans`, so new Cursor plans land in this
directory and can be committed with the rest of Cursor-Governance.

Do not recreate `~/.cursor/plans` as a real directory. Heal with:

```bash
bash ops/scripts/setup_workspace_symlinks.sh
# or:
bash -c 'source ops/scripts/lib/workspace_kind.sh; source ops/scripts/lib/cursor_plans_store.sh; ensure_machine_cursor_plans_store'
```

The first successful heal writes `$HOME/.cursor/l9-plans-store` with the
absolute path of this directory so a later SessionStart in another clone
does not retarget the store.
