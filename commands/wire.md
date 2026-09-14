---
name: wire
version: "2.0.0"
description: "Exhausted-repair fallback for workspace governance links after sessionStart auto-wire"
auto_chain: null
---

# /wire — governance workspace repair (fallback)

## WHAT IT DOES

Repairs consumer `.cursor-commands`, `.cursor/plans`, and the machine plugin
link by running the full workspace symlink setup, then re-checks wiring.

**SessionStart is the primary path.** Opening a governed workspace (or
`make start`) realpath-validates those links and heals them with
`L9_WIRE_LINKS_ONLY=1` plus one retry. Use `/wire` only when that auto-repair
is exhausted and the SessionStart report still says `wiring: FAIL`.

Do **not** use this slash for ordinary day-to-day stale absolute links.

## WHEN TO USE

- SessionStart / `make start` printed `exhausted auto-repair` / `wiring: FAIL`
- Links-only heal could not restore health (missing installed hooks copy)
- First-machine hooks were never installed — prefer `make cursor-install` first

## WHEN NOT TO USE

- Wrong-target or dangling `.cursor-commands` / `.cursor/plans` / plugin link
  on a machine that already has Cursor hooks — SessionStart heals those
- Inventing a second activation path or a new bootstrap installer
- Cursor SessionStart Claude cloud projection (forbidden)

## EXECUTION

```bash
REPO="${CURSOR_PROJECT_DIR:-$(pwd)}"
GC="$HOME/.cursor-governance"
bash "$GC/ops/scripts/wire_governance_workspace.sh" "$REPO"
make -C "$GC" start WS="$REPO"
```

`wire_governance_workspace.sh` runs `setup_workspace_symlinks.sh` then
`check_governance_wiring.sh`. Cursor auto-wire still SKIPs Claude projection.

## FIRST MACHINE

Hooks are not created by a clone alone. Install once:

```bash
make -C "$HOME/.cursor-governance" cursor-install WS="$(pwd)"
# or, after the chicken-egg clone exists:
make -C "$HOME/.cursor-governance" start WS="$(pwd)"
```

Then later opens auto-repair. `/wire` remains the escape hatch.
