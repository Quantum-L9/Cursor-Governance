# ops/ci_parity — CI's scanners, before the push (hosted Claude Code)

CI used to be the first place a CodeQL or Semgrep finding appeared: push, wait,
read the alert, fix, push again. On #659 that cost three rounds. This package
runs the same scanners, at the same versions, at the cheapest moment that still
precedes the push, and keeps only what CI would flag: NEW findings on lines the
change touched.

Doctrine: `AGENTS.md` → `CI_PARITY_HOSTED_CLAUDE_V1`. Cursor never invokes any
of this (the hooks and the `make pr` wave entry are Claude-surface only).

## Files

| File | Role |
|---|---|
| `tools.yaml` | The one pin manifest: tool versions, sha256, CI evidence (`ci_ref`), lanes |
| `manifest.py` | Loader shared by every consumer; the kill switch `L9_CI_PARITY=0` |
| `validate_manifest.py` | Fails when a recorded CI pin moves without a re-pin |
| `install.py` | sha256-verified, flock single-flight, idempotent install (`--check` to audit) |
| `findings.py` | One finding shape; SARIF/JSON parsers; changed-line filter |
| `run.py` | Lanes, CPU budget, snapshot clone, receipts; `--file` / `--commit` / `--gate` / `--status` |
| `sonar_status.py` | Read-only SonarCloud PR quality gate + issues (never a scanner run) |
| `lanes/yamllint.yaml` | yamllint config for the lane (relaxed; errors block) |

Paid-tier Semgrep runs through `ops/secrets/capability_exec.py` (entry
`semgrep-pro` in `ops/secrets/capability-exec.json`).

## When each lane runs

| Moment | Trigger | Lanes | Where | Blocks |
|---|---|---|---|---|
| Edit | PostToolUse Edit/Write (`ci_parity_posttool.py`) | fast: ruff, shellcheck, actionlint, zizmor, yamllint, biome | the edited file, in the workspace | no — findings on the edited lines go back to the agent |
| Commit | PostToolUse Bash when HEAD moved | every applicable lane | background, `~/.cache/l9-ci-parity/<repo>/clone` at the commit | no — writes receipts |
| Push | PreToolUse `git push` (`ci_parity_push_gate.py`) and the `make pr` wave | reuses receipts; runs what is missing | snapshot clone | yes: NEW finding, changed line, blocking severity |
| After push | PostToolUse on `git push` | SonarCloud read | API | no |

A lane applies only when the change touches a file it globs. `osv-scanner`
compares the changed lockfile against the base and reports vulnerabilities the
change introduced. pip-audit is installed but has no lane: the `make pr`
security wave already runs that exact pin when dependency files change.

## What blocks, and why it matches CI

- **Diff scope.** Findings are kept only when they land on a line added or
  modified between the merge-base and the commit. The base is the open PR's
  base branch (REST GET), else `PR_BASE`, else `origin/main`.
- **CodeQL.** CI's analysis is diff-informed: a data-flow result counts when
  its source or sink is in the diff. `findings.py` keeps every flow location for
  that reason; checking only the reported sink line misses real alerts.
  Blocks on error level or security-severity ≥ 7.0, like code scanning.
- **Semgrep (L9 Analysis config).** CI runs strict: a rule that fires without an
  entry in `.github/governance/semgrep-identity-map.yaml` fails the job. The lane
  blocks on exactly that.
- **Semgrep Pro.** `semgrep ci --dry-run` fetches the org policy with the token
  and creates no scan. Advisory until probe U1 proves parity with the
  `semgrep-cloud-platform/scan` check.
- **Biome** is advisory, as in CI (`enforce-biome: false`).
- **New tools** (actionlint, zizmor, shellcheck, yamllint) block on error level
  on changed lines only, so existing debt never blocks.

## Parity proof (2026-09-24)

| Commit | CI verdict (CodeQL) | Local `run.py --gate` |
|---|---|---|
| `745a1b06` (#659 before its fix) | 3 new high alerts: `py/clear-text-logging-sensitive-data` at `ops/secrets/infisical_cli_login.py:73`, `ops/secrets/session_start_secrets.py:228`, `ops/scripts/session_start_runtime_report.py:933` | `blocking=3`, the same rule at the same three lines, nothing else |
| `29c767df` (#659 fixed) | CodeQL green | `blocking=0`, exit 0 |

Both runs: 4 CPU container, ~2.5 min wall-clock (CodeQL dominates). The
commit-time background run is what keeps that off the push path.

## Concurrency without collision

- Scans read a `git clone --shared` checkout of the commit, never the working
  tree, so edits in progress are neither read nor dirtied (the make pr gate's
  dirtiness detector stays quiet).
- One flock per repository serializes the snapshot clone; a newer commit
  cancels an older commit's run (latest wins).
- Lanes share a weighted semaphore of nproc slots at nice 10, so `pytest -n auto`
  in `make pr` keeps priority.
- Receipts are keyed by (commit, merge-base, lane config, tool version, runner
  code digest): any change to how a finding is judged voids them.

## Operating

```bash
python3 ops/ci_parity/install.py --check      # 10/10 OK at pinned versions
python3 ops/ci_parity/run.py --status         # receipts + in-flight run
python3 ops/ci_parity/run.py --gate HEAD      # what the push gate would say
python3 ops/ci_parity/sonar_status.py --auto  # SonarCloud for this branch's PR
L9_CI_PARITY=0                                # session kill switch
```

## Re-pinning

When `validate_manifest.py` reports a moved CI pin: read the CI log for the
version it now runs, update `version`, `url`, `sha256` and `ci_ref` in
`tools.yaml` together, then `install.py` and re-run the parity replay.
