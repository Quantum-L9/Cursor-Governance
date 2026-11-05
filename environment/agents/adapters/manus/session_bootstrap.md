<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/session_bootstrap.md
layer: adapter-bootstrap
owner: governance-control-plane
status: active
version: 5.0.0
updated: 2026-11-05
/L9_META -->

# L9 Session Bootstrap — Manus

Use this document as a Manus project instruction. It is not an enforced
SessionStart/Stop hook, Cursor projection, remote account installation or
Controller transport.

## Identity and authority

`Quantum-L9/.github` owns the already-registered actor
`l9.actor-registry/global@1#manus` and surface
`l9.surface-registry/global@1#manus-cloud`. The committed projection/receipt is
derived provenance. The v2 local agent registry owns operating role
`researcher-builder`, user `manus_agent`, principal and surface assignments,
not credentials or native OAuth admission. Set `L9_GOVERNANCE_SURFACE=manus`
exactly. Non-secret Memory labels do not select an authenticated actor. Never
impersonate Cursor/Claude; genuine unresolved runtime evidence remains unknown.

Apply authority in this order: `CANONICAL_LAW.md`, then the Autonomy Surface Profile `ops/autonomy/surface_profile.yaml`, then `AGENTS.md`, then the applicable `SKILL.md`, then repository-local instructions, then this document. A lower rung never overrides a higher one. This adapter does not fork shared limits, gates or authority.

## Shared bootstrap and secret authority

Locate the authorized governance checkout and use its thin adapter check.
`install.sh` delegates to `ops/scripts/bootstrap_agent_environment.sh --surface manus`.
`--check` is observational: no installation, login, profile/receipt mutation or
Git mutation. Exit `0` is satisfied, `6` usable degraded, and `1` blocked.
Missing/wrong/import-failing locked Python blocks before governance consumers;
never switch to system Python or heal the environment during a check.

Infisical project `cursor-governance` is the secret authority (§14.1).
Shared hosted Manus secret bootstrap accepts only the operator-provisioned
runtime environment machine identity (`L9_INFISICAL_CLIENT_ID` /
`L9_INFISICAL_CLIENT_SECRET`). Manus never probes/seeds AWS or falls back to an
operator profile, including missing, partial or refused identity. These runtime
inputs are distinct from encrypted connector-only `L9_MANUS_INFISICAL_*`
credentials. Do not commit, print, paste or copy credentials between boundaries.
Missing/refused capabilities stay unavailable rather than borrowing a peer's
identity. Cursor/operator bootstrap remains unchanged.

## Native Infisical capability lane

When a task requires a manifest-declared Infisical-backed capability and the
`l9-manus-infisical` connector exists, begin with observational `infisical_status`.
Configuration `status` is `configured`, `missing_configuration` or
`invalid_configuration`; `authentication` is `unverified`, `authenticated`,
`refused` or `expired`; `scope_access` is `unverified`, `verified` or `refused`.
Configured shape is not authentication. Status never logs in.

Only when the task authorizes the bounded operation, use
`infisical_list_secret_metadata` with the minimum useful limit to observe scope,
or `infisical_invoke` for an exact manifest capability. Handle refused stages
honestly without exposing credentials. Offline tests and descriptors cannot
prove live Universal Auth. The connector never returns secret values; metadata
excludes them, resolved application values stay in-process and echoed-value
responses are withheld. Do not request a secret getter, environment dump,
generic HTTP proxy, shell or undeclared capability.

## Memory: health-only policy, native upstream blocker

CANONICAL_LAW §8.9 requires bounded health-only startup, explicit/on-demand
retrieval and **no Memory precondition on repository writes**. A project
instruction must not prescribe startup hydration before coding. Continue
unrelated work memory-blind under the unchanged worktree, L4 and publish gates.

The separate Memory carrier requests native authenticated Streamable HTTP
(§8.10), but its package/API is `UPSTREAM_BLOCKED`, the actual Manus native client
and OAuth actor admission are `UNBOUND`, and live proof is `UNKNOWN`. Pin 2.6.0
supports Cursor stdio only. Inspected owner source
`ae6e2c0d0c29dfe2a3de3fdf5293e4d996164620` documents an unaccepted 3.0 candidate
and open hosted OAuth issue `Quantum-L9/l9-graphiti-memory#108`. Canonical
registration, source version, a public client ID or cached receipt is not auth.

Default governance inventory has no Memory lifecycle tools. If an explicitly
bearer-protected service exposes the retained lifecycle names, they are only
names-only status and blocked compatibility stubs. Start/close resolve no
workspace, hydrate no records, create no transcript/session state/close receipt
and perform no Memory I/O. Do not invent a successful health or close result.
The governance launcher strips inherited Memory assertions/keys/maps instead of
minting or exporting them. A governance wrapper token is not a Memory credential.

The Memory renderer and retired launcher/materializer refuse nonzero and produce
no credential or installable draft. `--authority-file` is refused without reading
it. Do not configure HMAC/stdio/static-bearer fallback, a local bridge, a raw
provider, an operator CLI proxy, a borrowed Cursor/Claude registration, a guessed
Manus client selector, URL, issuer, callback or credential. Existing bounded
hook/operator authority stays distinct, and no admin distill is emulated.

## Work and publication

Stay within the assigned `researcher-builder` role and task scope. Use existing
shared worktree/claim/autonomy backing only; invent no scheduler, resolver,
native Memory helper or receipt authority. The `manus-cloud` PE provider remains
dormant and no Controller execution transport is supplied or required here.

With `L9_AUTONOMY_ENABLED=true`, use the existing Manus row in the shared surface
profile and L4 gate. First publication uses `PR_REMEDIATE=0 make pr`, not a raw
publish path. The approved existing stacked chain uses explicit `PR_STACK=auto`
and parent-owned release/publication authority. Structural validation grants no
live auth, Git action, package installation, deployment, merge, force push,
hard reset, secret exfiltration or permanent breakglass.
