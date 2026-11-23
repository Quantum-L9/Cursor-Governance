<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 6.1.0
updated: 2026-11-21
/L9_META -->

# Manus adapter — thin governance and capability binding

This adapter consumes the shared L9 owners. It is not a Cursor projection,
Memory client implementation, scheduler, secret resolver, or identity authority.
Its durable project instruction is [`session_bootstrap.md`](session_bootstrap.md);
that instruction is not an enforced Manus SessionStart/Stop hook.

## Authority and identity

`Quantum-L9/.github` owns the existing actor
`l9.actor-registry/global@1#manus` and surface
`l9.surface-registry/global@1#manus-cloud`. The committed canonical identity
projection and receipt are derived provenance. The v2
`environment/agents/agent_registry.yaml` owns operating role, user, principal
and surface assignments, not canonical names, credentials or OAuth admission.

The validator delegates the complete existing canonical assurance checker,
including governing binding, projection coordinates, receipt-byte integrity and
all operating bindings. It additionally requires the exact active Manus
actor/surface assignment. Missing, tampered or non-current projections fail.
No actor or surface is inferred from a public client ID. Genuine unrecognized
runtime surface evidence stays unknown in the shared resolver.

## Shared bootstrap

`install.sh` delegates to `ops/scripts/bootstrap_agent_environment.sh --surface manus`
after validating the supplied Git workspace. `--check` is observational, not an
installation or authentication attempt. Shared outcomes are `0` (satisfied),
`6` (usable but degraded) and `1` (blocked); missing/wrong/import-failing locked
Python blocks before governance consumers. Use the checkout's `.venv/bin/python`,
not system Python, for governance validation. The installer does not configure
a Manus account, install a project instruction remotely or heal a check run.

Because Manus exposes no SessionStart hook, the installer is the session start.
Before the bootstrap it binds the two machine-level facts later gates assume,
through `session_env.sh`: `$HOME/.cursor-governance` (the SSOT path
`resolve_governance_paths.sh` accepts, provisioned through the existing
`governance_sync.sh` clone-if-missing owner rather than a second implementation
here) and `L9_GOVERNANCE_SURFACE=manus` (unset makes
`is_cursor_host_surface()` fail closed to Cursor, and the
`pass_filenames: false` `symlinks-check` hook then fails every `make pr` on a
clean tree). It then provisions the governance-managed authority checkout the
default projection binding verifies — the step Cursor's
`session_start_bootstrap.sh` owns for its surface. `--check` reports all three
without mutating them.

Hosted Manus shared secret bootstrap consumes only sanctioned environment
machine identity (`L9_INFISICAL_CLIENT_ID` / `L9_INFISICAL_CLIENT_SECRET`). It
never borrows an operator profile or probes/seeds AWS. Cursor/operator bootstrap
remains separately owned and unchanged. Provisioning is operator-owned and
secret values never belong in examples, repositories, receipts or chat.

## Governance MCP boundary

The governance MCP uses Streamable HTTP at `/mcp`, with `/health` reporting only
that governance service's health. Default discovery lists six governance tools:
status, validate, bootstrap, read, search and skill inventory. Validation,
workspace Git status and bootstrap invocation retain bearer guards. Apply also
requires `--allow-bootstrap-apply`. Read/search paths and output are bounded;
there is no shell, arbitrary file access or repository-write tool.

`governance_status` consumes the structured validation report. `validated`
means structural/canonical assurance only, not live readiness. Report layers
remain separate: structural, canonical identity, native binding and live proof.
A governance bearer token is not a Memory or Infisical credential.

## Memory 3.0: blocked, not bridged

CANONICAL_LAW §8.10 requires native authenticated Streamable HTTP. The secret-free
[`memory-mcp-connector.json`](memory-mcp-connector.json) requests a Manus native
client, but is deliberately non-installable:

| Layer | Current posture |
|---|---|
| Owner package/native API | `UPSTREAM_BLOCKED`; examined consumer pin 2.6.0 supports Cursor stdio only |
| Requested Manus native client | Registered in Auth0 as `manus-native` (public PKCE, `https://manus.im/api/webhook/mcp/callback`); the carrier stays `UNBOUND` until a live PKCE receipt |
| OAuth canonical actor admission | `UNBOUND` |
| Live authentication and scope proof | `UNKNOWN` |

Owner source `ae6e2c0d0c29dfe2a3de3fdf5293e4d996164620` documents an unaccepted
3.0 release candidate and hosted OAuth issue `Quantum-L9/l9-graphiti-memory#108`.
Source version, reachable routing, a local assertion or canonical registration
is not accepted package, deployment or client admission evidence.

