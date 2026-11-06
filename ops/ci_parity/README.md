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
| Publish | `make pr` reader wave (non-Cursor surfaces) | `biome`, `semgrep-l9` only: Analyze (central Core)'s two blocking checks | snapshot clone at HEAD | yes — exit 2 fails the gate |
| CI | GitHub | CodeQL and every other check | GitHub | CI |
| After push | PostToolUse on `git push` | SonarCloud read | API | no |

A lane applies only when the change touches a file it globs. `osv-scanner`
compares the changed lockfile against the base and reports vulnerabilities the
change introduced. pip-audit is installed but has no lane: the `make pr`
security wave already runs that exact pin when dependency files change.

## What blocks, and why it matches CI

- **Diff scope.** Findings are kept only when they land on a line added or
  modified between the merge-base and the commit. The base is the open PR's
  base branch (REST GET), else `PR_BASE`, else `origin/main`. A lane whose CI
  check judges more declares `scope:` in `tools.yaml`: `changed-files` keeps
  every finding in a changed file (Biome), `whole-tree` keeps every finding
  (Core's Semgrep gate).
- **CodeQL.** CI's analysis is diff-informed: a data-flow result counts when
  its source or sink is in the diff. `findings.py` keeps every flow location for
  that reason; checking only the reported sink line misses real alerts.
  Blocks on error level or security-severity ≥ 7.0, like code scanning.
- **Semgrep (`semgrep-l9`) is Analyze (central Core)'s SDK gate.** It runs the
  pinned `l9-ci` SDK the way `org-ci.yml` does: `semgrep run` then
  `gate evaluate`. The SDK source sits at `.l9/runtime/sdk/source` in the
  snapshot, because Semgrep names each rule by its config path and Core's policy
  keys read `l9.runtime.sdk.source.l9_ci...`. Core's own bundled governance for
  `pr_fast` (strictness, requiredness, `semgrep-policy.yaml`, identity maps) is
  read from l9-ci-core and staged under `.l9/runtime/org-governance`; Core never
  uses this repository's `.github/governance` files for this gate. Core judges
  the whole tree, so the lane blocks on every finding Core's gate blocks. The
  verdict is `gate evaluate`'s exit (0 pass, 1 fail, 6 incomplete): `semgrep
  run` exits 0 even when semgrep wrote no report. Behind an HTTPS proxy the SDK
  hands semgrep only PATH/HOME/TMP*, so a mode-0700 shim first on PATH restores
  the proxy settings for that one process and is deleted when the lane ends.
- **Semgrep Pro.** `semgrep ci --dry-run` fetches the org policy with the token
  and creates no scan. Advisory until probe U1 proves parity with the
  `semgrep-cloud-platform/scan` check.
- **Biome** blocks: Analyze (central Core) runs `biome ci` in blocking mode with
  its locked 2.5.8 binary, so any finding in a changed file blocks.
- **New tools** (actionlint, zizmor, shellcheck, yamllint) block on error level
  on changed lines only, so existing debt never blocks.

## Parity proof (2026-09-24)

| Commit | CI verdict (CodeQL) | Local `run.py --gate` |
|---|---|---|
| `745a1b06` (#659 before its fix) | 3 new high alerts: `py/clear-text-logging-sensitive-data` at `ops/secrets/infisical_cli_login.py:73`, `ops/secrets/session_start_secrets.py:228`, `ops/scripts/session_start_runtime_report.py:933` | `blocking=3`, the same rule at the same three lines, nothing else |
| `29c767df` (#659 fixed) | CodeQL green | `blocking=0`, exit 0 |

Both runs: 4 CPU container, ~2.5 min wall-clock (CodeQL dominates). That scan
stays on CI. `make pr` does not start it, and the push hook does not wait on it.

### Core Semgrep gate (2026-11-06)

| Commit | CI verdict (Analyze (central Core)) | Local `semgrep-l9` |
|---|---|---|
| `0f3612da` (#829 before its fix) | `gate-result.json` status fail, 7 blocking: `hardcoded-credential` at `ops/memory/agent_assertion.py:34,39`, `ops/scripts/validate_legacy_doctrine_residue.py:229`, `ops/secrets/infisical_cli_login.py:60`, `ops/secrets/login_registry.py:18,20`; `sql-string-format` at `ops/memory/store_compat.py:96` | `blocking=7`, the same rules at the same seven lines, ~71 s |
| `3cd61988` (main) | green | `blocking=0`, ~69 s |

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
python3 ops/ci_parity/install.py --check      # 11/11 OK at pinned versions
python3 ops/ci_parity/run.py --status         # receipts + in-flight run
python3 ops/ci_parity/run.py --gate HEAD      # manual scan of every applicable lane
python3 ops/ci_parity/run.py --gate HEAD --lanes biome,semgrep-l9   # what make pr runs
python3 ops/ci_parity/validate_manifest.py --remote   # pins still match l9-ci-core main
python3 ops/ci_parity/sonar_status.py --auto  # SonarCloud for this branch's PR
L9_CI_PARITY=0                                # session kill switch
```

## Re-pinning

When `validate_manifest.py` reports a moved CI pin: read the CI log for the
version it now runs, update `version`, `url`, `sha256` and `ci_ref` in
`tools.yaml` together, then `install.py` and re-run the parity replay.
