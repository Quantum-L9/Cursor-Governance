<!-- L9_META
l9_schema: 1
parent: l9-incident-response
layer: reference
role: diagnostic_playbook
tags: [incident, network, dns, tls, proxy, diagnostics]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-06-06
/L9_META -->

# Network troubleshooting (developer diagnostics)

Use for **developer network failures** — not production incident mitigation. Read-only by default.

## Safety boundaries

- Prefer read-only diagnostics; ask before probing unrelated external services.
- Do not print proxy URLs, credentials, tokens, or raw config values in shared output.
- Do not dump npm/pip/git/docker/OS proxy or certificate store configs.
- Do not disable or bypass TLS verification.
- Do not change OS networking, DNS, proxy, VPN, or trust-store settings without explicit user approval.

## Workflow

1. **Collect** — exact error, command, target host/URL/port, OS, proxy/VPN context.
2. **Classify** — match symptom to category (table below).
3. **Diagnose** — smallest read-only checks scoped to the failing target.
4. **Explain** — interpret output before suggesting fixes.
5. **Advise** — present remediation as choices; wait for approval before changing state.
6. **Verify** — re-run the original failing command.

## Error classification

| Pattern | Likely cause |
|---------|----------------|
| `ECONNREFUSED`, `Connection refused` | Service/port not listening |
| `ECONNRESET`, `socket hang up` | Connection dropped (target, proxy, firewall) |
| `ETIMEDOUT`, `timed out` | Routing, firewall, proxy, availability |
| `ENOTFOUND`, `getaddrinfo` | DNS / hostname |
| `ERR_PROXY_*`, HTTP `407` | Proxy config or auth |
| `ERR_CERT_*`, `CERT_HAS_EXPIRED` | TLS / trust |
| HTTP `403` | Auth, allowlist, CORS, policy |
| HTTP `502`/`503`/`504` | Upstream / gateway instability |
| `npm ERR! network`, `pip` timeout | Registry / proxy / DNS path |
| `fatal: unable to access` (git) | Remote, proxy, DNS, TLS path |

## Safe checks (explain before running)

```bash
# Connectivity (macOS/Linux)
curl -v telnet://<host>:<port> --connect-timeout 5

# DNS
dig <host>

# HTTP
curl -vvv -o /dev/null -w "HTTP %{http_code}\n" https://<host>/<path>

# TLS
openssl s_client -connect <host>:<port> -servername <host> </dev/null
```

Package-registry probes only when the failed operation already targeted that registry, or after user approves the probe target.
