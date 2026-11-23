# Versioned systemd units for the L9 host

These are the units that run on `igorbot-openclaw` (167.233.222.27), copied here
so the deployment is reviewable and reproducible instead of living only in
`/etc/systemd/system` on one machine.

| File | Installs to | Purpose |
|---|---|---|
| `l9-governance.service` | `/etc/systemd/system/` | Governance MCP, streamable HTTP on 127.0.0.1:8787 |
| `l9-governance.service.d/10-session-binding.conf` | `/etc/systemd/system/l9-governance.service.d/` | `ExecStartPre` session binding + `L9_AUTHORITY_ROOT` |
| `l9-cog.service` | `/etc/systemd/system/` | Cognitive runtime MCP on 127.0.0.1:8080 |
| `l9-cog.service.d/10-hosts.conf` | `/etc/systemd/system/l9-cog.service.d/` | DNS-rebinding allow-list for the cog transport |
| `l9-ops.service` | `/etc/systemd/system/` | Ops kernel MCP, stdio bridged by `mcp-proxy` on 127.0.0.1:7010 |
| `l9-splitwisely.service` | `/etc/systemd/system/` | SplitWisely.ai Node service on 127.0.0.1:3000 |
| `l9-session-binding.sh` | `/usr/local/bin/l9-session-binding` (mode 755) | Refresh authority checkout, compute binding, log the result |

## Why the binding is a unit precondition

Manus fires no session hook. `ExecStartPre=/usr/local/bin/l9-session-binding`
is the closest thing to one that the host cannot forget: every service start and
every reboot recomputes the Manus projection binding before the tool surface
opens.

The script is **non-fatal by default** — a dead control plane cannot explain
itself — and logs a single line:

```
l9-session-binding: status=BOUND authority=d0d2927 at 2026-11-23T18:46:01Z
```

Set `L9_BINDING_STRICT=1` in the drop-in to make a failed binding fail the unit.

## Install

```bash
install -m 755 l9-session-binding.sh /usr/local/bin/l9-session-binding
install -d /etc/systemd/system/l9-governance.service.d
install -m 644 l9-governance.service /etc/systemd/system/
install -m 644 l9-governance.service.d/10-session-binding.conf /etc/systemd/system/l9-governance.service.d/
systemctl daemon-reload
systemctl restart l9-governance
journalctl -u l9-governance -n 5 --no-pager
```

## Note on secrets

The governance token is **not** in this directory. It lives at
`/etc/l9/governance.token` (`root:l9`, mode 640) and is referenced by path in the
unit's `--auth-token-file` argument. Never commit it.
