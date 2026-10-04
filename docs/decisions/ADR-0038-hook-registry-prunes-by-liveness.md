# ADR-0038: The hook registry prunes by liveness, not by retirement list

## Status

Accepted

## Date

2026-10-04

## Context

`~/.cursor/hooks.json` and the `~/.cursor/hooks` link farm are machine-global
state. The reconcile in `ops/scripts/setup_workspace_symlinks.sh` only ever
*appended* to them: template entries this machine lacked were added, and
nothing was ever removed except through three hard-coded per-event sets
(`retired_session_end`, `retired_bse`, `retired_start`). Each of those sets was
added reactively, after the stale entry it names had already caused an
incident.

On 2026-10-04 the same gap produced a worse failure. `sacred-wip-transport.sh`
was registered in `preToolUse` on 2026-08-27 from the branch
`feat/sacred-wip-editor-transport`, which never merged. PR #677 (merged
2026-10-01) retired the WIP subsystem and deleted the script, but nothing
removed the two entries naming it. One of them carries `failClosed: true`, so
for five weeks every `Write`, `StrReplace`, `EditNotebook` and `ApplyPatch` in
*every* workspace on the machine was refused:

```
Hook "./hooks/sacred-wip-transport.sh" failed with exit code 127
```

Throughout, `check_governance_wiring.sh --machine` reported
`RESULT: PASS`. Its checks ask whether each *required* hook is present; none
asks whether an entry already in the registry can still execute. A hook that
blocks all editing machine-wide was therefore invisible to the only check that
inspects the registry.

A retirement list could not have prevented this. The hook was never on `main`,
so no retirement PR existed to add one, and the deletion that killed it
happened in an unrelated subsystem.

The obvious alternative — treat `ops/hooks/hooks.json.template` as
authoritative and delete anything it does not declare — is wrong. The registry
legitimately contains entries the template never names: the reconcile injects
canonical commands itself, and agents register their own, such as the live
`bash ./hooks/l4-gate-e2b6cf.sh` debug gate found during this investigation. A
template purge would delete working hooks.

## Decision

1. **Liveness is the general removal rule.** After the template merge and the
   per-event retirements, any entry whose `./hooks/` script does not resolve to
   an existing file is dropped, on every event, with a `PRUNED:` line. A
   missing script can only ever exit 127, so this cannot remove working
   behaviour; when the entry is `failClosed` it is actively holding the editor
   shut.
2. **The script is found by token, not by prefix.** The first `./hooks/` token
   in the command is resolved, so an interpreter prefix
   (`bash ./hooks/x.sh`) is matched. A command with no such token belongs to
   another tool and is never judged.
3. **Dangling governance links are swept.** Symlinks under `~/.cursor/hooks`
   that resolve nowhere and point into a governance clone are removed with a
   `REMOVED:` line. Real files, and dangling links owned by anything else, are
   left alone.
4. **Per-event retirement lists stay, and gain one.**
   `./hooks/sacred-wip-transport.sh` is retired explicitly for `preToolUse`,
   citing PR #677. The lists are not redundant with liveness: they also remove
   an entry whose script still *exists* but is superseded — including this one,
   which would come back to life the moment the unmerged branch is checked out
   in another clone.
5. **One owner answers the question.** The registry reconcile moves out of a
   heredoc into `ops/scripts/reconcile_hooks_registry.py`, which also serves
   `--check`. `check_governance_wiring.sh --machine` now fails when any
   registered command cannot run, escalating the message for `failClosed`
   entries, and gets that verdict from the same module that enforces it, so
   the check cannot drift from the reconcile.

## Consequences

A hook can now disappear from the machine without anyone remembering to write
a strip for it, which is the only property that would have caught this class.
The cost is that a template entry whose script fails to install is pruned
rather than left registered; that is the safer failure, and the wiring check
reports the missing required hook loudly in the same run.

`ops/scripts/tests/test_hooks_registry_prune.sh` (carried into pytest by
`tests/ops/scripts/test_hooks_registry_prune.py`) runs against a throwaway
`$HOME` and covers the reported fault, the interpreter-prefixed case no
retirement list can reach, foreign entries and links surviving untouched,
idempotence, and the per-event collapses this module inherited.

This ADR does not reinstate the WIP subsystem, which stays retired per
`WIP_SUBSYSTEM_RETIRED_V1`.
