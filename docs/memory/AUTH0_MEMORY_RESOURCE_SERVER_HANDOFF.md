# Memory 3.0 Auth0 resource-server handoff

Cursor-Governance owns the consumer requirements in
`ops/config/memory-auth0-onboarding.yaml`. Quantum-L9/l9-graphiti-memory owns
the resource server. This repository did not change Memory, Auth0, or `.github`.

## Consumer contract already fixed here

- Auth0 is the only authorization server. No second authorization server, OAuth
  proxy, static bearer, HMAC, stdio substitute, or SQLite fallback.
- PKCE is required. Method `S256`. `plain` is forbidden. Both approved clients
  are public (`token_endpoint_auth_method: none`). Client secrets are forbidden.
- Scopes the client requests, exactly: `memory.read`, `memory.write`.
- Cursor native redirect URIs, exactly:
  - `https://www.cursor.com/agents/mcp/oauth/callback`
  - `http://localhost:8787/callback`
  - `cursor://anysphere.cursor-mcp/oauth/callback`
- Claude account connector redirect URI, exactly:
  `https://claude.ai/api/mcp/auth_callback`
- The Claude connector is account-managed. It is not a project `.mcp.json`
  entry and it does not receive a hosted-session credential.
- A stdio-only `l9-memory client cursor` entry is `UPSTREAM_BLOCKED`. This
  repo does not install that entry as a fallback.
- OAuth `sub` and client id do not establish actor, surface, release, or
  runtime identity.

## Resource identifier

Memory published `https://memory.quantumaipartners.com/mcp` as
`MEMORY_RESOURCE_IDENTIFIER` in `src/l9_graphite_memory/version.py` and in
ADR-100 (Quantum-L9/l9-graphiti-memory#106). This consumer records that
string. The host alone is not the audience. The Graphiti route
`https://memory.quantumaipartners.com/graphiti/mcp` is not this identifier.

## Still unbound (do not treat as passed)

`issuer.domain`, `clients.cursor-native.client_id`, and
`clients.claude-account-connector.client_id` are null. No tenant was created
and no client was registered by this change. ADR-100 does not contain a live
PKCE receipt. The installed package entry is still the stdio command.

## Memory-owned work that unblocks installation

1. Serve MCP Streamable HTTP on `https://memory.quantumaipartners.com/mcp`
   for protocol versions `2025-11-25` and `2025-06-18`. Verify Auth0-issued
   JWTs (signature, issuer, audience, expiry). The access-token `aud` claim
   must equal that identifier exactly. Enforce `memory.read` and
   `memory.write`. Keep namespace authorization and canonical storage inside
   Memory.
2. Pre-register two public PKCE clients with the redirect URIs above. Return
   the issuer domain and the client ids to the consumer onboarding file. Do
   not enable a client secret, a static bearer, or dynamic registration as a
   substitute. A live PKCE receipt is still required.
3. Change `l9_graphite_memory.client_config.cursor.managed_server_entry` so the
   Cursor entry is native Streamable HTTP: `url` equal to the resource
   identifier, `auth.CLIENT_ID` equal to the cursor-native client id,
   `auth.scopes` exactly `memory.read` and `memory.write`, and no
   `CLIENT_SECRET`, `env`, `headers`, or stdio command.
4. Hosted proof still required after that package exists: Cursor desktop
   authorization, Claude account-connector authorization, and mobile. Those
   runs are blocked until the tenant, resource server, and package entry exist.
   A local onboarding fixture is not that proof.

Until the issuer domain and both public client ids are registered, a native
entry whose URL equals the published identifier returns `unbound_client`, and
returns `unbound_issuer` once the client id is present and the domain is not.
The current package entry is stdio, so a real install returns
`upstream_blocked` before those checks. A package entry that fails
authorization is removed from the machine config. Matching the inspector
does not keep it.
