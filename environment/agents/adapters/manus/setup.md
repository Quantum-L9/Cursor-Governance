<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/manus/setup.md
layer: adapter
owner: governance-control-plane
status: active
version: 5.0.0
updated: 2026-11-05
/L9_META -->

# Manus adapter setup

This is a thin binding to existing shared bootstrap, canonical identity,
secret authority and autonomy owners. Setup does not activate Program Execution,
create a host hook or invent a Memory client. Canonical names are owned by
`Quantum-L9/.github`; the local v2 agent registry contains operating bindings.

## Project instruction and observational check

Make the authorized governance checkout available in the Manus workspace.
Copy only the non-secret assignments from
[`environment.env.example`](environment.env.example) into the project/session
environment and use [`session_bootstrap.md`](session_bootstrap.md) as the project
instruction. Do not set a literal hosted `L9_GOVERNANCE_DIR`: such fields do not
expand `$HOME`. A project instruction is not proof of an enforced startup hook.

From an existing governed Git workspace, use the thin installer in check mode:

```bash
bash environment/agents/adapters/manus/install.sh \
  --governance /absolute/authorized/governance-checkout \
  --workspace /absolute/authorized/git-workspace --check
```

The shared owner makes `--check` observational. It performs no installation,
secret login/profile mutation, receipt mutation or Git mutation. Exit `0` means
satisfied source/environment checks, `6` means usable degraded, and `1` means
blocked. A missing, wrong-version or import-failing locked interpreter is a
blocker, never permission to use system Python. Explicit apply is a separate
authorized action using the existing shared owner, not an adapter workaround.
A cached/source readiness receipt is not live authentication proof.

## Governance MCP (separate authentication)

An authorized operator can use `serve_mcp.sh` with the locked interpreter to
serve the existing governance contract. `/mcp` is its Streamable HTTP endpoint;
`/health` proves only governance service reachability. Use only the actual
operator-owned HTTPS endpoint with `render_mcp_connector.py`; never manufacture
an endpoint or put credentials in a URL.

The default inventory contains six governance names and no Memory tools.
`governance_validate`, optional workspace status and bootstrap invocation retain
bearer protection; apply additionally requires `--allow-bootstrap-apply`.
Governance reads/search remain bounded and never expose a shell or general
repository write. A wrapper bearer credential stays outside the repository,
project instructions and task text and is not a Memory credential.

For compatibility, `--enable-memory-lifecycle` requires `--auth-token-file`.
It adds names-only status and blocked start/close stubs, not live capabilities.
The launcher strips all inherited `L9_MEMORY_*` values and
`L9_MANUS_MEMORY_AUTHORITY_JSON`; it does not source a mint/export helper.
Neither missing nor stale authority triggers a local operator fallback.

## Memory 3.0 remains non-installable

The carrier requests **native authenticated Streamable HTTP**, but package/API
support is `UPSTREAM_BLOCKED`, the requested Manus native client and OAuth actor
admission are `UNBOUND`, and live proof is `UNKNOWN`. Installed pin 2.6.0's
Cursor stdio entry is not a Manus native client. Owner source
`ae6e2c0d0c29dfe2a3de3fdf5293e4d996164620` documents the unaccepted 3.0 candidate
and open hosted OAuth implementation/admission issue
`Quantum-L9/l9-graphiti-memory#108`.

Do not create a Memory connector from the carrier. The renderer's old flags and
API refuse nonzero without writing or overwriting drafts; `--authority-file`
refuses without reading the file. The legacy launcher and credential
materializer refuse before server/helper execution, stdin reads or output.
No URL, issuer, client ID, callback or credential has been supplied by this
adapter. Do not guess `client_config.manus`, relabel Cursor selectors, borrow a
peer's registration or build a stdio/HMAC/static-bearer/HTTP/provider bridge.

Startup is bounded **health-only**. Retrieval is explicit/on-demand, never a
repository-write precondition. Current compatibility stubs perform no health
request or Memory I/O because no admitted owner Manus API exists. They resolve
no workspace, write no session state or transcript, and produce no close
receipt. Continue unrelated coding memory-blind. The existing operator CLI and
bounded hook envelopes are separate authorities, not agent MCP substitutes;
this adapter does not emulate admin distill.

## Two Infisical boundaries

Infisical project `cursor-governance` is the secret store (§14.1).
Shared hosted Manus bootstrap takes sanctioned environment machine identity
`L9_INFISICAL_CLIENT_ID` / `L9_INFISICAL_CLIENT_SECRET` only. These are
operator-provisioned runtime inputs, never committed examples or chat values.
Manus has no AWS probe/seed and no operator machine-profile fallback, even when
identity is missing, partial or refused. Cursor/operator behavior is unchanged.

The independent `l9-manus-infisical` connector uses dedicated connector-only
`L9_MANUS_INFISICAL_*` configuration. An authorized operator can use
`render_infisical_mcp_connector.py --help` with a private client-secret file and
actual approved client/project coordinates to create a temporary mode-0600
draft for the encrypted Custom MCP environment. That lane's credentials are
not shared bootstrap inputs and never enter project/session instructions.
Delete transient drafts after the authorized configuration step; no setup or
credential provisioning is performed merely by reading this document.

`infisical_status` is observational. Its configuration `status` is `configured`,
`missing_configuration` or `invalid_configuration`; `authentication` is
`unverified`, `authenticated`, `refused` or `expired`; `scope_access` is
`unverified`, `verified` or `refused`. Configured does not mean authenticated.
Only an explicit task-authorized bounded request can provide an auth/scope
observation, and offline tests never prove live Universal Auth. A refused
request names its stage without echoing credentials; expiry is not replaced
with a fictional usable lifetime.

The existing fixed capability manifest owns permitted operations. Metadata
requests exclude values (`viewSecretValue=false`), resolved application values
stay in-process, and echoed-value responses are withheld. Do not add a generic
secret getter, HTTP proxy, environment dump, shell or capability beyond that
manifest as a setup shortcut.

## Offline validation and limits

```bash
.venv/bin/python -B environment/agents/adapters/manus/validate_manus_adapter.py --repo-root . --json
.venv/bin/python -B -m pytest -q environment/agents/adapters/manus/tests
.venv/bin/python -B tools/assurance/check_canonical_identity_projection.py
```

Structural/canonical PASS and `validate() == []` mean no source-contract errors;
they do not mean Memory is ready. Status keeps native binding and live proof
separate. Missing, tampered or non-current identity projection fails canonical
assurance rather than inventing identity.

No public Manus startup hook or Controller transport is created here. The
`manus-cloud` PE provider stays dormant. Ordinary authorized work remains
subject to shared worktree, L4 and publish-path gates. First publication uses
`PR_REMEDIATE=0 make pr`; the approved stack requires explicit `PR_STACK=auto`
and parent-owned authorization. This document confers no Git action, package
upgrade, live authentication, deployment, merge or secret provisioning.
