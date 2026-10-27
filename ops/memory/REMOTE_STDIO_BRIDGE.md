# Dormant Memory 3.0 stdio bridge

ADR-0053. The wrapper `run_memory_mcp.sh` keeps launching the pinned Memory
2.6.0 stdio server. It selects `ops.memory.remote_stdio_bridge` only when all
of the following are set on that process, outside any generated MCP file:

| Variable | Required value |
|---|---|
| `L9_MEMORY_REMOTE_STDIO` | `1` |
| `L9_MEMORY_REMOTE_URL` | `https://<host>/mcp`, or `http://` to a loopback host |
| `L9_MEMORY_REMOTE_SECRET_MAP` or `L9_MEMORY_REMOTE_KEY_NAME` | one agent's durable signing key |

`L9_MEMORY_REMOTE_KEY_NAME` is resolved through `ops.secrets.capability_bind.bind`.
This adapter does not create, rotate, or write that secret. A hosted
container's ephemeral key is refused. The HTTP request carries only
`Authorization: Bearer`, `L9-Identity-Assertion`, and
`L9-Identity-Assertion-HMAC`, minted again for each request.

Activation still requires a published Memory 3.0 artifact, server-side key
registration, and an operator decision to set the variables. None of those
happen by merging this change.
