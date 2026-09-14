# RUNBOOK — Program Execution Control Plane

Target: Quantum-L9/Cursor-Governance
Scope: PE-010, PE-020, MQ-010, EN-010, PR-010, SC-010, OB-010
Mode: create-only for new files. Existing repo files are appended to /
edited in-place per the explicit instructions in each step below (Gap 2)
— never blindly overwritten.

Every step below states the exact `gh`/token scope an automation agent
needs to execute it (Gap 1). Use the narrowest scope listed; do not grant
a broader PAT than the step requires.

## 0. Preconditions

- `main` is protected; you have PR merge rights or a reviewer who does.
- `gh` CLI authenticated. See the per-step token table below — no single
  token needs every scope; provision per-step if running unattended.
- Python 3.11+, `pip install pyyaml jsonschema pytest`.
- `conftest` installed for PE-020/policy steps (install command in that
  step's workflow file).

## Token/permission matrix (Gap 1)

| Step | Action | Required scope / permission | Notes |
|---|---|---|---|
| 1 (PE-010) | Push branch, open PR | `contents:write`, `pull_requests:write` (fine-grained) or classic `repo` | Standard PR creation; no admin scope needed |
| 1 (PE-010) | `agent_git.py claim/commit/push` | `contents:write` on the repo | Runs against a worktree, not `main` directly — branch protection still applies |
| 2 (PE-020) | Edit `CODEOWNERS`, `ORG_INVARIANTS.yaml`, `COMMANDS_MANIFEST.yaml` | `contents:write` | No elevated scope; these are normal file edits via PR |
| 2 (PE-020) | Apply GitHub ruleset via `gh api /repos/.../rulesets` | `administration:write` (fine-grained) or classic `repo` + org owner/maintain role | This is the first step that needs elevated, human-approved access — do not automate without explicit sign-off |
| 3 (MQ-010) | Enable "Require merge queue" | `administration:write` or Settings UI as repo admin | UI-only for most orgs; API path also needs `administration:write` |
| 3 (MQ-010) | Edit `l9-lint-test.yml` to add `merge_group` trigger | `contents:write` | Normal workflow-file edit |
| 4 (EN-010) | Supabase branch/GitHub integration setup | Supabase project owner/admin role (not a GitHub token) | Out of GitHub's token model entirely — a Supabase dashboard action |
| 4 (EN-010) | Vercel-Supabase integration | Vercel project admin | Same — external dashboard, no GitHub scope applies |
| 4 (EN-010) | `environment_lease.py claim/verify` in CI | `contents:read` (reads reports dir) | Runs inside Actions with default `GITHUB_TOKEN`; no PAT needed |
| 5 (PR-010) | `actions/attest-build-provenance` | `id-token:write`, `attestations:write` (workflow permissions block, not a PAT) | Set in the workflow's `permissions:` block, already present in `artifact-provenance.yml` |
| 5 (PR-010) | `gh attestation verify` | `attestations:read` | Read-only; safe to run in any job including forked-PR contexts with default token |
| 5 (PR-010) | Wire deploy gate to real deploy command | Whatever your deploy target requires (e.g. Vercel token) — unrelated to GitHub scopes | Document separately per deploy target |
| 6 (SC-010) | `semantic_merge_probe.py` trial merge in `merge_group` | `contents:read` | Read-only checkout; the trial merge happens in a disposable worktree, never pushed |
| 6 (SC-010) | Upload/read test-impact artifacts | `actions:write` (default in Actions context) | Standard `actions/upload-artifact`/`download-artifact` permission, already default |
| 7 (OB-010) | `emit_program_execution_metrics.py` / `ops/lib/telemetry.py` | `contents:write` if committing telemetry JSONL to the repo; `contents:read` if writing to a runner-only path | Recommend runner-only path (e.g. artifact upload) over committing telemetry to git |

General rule: only step 2's ruleset application and step 3's merge-queue
toggle need `administration:write` / org-admin. Everything else is normal
`contents:write` or the zero-config default `GITHUB_TOKEN` inside Actions.
Never grant `administration:write` to an unattended agent — those two
actions require a human running `gh api` or clicking through Settings.

## 1. PE-010 — Foundation (feature tree + agent git)

1. Create branch `feat/program-execution-foundation` from `main`.
2. Add: `contracts/schemas/canonical.schema.feature_tree.v1.yaml`,
   `tools/check_feature_tree.py`, `tools/agent_git.py`,
   `commands/agent-git.md`, `.github/workflows/feature-tree-gate.yml`,
   `.github/workflows/agent-git-guard.yml`, `ops/lib/telemetry.py`,
   `tests/tools/*`, `tests/fixtures/feature_trees/*`.
3. Create the first live tree at `reports/<date>/tasks/feature_tree.v1.yaml`
   using `example_minimal_tree` in the schema file as a template.
4. Run locally:
   ```
   python tools/check_feature_tree.py --tree reports/<date>/tasks/feature_tree.v1.yaml --json
   pytest tests/tools/
   ```
5. Open PR titled `PE-010: feature-tree gate + agent-git driver`
   (token: `contents:write` + `pull_requests:write`, see matrix above).
6. Do NOT edit `ORG_INVARIANTS.yaml`, `COMMANDS_MANIFEST.yaml`, or
   `CODEOWNERS` yet — that's step 2 below.
7. Merge only after both new checks pass.

## 2. PE-020 — Policy compiler + wiring into existing repo files (Gap 2)

Depends on PE-010 merged. This step is where the "deferred" edits from
PE-010 actually land — as explicit append/modify instructions against
files that already exist in your repo, not new files.

1. Branch `feat/policy-compiler` from `main`.
2. Add new files: `tools/generate_program_execution_artifacts.py`,
   `policy/feature_tree.rego`, `policy/testdata/*.yaml`,
   `governance/generated/CODEOWNERS`,
   `governance/generated/github-ruleset.program-execution.json`,
   `.github/workflows/policy-conftest.yml`.
3. Regenerate and verify no drift:
   ```
   python tools/generate_program_execution_artifacts.py \
     --tree reports/<date>/tasks/feature_tree.v1.yaml \
     --out-codeowners governance/generated/CODEOWNERS \
     --out-ruleset governance/generated/github-ruleset.program-execution.json
   conftest verify --policy policy
   conftest test --policy policy reports/<date>/tasks/feature_tree.v1.yaml
   ```
4. **Append to `ORG_INVARIANTS.yaml`** (do not remove existing entries) a
   new top-level block:
   ```yaml
   program_execution_invariants:
     feature_tree_schema: contracts/schemas/canonical.schema.feature_tree.v1.yaml
     agent_git_required: true
     merge_order_source: reports/latest/tasks/feature_tree.v1.yaml
   ```
5. **Append to `commands/COMMANDS_MANIFEST.yaml`** a new entry registering
   `/agent-git` (match your manifest's existing entry shape, e.g.):
   ```yaml
   - command: agent-git
     path: commands/agent-git.md
     category: git-operations
   ```
6. **Modify root `CODEOWNERS`**: either append `# Program execution ownership: see governance/generated/CODEOWNERS`
   as a pointer comment, or `include`/concatenate the generated file's
   contents at the bottom (do not delete pre-existing ownership lines).
7. **Modify `Makefile`**: append targets, do not replace existing ones:
   ```makefile
   feature-tree-check:
   	python tools/check_feature_tree.py --tree reports/latest/tasks/feature_tree.v1.yaml --json

   agent-git-doctor:
   	python tools/agent_git.py --cwd . doctor
   ```
8. **Modify `.pre-commit-config.yaml`**: append a new hook entry:
   ```yaml
     - repo: local
       hooks:
         - id: feature-tree-check
           name: feature-tree-check
           entry: python tools/check_feature_tree.py --tree reports/latest/tasks/feature_tree.v1.yaml
           language: system
           pass_filenames: false
   ```
9. Token: `contents:write` for all of the above; the ruleset `gh api`
   apply (below) needs `administration:write` — get explicit human sign-off
   before running it (see token matrix).

## 3. MQ-010 — Merge queue

Depends on PE-020 merged.

1. Branch `feat/merge-queue` from `main`.
2. Add `tools/check_merge_queue.py`, `policy/merge_queue.rego`,
   `ops/config/merge-queue.config.yaml`,
   `contracts/program-execution/canonical.merge_queue.v1.yaml`,
   `.github/workflows/merge-queue.yml`.
3. **Modify `.github/workflows/l9-lint-test.yml`** (and any other required
   check workflow): append `merge_group:` under its existing `on:` block —
   do not remove `pull_request:` or other existing triggers:
   ```yaml
   on:
     pull_request:      # existing — leave as-is
     merge_group:        # append this line
   ```
   This edit is mandatory — GitHub cannot report a required check inside
   the queue without it.
4. Apply external configuration per
   `EXTERNAL_CONFIGURATION/github-ruleset.program-execution.md` and
   `EXTERNAL_CONFIGURATION/github-merge-queue.md` (needs
   `administration:write` / org-admin — human action, not agent-automatable).
5. Verify with a throwaway PR that "merge-queue-ci / required-checks" is
   required, and that a second run appears tagged `merge_group`.

## 4. EN-010 — Environment leases

Parallel-safe with MQ-010.

1. Branch `feat/environment-leases` from `main`.
2. Add the EN-010 files (schema, tool, config, sweep script, gate workflow —
   see MANIFEST.json for the exact list).
3. Apply Supabase/Vercel external configuration per the two
   `EXTERNAL_CONFIGURATION/*.md` docs (dashboard actions, not GitHub tokens).
4. Verify a real PR claims a lease, deploys a preview, and the gate fails
   correctly on an `--expect-db-branch` mismatch.
5. Schedule `ops/scripts/reconcile_preview_leases.py` (cron workflow) at
   `sweep_interval_minutes` from `ops/config/environment-lease.config.yaml`.

## 5. PR-010 — Signed provenance

Depends only on PE-010.

1. Branch `feat/artifact-provenance` from `main`.
2. Add `contracts/program-execution/canonical.provenance.v1.yaml`,
   `tools/verify_provenance.py`, `policy/provenance.rego`,
   `.github/workflows/artifact-provenance.yml`,
   `.github/workflows/deploy-with-provenance-gate.yml` (new — closes the
   "gate with nothing plugged into it" gap).
3. **Replace the placeholder build step** in `artifact-provenance.yml`
   (`echo "build step placeholder..." > artifact.txt`) with your actual
   build/package command, and the placeholder deploy step in
   `deploy-with-provenance-gate.yml` with your real deploy command.
4. **Append to `governance/TRUST_MODEL.md`**: a sentence stating deployment
   requires `gh attestation verify` to pass, not merely an `L9-Agent`
   commit trailer.

## 6. SC-010 — Semantic conflict + test impact

Depends on PE-020 and MQ-010 merged.

1. Branch `feat/semantic-conflict` from `main`.
2. Add the SC-010 files plus the now-included
   `reports/latest/semantic_contracts/*.yaml` (one per node — see MANIFEST)
   and `reports/latest/test_impact_map.v1.yaml`, both authored in this
   pack (closes the "no semantic contracts exist" gap).
3. Every future node must add its own
   `reports/latest/semantic_contracts/<NODE-ID>.semantic_contract.v1.yaml`
   alongside its `contract` field.
4. Extend `reports/latest/test_impact_map.v1.yaml` whenever a new tool or
   test file is added — until an entry exists, `test-impact.yml` correctly
   falls back to the full suite.

## 7. OB-010 — Observability (now wired, not standalone)

Depends on PE-010, EN-010, MQ-010, SC-010 merged.

1. Branch `feat/program-execution-telemetry` from `main`.
2. Add `ops/schemas/program_execution_event.schema.json`,
   `ops/scripts/emit_program_execution_metrics.py`, `ops/lib/telemetry.py`
   (new shared in-process emitter, tested in
   `tests/tools/test_telemetry.py`).
3. Apply the four call-site edits in `wiring/ob-010-instrumentation-diffs.md`
   to `tools/agent_git.py`, `tools/check_feature_tree.py`,
   `tools/environment_lease.py`, and `tools/semantic_merge_probe.py` —
   each is a 2-4 line addition at an existing function boundary, not a
   rewrite. This closes the "OB-010 emits nothing automatically" gap.
4. **Append to `ops/governance-dashboard.md`** and
   `ops/feedback_loop_config.yaml`: point them at
   `reports/<date>/telemetry/program_execution_events.jsonl`.

## Rollback

Every node is additive and independently revertable: `git revert` the
node's merge commit. Step 2/3/5/7's file *edits* (append-only by design)
revert cleanly with the same commit revert, since nothing pre-existing
was deleted, only appended to.
