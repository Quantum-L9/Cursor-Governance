# RB-HK-001 - Repository Housekeeping

| Field | Value |
|---|---|
| Runbook ID | RB-HK-001 |
| Version | 1.0.0 |
| Owner | Quantum-L9 |
| Target repo | `Quantum-L9/Cursor-Governance` |
| Blast radius | GitHub branch rulesets, 14 remote branches, root-level file renames, `.github/**`, `.gitignore` |
| Reversibility | Rulesets: instant. Branch deletions: recoverable by SHA (recorded in Section 4.2). Renames: revert commit. |
| Est. duration | Phase 0-2: 45 min. Phase 3 automation: 30 min. |
| Recurrence | Phases 0-2 are one-time. Phase 3 makes them never needed again. |

---

## 1. Objective

Close the housekeeping gaps found in the 2026-08-13 audit, then automate each
one so the same debt cannot re-accumulate. The test of success is not a clean
repo today - it is that no human runs this runbook a second time.

## 2. Findings this runbook closes

| ID | Finding | Severity |
|---|---|---|
| H-01 | `main` is unprotected (`"protected": false`) | Critical |
| H-02 | 14 non-`main` branches, zero open PRs | High |
| H-03 | Filenames containing spaces (3 known) | Medium |
| H-04 | Generated reports and runtime state committed | Medium |
| H-05 | `.env.example` and `.env.template` both present | Low |
| H-06 | No `dependabot.yml` despite three dependency manifests | Medium |
| H-07 | Repo governs other repos but not itself in CI | High |
| H-08 | Three competing in-flight work locations | Resolved by decision, see Section 6 |

## 3. Preconditions

- [ ] You have **admin** on `Quantum-L9/Cursor-Governance` (required for rulesets).
- [ ] Working tree clean; you are on a branch, not `main`.
- [ ] `gh` CLI authenticated (`gh auth status`).
- [ ] The rules and skills normalization packs are unzipped but **not yet run**.
      Phase 2 renames paths; do that before glob-dependent work.

**Stop condition.** Without admin, Phase 0 cannot be completed. Do not proceed
to Phase 3 without Phase 0 - required status checks are meaningless on an
unprotected branch.

## 4. Procedure

### Phase 0 - Protect `main` (do this first, 10 minutes)

Every write-authority rule in `rules/` is currently advisory. GitHub enforces
nothing. The governing principle: AI agents may propose code, never own it -
no direct pushes to `main`, and CI is the real gate.

1. Repo **Settings > Rules > Rulesets > New branch ruleset**.
2. Name `main-protection`. Target `main`. Enforcement **Active**.
3. Enable:
   - Restrict deletions
   - Block force pushes
   - Require a pull request before merging, 1 approval
   - Dismiss stale approvals on new commits
   - Require conversation resolution
   - Require status checks to pass
4. Add as required status checks, using the exact job names:
   - `l9-lint-test`
   - `validate-org-policy`
   - `root-file-protection`
   - `codeql`
5. Save. Verify with:

```bash
gh api repos/Quantum-L9/Cursor-Governance/branches/main --jq '.protected'
```

Must print `true`. If it prints `false`, the ruleset did not apply - check that
the target pattern matches `main` exactly.

6. Repo **Settings > General**: enable **Automatically delete head branches**.
   This alone prevents H-02 from recurring.

Once `rules-check` and `skills-check` exist from the other two packs, add them
as required checks too.

### Phase 1 - Branch cleanup (15 minutes)

There are zero open PRs, so every branch below is merged or abandoned.

#### 4.1 Classify before deleting

Run the provided script in report mode. It never deletes without `--apply`, and
it refuses to delete anything not fully merged into `main` unless you pass
`--force-unmerged`.

```bash
./scripts/cleanup_branches.sh                 # report only
./scripts/cleanup_branches.sh --apply         # delete merged branches
```

#### 4.2 Recorded SHAs (recovery record)

