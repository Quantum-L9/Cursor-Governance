# Cursor-Governance Peer Execution Core PR Pack v3

PR-ready local application pack bound to:

`Quantum-L9/Cursor-Governance@0fbd477e507d33ee52f2a87c2d9eb77c15b6a492`

No remote write, branch creation, commit, push, or PR creation is performed.

## Objective

Make peer/provider adapters thin by construction and move reusable execution
behavior upstream into one canonical Peer Execution Core.

Target execution chain:

```text
Program Controller
-> Peer Runtime Binding
-> Execution Profile
-> Peer Execution Core
-> Shared Transport
-> Thin Provider
-> Provider / Host
```

Claude Code becomes the first thin implementation provider. DeepSeek remains
intentionally deferred and can later enter through Claude Code backend
configuration or a thin provider using the same canonical execution boundary.

## What the PR changes

- promotes `environment/program-execution/adapters/common/` into the canonical
  `environment/program-execution/peer_execution/` substrate;
- leaves `adapters/common/` only as compatibility re-export shims;
- introduces versioned canonical execution request, provider result, context,
  execution-profile, and peer-binding contracts;
- separates `agent_ref`, surface, provider, and execution profile in
  `PEER_RUNTIME_BINDINGS.yaml`;
- migrates Claude Code to a thin provider; validated context, permission ceilings,
  timeout policy, telemetry normalization, and receipt construction are resolved
  upstream before provider invocation;
- retires `claude-code-bounded-autonomy` as a provider identity;
- moves bounded execution mechanics from the Claude adapter tree into shared
  `peer_execution/autonomy/` infrastructure;
- adds a provider-neutral single-task pipeline facade with a non-mutating host
  preflight before Controller admission and an exact Program-Lock-bound probe
  after render;
- bridges canonical Controller rendered-contract v2 directly, without requiring
  a duplicate authorization ceiling that the Controller already enforced;
- enforces execution-profile permissions in Peer Execution Core for every
  provider, not only inside Claude-specific tool rendering;
- persists canonical dispatch intent before provider invocation and rejects
  request, budget, worktree, context, capability, provider, and profile drift;
- rejects unsafe runtime identifiers, symlinked runtime/context records, unsafe
  compound validation shell commands, and empty verification-gate false passes;
- denies all remote/release/deployment/destructive worker action classes upstream
  and writes context manifests atomically before provider execution;
- extends thin-driver conformance across every routable worker, verifier,
  remote-action, and deployment adapter kind while keeping the target deployment
  factory explicitly non-routable;
- updates active architecture doctrine, law, ADRs, and execution-plan routing;
- preserves old validation evidence under `validation/history/` rather than
  presenting pre-migration results as current proof;
- adds Controller-owned `abort-execution` recovery for admitted failures, including
  stale unrecorded Attempt Receipt quarantine before retry;
- makes Attempt Receipt handoff atomic, workspace-confined, conflict-detecting, and
  durable before `collect: PASS` is appended;
- stages the complete pack migration in an isolated detached worktree and applies
  one verified binary patch atomically to the operator target.

## Use

From an exact clean clone at the bound SHA:

```bash
python3 <pack>/scripts/apply_pr_pack.py /path/to/Cursor-Governance
python3 <pack>/scripts/validate_applied_repo.py /path/to/Cursor-Governance \
  --output /tmp/peer_execution_pr_validation.json
python3 <pack>/scripts/export_patch.py /path/to/Cursor-Governance \
  --output /tmp/peer_execution_core.patch
```

Then inspect the local diff. Nothing in this pack contacts a Git remote.

## Included

- `architecture_authority/`: binding thin-adapter law plus accepted ADRs.
- `repo_overlay/`: files copied into the bound repository after deterministic
  moves/removals.
- `scripts/apply_pr_pack.py`: exact-base local migration.
- `scripts/validate_applied_repo.py`: deterministic post-apply PR gates.
- `scripts/export_patch.py`: local unified/binary patch exporter.
- `scripts/validate_pack.py`: self-integrity and static architecture checks.
- `PR_DESCRIPTION.md`: ready-to-use PR narrative.
- `CHANGESET.yaml`: machine-readable implementation delta.
- `VALIDATION.md`: evidence and explicit unrun gates.

## Excluded

- DeepSeek integration or credentials;
- provider-specific cost pricing;
- remote GitHub mutations;
- Program Controller redesign;
- automatic merge or deployment;
- pretending dormant Codex/Gemini/Manus transports are executable.
