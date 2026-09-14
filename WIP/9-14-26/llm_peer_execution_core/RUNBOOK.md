# PR Pack Runbook

## Preconditions

- clean local clone of `Quantum-L9/Cursor-Governance`;
- `HEAD == 0fbd477e507d33ee52f2a87c2d9eb77c15b6a492`;
- Python environment capable of running the repository's existing validation;
- no need for GitHub credentials to apply or validate this pack.

## Apply

```bash
python3 scripts/apply_pr_pack.py /absolute/path/to/Cursor-Governance
```

The apply script fails closed on wrong SHA, dirty worktree, missing migration
anchors, or index/manifest regeneration failure.

It builds the complete migration in an isolated detached Git worktree, stages
that isolated result, creates one binary-capable patch, and applies it to the real
target only after staging succeeds. A failed apply resets the target to the exact
bound base and removes untracked pack residue. It does not run `git commit`,
`git push`, `gh`, or any remote API.

## Validate

```bash
python3 scripts/validate_applied_repo.py /absolute/path/to/Cursor-Governance \
  --output /tmp/peer_execution_pr_validation.json
```

All mandatory repository gates must PASS. Ruff is optional when unavailable: it is
reported as SKIPPED, never fabricated as PASS. Live peer probes are separately
environment dependent and are not converted into synthetic PASS results.

## Inspect

```bash
cd /absolute/path/to/Cursor-Governance
git status --short
git diff --stat 0fbd477e507d33ee52f2a87c2d9eb77c15b6a492
git diff --check 0fbd477e507d33ee52f2a87c2d9eb77c15b6a492 --
git diff 0fbd477e507d33ee52f2a87c2d9eb77c15b6a492 -- environment/program-execution environment/agents \
  environment/contracts CANONICAL_LAW.md AGENTS.md commands skills ops
```

## Export patch

```bash
python3 scripts/export_patch.py /absolute/path/to/Cursor-Governance \
  --output /tmp/peer_execution_core.patch
```

## Full pipeline smoke in a configured Claude environment

Use an instantiated Program Controller workspace whose task Source Contract is
already exact and admissible:

```bash
python3 environment/program-execution/scripts/run_peer_task_pipeline.py TASK-ID \
  --workspace "$HOME/.l9/programs/<program-id>" \
  --agent-ref claude-code \
  --surface claude-cli
```

The facade uses Controller claim/prepare/render/start, executes through the thin
Claude provider, records the canonical attempt receipt, and invokes independent
Controller verification. Add `--complete` only when Controller completion is
desired; Controller gates remain authoritative.

## Recovery

If an admitted execution fails, the pipeline requests Controller
`abort-execution`; the Controller preserves recovery evidence, quarantines any
unrecorded Attempt Receipt, releases the lease, and leaves the task in a legal
retryable failure/stale state. If pack validation fails, do not push. Inspect the
failing receipt or gate and rerun validation. To abandon pack changes, restore the
local clone from the exact bound commit using the operator's normal safe Git
workflow.
