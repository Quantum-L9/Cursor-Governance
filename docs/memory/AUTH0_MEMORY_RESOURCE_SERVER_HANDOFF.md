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

## Amendment — 2026-11-21: the Manus client is registered

The issuer and the Manus registration are bound. The Cursor and Claude client
ids are not.

| Fact | Value |
|---|---|
| Issuer | `https://quantum-ai-partners.us.auth0.com/` |
| Registration | `manus-native`, public, `token_endpoint_auth_method: none`, PKCE `S256`, `authorization_code` + `refresh_token` |
| Callback | `https://manus.im/api/webhook/mcp/callback` |
| Client id | `lIY0hERvmh34BZK0veLKtEtZm4qf9Beb` |
| Registration mode | Pre-registered. The tenant publishes no `registration_endpoint`, so dynamic registration is unavailable. |

The issuer was read from the live protected-resource document, not typed from
memory: `https://memory.quantumaipartners.com/.well-known/oauth-protected-resource/mcp`
names that authorization server and this resource identifier.

`resource_parameter_profile` is `compatibility` on the tenant. That setting is
load-bearing: MCP clients send the RFC 8707 `resource` parameter rather than
`audience`, and on the default profile Auth0 ignores it, so the access token
carries no Memory audience and every call is refused as `invalid_token` after a
successful login.

Two tenant properties were not visible on the happy path and are recorded
because each one refuses a correct-looking registration:

- **The app type is `spa`, not `native`.** Auth0 answers a native client's
  hosted `https` callback with `400 invalid OAuth callback` even when the URI is
  in the allowlist, because a native callback is expected to be a custom scheme
  or loopback. `spa` keeps every public-client property (`token_endpoint_auth_method:
  none`, PKCE `S256`, `authorization_code` + `refresh_token`) and accepts the
  hosted callback.
- **The client grant carries `subject_type: "user"`.** A grant created without
  that field lands in the machine-to-machine lane (`client`), and `/authorize`
  then answers `Client "…" is not authorized to access resource server "…"` —
  after the callback is already accepted, which makes it read as an audience
  problem. `UpdateClientGrantRequestContent` has no `subject_type`, so the fix
  is a second grant, not a patch. Both lanes coexist on this client; Memory
  refuses user-less tokens, so the `client` grant confers nothing here.

Verified against the live tenant on 2026-11-21, with `prompt=none` and no
session: `/authorize` returns `302` to the callback with `error=login_required`
for both `resource` and `audience`; a nonexistent resource returns
`Service not found`; an unlisted callback returns `403 Callback URL mismatch`.

One gate remains, and it is not a registration:

1. **A live PKCE receipt.** No client has one. The Manus carrier therefore stays
   `UNBOUND` and non-installable in `memory-mcp-connector.json`.

Memory-side authorization is a separate operator input, not a tenant change:
Memory reads `L9_MEMORY_OAUTH_GRANTS_JSON`, never the token's `scope` claim, so
a verified subject absent from that map authenticates and then resolves to no
namespace. That entry is an Infisical `prod` change followed by a redeploy.

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
