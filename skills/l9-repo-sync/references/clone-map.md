<!-- L9_META
l9_schema: 1
parent: l9-repo-sync
tags: [sync, clone, ssot]
status: active
version: 1.3.0
updated: 2026-08-29
/L9_META -->

# Clone map

Bare `/ff` in this repo = **both** gitdirs **in parallel**. Flags split them
when you are in some other repo.

| Typed | Target |
|---|---|
| `/ff` (no flags) | This Cursor-Governance checkout **and** `$HOME/.cursor-governance`, parallel, when they differ |
| `/ff --clone` | Working copy only (`pwd` if identity, else `$HOME/Cursor-Governance`, else `CURSOR_GOVERNANCE_CLONE`) |
| `/ff --ssot` | `$HOME/.cursor-governance` only |

Same realpath (you are already on the live SSOT, no flags): one clone.
A consumer repo, no flags: SSOT only (not a pair with the consumer tree).

Agents run `ff.sh` **once** with the user's flags. Do not stop. Do not name
`ssot` vs `workspace`. `GLOBAL_COMMANDS` is not `activate_fresh`.
