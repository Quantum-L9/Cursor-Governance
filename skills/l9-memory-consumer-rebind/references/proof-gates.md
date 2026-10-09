<!-- L9_META
schema: 1
parent: l9-memory-consumer-rebind
layer: reference
role: proof-gates
status: active
-->

# Proof gates

Load this when proving the artifact, the grants, MCP, or publication.

## Artifact

Keep the cross-repo workflow's rebuild only when `uv build --wheel` from the peeled source, using the release `SOURCE_DATE_EPOCH`, produces the official digest. Otherwise the proof installs and hashes the official wheel. Do not add a second release-build pipeline.

## Grants and launcher

Trace registry grant to signed assertion to `ops/memory/run_memory_mcp.sh` to the bound verifier.

The launcher resolves governance to its own checkout when `CANONICAL_LAW.md` is there. `L9_GOVERNANCE_DIR` still wins when set. `$HOME/.cursor-governance` is only the fallback for a copied wrapper.

Identity comes from host markers. A caller-supplied static agent id does not grant identity. The door is the registry grant plus the signing material, never a request body.

Refuse missing grant, invalid signature, wrong actor, unauthorized namespace, and missing interpreter. Do not set a local-operator opt-out to make a red test pass.

## MCP

Cursor install goes through the package configurator. `L9_MEMORY_MCP_COMMAND` is the signed-agent launcher. The written entry has that command, the stdio args, and no env block.

Prove a temporary config. Do not write the live workstation MCP file unless cutover was authorized.

Claude's canonical file is `environment/agents/adapters/claude-code/mcp.template.json`. Regenerate from it. Do not keep a competing `.mcp.json` authority.

Isolated store, no production database: initialize, tool discovery, health, search, hydrate, `memory.write_agent`, phase lock, governed write, and an authorization rejection. One write, one record, correct agent attribution, readable from a second process after the first process exits.

## Audit command

A lockfile audit that reinstalls the project environment drops the PEP 610 seal. The existing audit invocation must not sync. `--no-sync` on that invocation is the repair. Do not disable the audit.

## Tests

Run the existing memory suites with the cross-repo requirement flag and the bound interpreter. The run that claims the flag must report zero skips. The velocity publication gate may skip that suite when the flag is unset. That skip does not replace the required run.

The real configurator handshake must supply its own cursor door and must not depend on a workstation key file or on `$HOME/.cursor-governance`.

## Publication

Hold unrelated dirty paths so the release receipt matches the rebind tree. Pathspec commits only. Authorize that clean tree. `PR_REMEDIATE=0 make pr` with empty `PR_STACK`.

After the PR exists, record its number, base, head, changed paths, and check conclusions. Required checks must pass. Do not merge.

Exclusions that stay outside this skill: upstream source edits, tag moves, production database, secret provisioning, host deployment, and the live workstation MCP file.