Deleting a remote branch is recoverable for ~90 days via `git reflog` on a
local clone, or immediately by re-pushing these SHAs. Recorded at audit time:

| branch | sha |
|---|---|
| `chore/memory-bank-tracking-and-ssot-freshness-check` | `f9f9054` |
| `chore/seed-governance` | `d1723a8` |
| `claude/claude-code-env-optimization-6tylwl` | `abc89d0` |
| `claude/cursor-governance-integration-f2zbb6` | `6f8e8c2` |
| `claude/new-environment-status-kfi10e` | `8ea070c` |
| `claude/startup-script-environment-ucgd5i` | `ccf4032` |
| `docs/l9-plan-kernel-pipeline` | `d29d8d4` |
| `feat/autonomy-first-class` | `48acbe3` |
| `feat/extinguish-claude-code-symlink` | `1370a90` |
| `feat/l9-plan-pe-autonomy-executable-template` | `61c1806` |
| `feat/sessionend-phase-b-gha-distill` | `218c228` |
| `feat/sessionend-phase-b-gha-distill-v2` | `a507ceb` |
| `fix-pr23-sonar` | `2cad996` |
| `pr-23` | `a93a6fc` |

To restore any one:

```bash
git push origin <sha>:refs/heads/<branch-name>
```

#### 4.3 Handle the unmerged ones deliberately

Any branch the script reports as **unmerged** contains work that exists nowhere
else. For each: open a PR, cherry-pick what matters, or file a Linear issue
capturing the intent, then delete. Do not force-delete unmerged work to make a
report green.

Note `feat/sessionend-phase-b-gha-distill` and `-v2` - the `-v2` suffix means
one supersedes the other. Confirm which, then delete both after merging the
survivor. Also `pr-23` and `fix-pr23-sonar` are remnants of one closed PR.

### Phase 2 - Path and file hygiene (20 minutes)

#### 4.4 Rename paths containing spaces

Spaces break shell globs, CI path filters, and `find`/`xargs` pipelines.

```bash
git mv "Activation Command.md" activation-command.md
git mv "key components" key-components
git mv "commands/harvest copy.md" commands/_harvest-copy-REVIEW.md
```

Then grep for every old reference and update it - including
`RULES-MANIFEST.yaml`, `COMMANDS_MANIFEST.yaml`, `AGENTS.md`, and
`.cursor-plugin/plugin.json`:

```bash
grep -rIn --exclude-dir=.git -e "Activation Command" -e "key components" -e "harvest copy" .
```

`_harvest-copy-REVIEW.md` is intentionally named to be obviously temporary.
Resolve it against `harvest.md`, `harvest2.md`, and `use-harvest.md`, then
delete it. That is a human merge decision, not an agent one.

#### 4.5 Stop committing generated and runtime files

Add to `.gitignore`, then untrack:

```bash
cat >> .gitignore <<'EOF'

# generated reports - CI artifacts, not source
governance-health-report.json
docs/rules-frontmatter-inventory.md
docs/skills-inventory.md

# runtime state
.harvest_executor_state.json
.governance-build-lock
EOF

git rm --cached governance-health-report.json .harvest_executor_state.json .governance-build-lock
git rm --cached commands/.harvest_executor_state.json
```

Ship `.harvest_executor_state.example.json` with structure and no live values.

**Decide `.governance-build-lock` deliberately.** If it is a reproducibility
lock consumed by CI, it stays tracked and this step is wrong. If it is a local
mutex, it goes. Check `Makefile` and `.github/workflows/` for readers before
untracking.

#### 4.6 Collapse the duplicate env template

Keep `.env.example` - the conventional name. Fold any unique keys from
`.env.template` into it, delete `.env.template`, update references.

Two templates guarantee they diverge, and a stale template is how a
missing-variable outage happens.

### Phase 3 - Automation (30 minutes) - the part that matters

Copy each file from `workflows/` into `.github/workflows/`, except
`dependabot.yml` which goes to `.github/dependabot.yml`.

