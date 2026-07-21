# memory-bank/ Git Policy

- **PlasticOS (`ib-odoo-19`):** `memory-bank/` is **git-tracked** — commit manually after sessionEnd T0 updates.
- **Other repos:** scaffold locally; track in git only when explicitly enabled in `group_registry.yaml`.
- **Never auto-commit** from hooks — hooks write files; human or explicit `make commit` only.
- **Scaffold rule:** `setup_workspace_symlinks.sh` copies template only when files missing — never overwrite existing.
