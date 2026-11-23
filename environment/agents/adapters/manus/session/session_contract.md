# Manus session contract — what fires, and what cannot

## The platform fact

Manus fires **no session hook**. There is no boot-script panel, no equivalent of
Cursor's `SessionStart`, and `AGENTS.md` is not auto-read in the ephemeral
sandbox. `~/.bashrc` is regenerated at session start, so anything appended there
disappears silently. Any design that assumes a host callback is wrong.

## The three surfaces that do exist

| Surface | Fires when | Guarantee |
|---|---|---|
| `l9-session-binding` as `ExecStartPre` on `l9-governance.service` | every service start, every reboot | The **box** is bound before the tool surface opens. Failure is logged; the unit still starts unless `L9_BINDING_STRICT=1`. |
| `governance_session_start` MCP tool | when a session calls it first | The **session** holds a receipt with timestamp, binding status and authority SHA. |
| `make manus-session-start` | operator or CI | Same code path as the tool, for a terminal or pipeline. |

## Receipt

```json
{
  "schema": "l9.manus.session-receipt.v1",
  "host": "manus",
  "issued_at": "2026-11-23T18:46:01Z",
  "binding_status": "BOUND",
  "bound": true,
  "authority_sha": "d0d2927",
  "steps": [
    {"step": "authority_refresh", "status": "completed", "exit_code": 0},
    {"step": "projection_binding", "status": "BOUND", "reason": null}
  ]
}
```

The receipt is idempotent: a second call issues a new timestamp with the same
binding facts. It never mutates the checkout.

## Posture rules

1. **Fail-open, report loud.** A failed binding does not kill the service by
   default, because a dead control plane cannot explain itself. The status is in
   the journal and in the receipt. Set `L9_BINDING_STRICT=1` to make it fatal.
2. **Cite only what is bound.** When `bound` is false, no operating-plane
   semantics may be cited. The binding line says so in its own words.
3. **Never infer a hook.** If a future Manus release adds a session hook, this
   contract is where it gets adopted — not by assuming one exists.

## Known limit

The `ExecStartPre` binding proves the *host* is bound at boot. It cannot prove
the *session* is bound, because the box cannot see Manus sessions. Only the
receipt does that, which is why the tool exists and why the first call of a
session should be `governance_session_start`.