| File | Destination | Prevents |
|---|---|---|
| `dependabot.yml` | `.github/dependabot.yml` | H-06 |
| `repo-hygiene.yml` | `.github/workflows/` | H-03, H-04, H-05 |
| `governance-self-check.yml` | `.github/workflows/` | H-07 |
| `branch-hygiene.yml` | `.github/workflows/` | H-02 |

Then:

1. Run each workflow once via `workflow_dispatch` and confirm green.
2. Add `repo-hygiene` and `governance-self-check` to the required checks from
   Phase 0. A check that is not required is a suggestion.
3. Leave `branch-hygiene` on its schedule; it reports and does not delete
   unless you set `DELETE_MERGED=true`.

## 5. Validation

1. `gh api .../branches/main --jq '.protected'` prints `true`.
2. Required checks listed on the ruleset match the workflow job names exactly.
3. `git ls-remote --heads origin | wc -l` matches your intended branch count.
4. `./scripts/check_repo_hygiene.py` exits 0.
5. No path in `git ls-files` contains a space.
6. `git ls-files | grep -E 'governance-health-report|harvest_executor_state'`
   returns nothing.
7. Auto-delete head branches is enabled.
8. A test PR from a throwaway branch is blocked until checks pass.

Step 8 is the only one that proves enforcement rather than configuration. Do it.

## 6. Work-tracking contract (H-08 resolved)

Decision recorded 2026-08-13:

| Location | Owner | Purpose |
|---|---|---|
| `WIP/` | **Human** | Your scratch space. Agents do not read or write it. |
| `TODO.md` | **Agent** | Agent-maintained task queue. |
| `current_work/` | **Retired** | Migrate contents to one of the above, then delete. |
| Linear | Both | Cross-session commitments and audit record. |

Enforce the boundary mechanically, not by convention. Add to `.cursorignore`:

```
WIP/
```

That is the whole point of the split: `WIP/` stops consuming context and stops
being something an agent can act on. Add a rule stating the agent owns
`TODO.md` and never touches `WIP/`, and let `repo-hygiene.yml` fail if
`current_work/` reappears.

`TODO.md` being agent-owned implies a format contract: one task per line,
status prefix, and a Linear identifier when work spans sessions. Without that,
`TODO.md` becomes a second unstructured scratch file.

## 7. Rollback

| Phase | Rollback |
|---|---|
| 0 | Set the ruleset to **Disabled**, or delete it. Instant. |
| 1 | `git push origin <sha>:refs/heads/<branch>` using Section 4.2. |
| 2 | `git revert` the rename/gitignore commit. |
| 3 | Delete the workflow file, and remove it from required checks first. |

Remove a check from the ruleset **before** deleting its workflow. Deleting the
workflow first leaves a required check that can never report, blocking all PRs.

## 8. Deferred - not in scope

Recorded so it is not lost, and explicitly not actioned now:

- **Directory consolidation.** `governance/` vs `execution-governance/`, and
  `workflows/` vs `pipeline/` vs `.wave/`, read as consolidation candidates,
  with negative code growth as the quality signal. Deferred because
  consolidation renames paths that rule globs and skill `paths` depend on.
  Revisit only after both normalization packs land and the glob sets are
  stable and CI-enforced.
- Command duplicate-cluster collapse (from the plugin audit).
- Skill pruning of unused `l9-*` skills.

## 9. Recurrence schedule

Once Phase 3 is live, the only recurring human action is reviewing what the
automation reports.

| Cadence | Action | Automated by |
|---|---|---|
| Every PR | Hygiene, governance self-check, CodeQL, lint/test | required checks |
| Weekly | Dependency PRs to review | `dependabot.yml` |
| Weekly | Stale-branch report | `branch-hygiene.yml` |
| On merge | Head branch deleted | repo setting |
| Quarterly | Read Section 8 and decide whether deferred items are still deferred | you |

## 10. Change log

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-13 | Initial. Phases 0-3, WIP/TODO contract, deferred list. |
