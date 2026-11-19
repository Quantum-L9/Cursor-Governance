# Open

Owner queue. Nothing below is done.

## Claude desktop and hooks

- Claude Code desktop does not fan out. The 480-lane profile is a ceiling. `/autonomy` and `/l9-bounded-autonomy` are user-invocable only, there is no campaign graph unless `cli.py init` ran, and `Agent` is not pre-allowed. Desktop Build and remediation stay single-agent until those four are true.
- Collapse Claude Code bootstrap to one script. One file holds the mobile environment variables. Delete the superseded copies.
- Which Cursor hook events still lack a merge gate sibling? Claude has `merge_gate_wrap.py`. Cursor `beforeShellExecution` runs L4, not merge.
- Audit Cursor, Claude Code desktop, and Claude Code mobile hooks. Cursor and Claude may diverge. Desktop and mobile should match except for a native interface difference.
- Consider `git fetch --prune` in `l9-repo-hygiene`.

## Publication, pins, and reviews

- Align pins across repos and lock them.
- Dependabot: which PRs to merge, which to close, and how a bump stays aligned with the pins.
- Verify CI-repo releases. Fan-out from ci-core must be unblocked so consumers inherit CI from ci-core.
- `.github` doc PRs to consumers must not fail consumer CI. Prior ones needed remediation and were deleted.
- Verify the GitHub code-review agent is enabled.
- Copilot: assign seats or enable review-without-a-license, plus a hard AI-credit budget. Default effort Lite. Do not auto-request Copilot on every PR into the default branch. Request it for feat/fix/perf/refactor code diffs, excluding `feat/ff-shelf-*`, dependabot, chore/docs/ci, and generated or corpus-only diffs. Keep Code Quality on for every PR. Leave the disabled "Code Quality Copilot review for default branch" ruleset disabled. Do not add org-wide merge-blocking quality gates yet.
- Remove the personal name from CODEOWNERS. Replace it with Quantum AI Partners in `.github` and push that revision to consumer repos.
- Merge the Odoo PRs and disable owner approval.
- L4 `authorize-release` is a routing gate. `begin` plus `authorize-release` does not prove kernels or finished work. Harden it so a release receipt cannot be minted without evidence.
- Hooks, repo hygiene, `l9-git-work-preserve`, and `/ff` should leave a tree Claude Code will execute without stopping on dirt.

## Skills and campaigns

- Turn this file into a JSON execution contract a plan or Program Execution campaign can run.
- `l9-issue-remediation`: `/issues` is Diagnose. Add an explicit converge mode with `PR_STACK=auto` and `PR_REMEDIATE=0` written in the file. Publish is two shells (`l4 begin` then `authorize-release`, then `make pr`), never one compound line. Print the stack tip before mutating. Stop after the PR opens. Close the issue when it is resolved.
- Review `fix/ordinary-native-task-admission` (`443c7bf6`, `eba7aaad`) before publish. Ordinary Tasks with no campaign runtime are allowed. Campaign Tasks stay fail-closed. Not pushed.
- Run the ChatGPT test runbooks on the Meta-Injector, Topology, and Graphiti-Memory repos.

## Still in the tree

- [ ] Promote `ops/ui-operator/cartridges/vercel-project-settings-stub.yaml` to a filled v1 cartridge after approval.
- [ ] `intelligence/reasoning/reasoning-snapshot-generator.py` — keep, needs a fix.
- [ ] `intelligence/reasoning/cursor-native-reasoning.md` — compare with `l9-structured-reasoning` before editing or deleting.
- [ ] `workflows/Dags-Harvest/DAG-Harvest-5.md` — startup references, verify.
- [ ] Markdownlint MD024: duplicate `### Diagnose` / `### Converge` in `skills/l9-issue-remediation/SKILL.md` and `skills/l9-pr-remediation/SKILL.md`. MD029 step 7 in `commands/l9-issue-remediation.md`. Same pattern in both packs' `references/`.
- [ ] mypy, advisory since 2026-07-28: `workflows/gmp_executor.py`, `workflows/dags/inspect_dag.py`, `workflows/harvest_deploy.py`, `workflows/nodes/{validate,report}.py`, `workflows/state.py` reducer redefinition.
- [ ] `tools.validation.validate_external_code` — deferred gap.
- [ ] Decide whether `pre-commit install` is an optional local hook. This repo has no commit hook.
- [ ] Retire `make push: precommit backup` and the Claude `pre-commit install` instruction.
- [ ] Re-enable merge authority (`ops/config/merge-authority.json` is `"enforcement": "disabled"`, CANONICAL_LAW §6.2.16). Fix the recorder first, or `strict` is unusable: Cursor receipts are not grantable, a typed `/l9-pr-remediation` can be dropped, chat instructions only record on the `_DIRECTED` grammar, receipts die with the session, and terminal grants need `/dev/tty`.
- [ ] Confirm a `main` run of Exact-head memory lifecycle proof executes the wheel build, install, binding check, and lifecycle test, with none skipped. `MEMORY_PROOF_ADVISORY` is `"false"`. The clone is a non-persisted `actions/checkout` of `Quantum-L9/l9-graphiti-memory` with `GH_TOKEN`. `L9_GITHUB_READ_TOKEN` is not in this pull-request workflow. Run 44396822814 was green while those four steps were skipped.