The historical renderer API/flags refuse nonzero, emit no installable draft and
never overwrite output. `--authority-file` is retired and is refused without
reading it. `serve_memory_mcp.sh` deterministically refuses the retired
stdio/HMAC launch before minting, materializing, creating temporary files or
starting a server, even with stale inherited authority. The materializer's CLI
and production API also refuse without reading stdin or producing credentials;
its pure grant inspection exists solely for negative canonical assurance.

The governance launcher strips inherited Memory assertion/key/map fields and
never mints/exports Memory authority. Default inventory remains governance-only.
`--enable-memory-lifecycle` still requires a bearer-token file, but exposes only
names-only status and blocked start/close compatibility stubs. These stubs do
not resolve workspaces, invoke the operator CLI, hydrate, close, create a
transcript/receipt or emulate admin distill.

Startup policy is **health-only**, retrieval is **explicit/on-demand**, and
Memory is **not a repository-write precondition** (§8.9). Continue unrelated
coding memory-blind under the unchanged worktree, L4 and publication gates.
The bounded hook/operator lanes remain distinct; they are not a substitute
agent MCP transport. No stdio/HMAC/static-bearer/provider/HTTP bridge fallback,
Cursor selector relabeling or guessed Manus client configuration is permitted.

## Native Infisical capability lane

The separate `l9-manus-infisical` local stdio connector is not Memory transport.
It uses connector-only `L9_MANUS_INFISICAL_*` Universal Auth configuration,
distinct from shared bootstrap `L9_INFISICAL_*` runtime identity. Connector
credentials stay in the encrypted connector environment, not project/session
instructions or environment examples. Application values remain in-process.

The fixed initial capability `github.get_repository` resolves only `GITHUB_TOKEN`
and performs an allowlisted GitHub HTTPS GET, returning curated metadata.
Metadata listing sends `viewSecretValue=false`; responses containing resolved
values are withheld. No generic HTTP, secret-return, environment dump or shell
capability is exposed.

### The capability manifest is derived, never written

`infisical_capabilities.json` is generated from `ops/secrets/capabilities.yaml`
by `render_infisical_capabilities.py` (mapping logic in `capability_source.py`).
Do not edit it: `make manus-adapter-check` runs the renderer with `--check` and
fails the build when the committed file is stale, and the validator independently
compares the recorded `generated.source_sha256` against the registry bytes. A
registry edit therefore forces a reviewed re-render instead of silent drift.

The registry models one capability as *many* methods over *many* paths; this
adapter models one method over one path, pinned to `api.github.com`, `GET`, and
`GITHUB_TOKEN`, behind a named bounded response filter. Widening the adapter to
the registry's cardinality was rejected — rendering `github.mcp` faithfully
would expose 21 endpoints (including `/search/code`, `/user/repos` and `/gists`)
behind a `passthrough` sanitizer, turning a bounded single-object read into a
general GitHub proxy with a live credential behind it.

So each adapter capability is an explicit projection of exactly one registry
endpoint, and everything else is reported rather than dropped. The manifest's
`exclusions` array names every registry entry that is not exposed, with a
machine-derived reason and the exact methods and paths withheld; `narrowings`
records where the adapter is deliberately stricter than the registry (verb,
path count, sanitizer, parameter patterns). A projection that no longer matches
the registry raises instead of shrinking the surface. `infisical_status` reports
the same exclusion list, so an operator can tell "not sanctioned for this
surface" apart from "does not exist".

`infisical_status` distinguishes configuration from observations:

- `status`: `configured` / `missing_configuration` / `invalid_configuration`.
- `authentication`: `unverified` / `authenticated` / `refused` / `expired`.
- `scope_access`: `unverified` / `verified` / `refused`.

Configured shape is not live authentication. Status performs no login; an
explicit, task-authorized bounded metadata/capability request can establish an
observation. Offline tests are not live Universal Auth proof. Errors identify
the refused stage without exposing credentials; token expiry is bounded by the
actual positive finite lifetime, not an invented fallback.

## Verification and operating limits

```bash
.venv/bin/python -B environment/agents/adapters/manus/validate_manus_adapter.py --repo-root . --json
.venv/bin/python -B environment/agents/adapters/manus/render_infisical_capabilities.py --check
.venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests
.venv/bin/python -B tools/assurance/check_canonical_identity_projection.py
```

These are offline/source checks, not connector creation, secret retrieval or
native Memory admission. Setup details are in [`setup.md`](setup.md).

The `manus-cloud` Program Execution provider remains dormant; this adapter
supplies no Controller transport and surviving work does not require PE.
Use the existing shared autonomy/worktree/L4 authority. First publication uses
`PR_REMEDIATE=0 make pr`; the approved existing stack uses explicit
`PR_STACK=auto` and parent-owned release/publication authority. No merge,
Git mutation, package installation, deployment or secret provisioning is
conferred by adapter structural PASS.
