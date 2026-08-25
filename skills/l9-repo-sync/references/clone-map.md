<!-- L9_META
l9_schema: 1
parent: l9-repo-sync
tags: [sync, clone, ssot]
status: active
version: 1.2.0
updated: 2026-08-22
/L9_META -->

# Clone map (print every time)

| Alias | Path | Script default without env |
|---|---|---|
| `ssot` | `$HOME/.cursor-governance` | Yes (`CURSOR_GOVERNANCE_DIR` default) |
| `workspace` | Cursor folder gitdir (this checkout) | No — must set `CURSOR_GOVERNANCE_DIR` |

`CURSOR_GOVERNANCE_DIR` selects the **ff clone**.
`GLOBAL_COMMANDS` / `$GOV_ROOT` after `resolve_governance_paths.sh` is the
governance content root (same path on the live SSOT). They are not a license
to `activate_fresh`.

If the user says “this repo” and `ssot` and `workspace` are different gitdirs
(`samefile` false): diagnose both, **stop until they name one**.
