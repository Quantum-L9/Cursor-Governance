---
name: Full PR Remediation Plan
overview: "Close the stale, conflicting PR #18 and recover only its still-valid content (pr-repair pipeline + browser-copilot spec, with 3 validated bug fixes) into a fresh, clean PR against current main; separately, push the one validated SonarCloud nit fix to the already-green PR #27."
todos:
  - id: close-pr18
    content: "Post closing comment + gh pr close 18 (root cause: committed .venv-precommit/ + broken gitlinks)"
    status: pending
  - id: branch-recovery
    content: Create feat/pr-repair-pipeline-recovery off main; copy in pr-repair/ + browser_copilot spec from PR18 head
    status: pending
  - id: fix-connectors
    content: Delete dead pr_repair/connectors/ package (0.2.0 draft shadowing the real 0.3.0 connectors.py module)
    status: pending
  - id: fix-dedupe
    content: Fix dedupe.py severity comparison to use enum rank instead of string value
    status: pending
  - id: fix-repair-ready
    content: Fix pipeline.py repair_ready to require candidate_count > 0
    status: pending
  - id: validate-recovery
    content: Run ci/validate_repo.py, validate_counts.py, check_secrets.py, py_compile, and pr-repair's own pytest suite locally
    status: pending
  - id: open-new-pr
    content: "Push feat/pr-repair-pipeline-recovery and open PR against main, linking PR #18"
    status: pending
  - id: fix-pr27-sonar
    content: Apply deploy.sh:116 local-variable fix on chore/remove-venture-forge-toolbox, push, verify all 8 checks stay green
    status: pending
isProject: false
---

# Full PR Remediation Plan — `Quantum-L9/igorbot`

Both open PRs have now been fully investigated (CI logs, GraphQL review threads, SonarCloud API via the `openclaw-igorbot/sonarcloud` AWS secret, and direct inspection of the actual PR-head source). This plan is the concrete execution path for both, per your decision to **close and recover** PR #18.

## PR #18 — close, recover the real content into a new PR

**Verified facts (via `gh api pulls/18/files --paginate`, git object inspection on the fetched PR head, and `git ls-tree origin/main`):**

| Category | Files | Disposition |
|---|---|---|
| `.venv-precommit/` (vendored virtualenv) | 856 | **Never recover** — accidentally committed, root cause of the Config Coherence / Pre-commit Hooks / SonarCloud gate failures reported earlier |
| `workspace/output/boostyourclaim_ops_runs/...` (scraped/generated client output, unrelated to IgorBot) | 28 | **Never recover** |
| `graphiti/neo4j-data/.../fulltext-1.0/...` (binary Neo4j Lucene index segments) | 24 | **Never recover** — binary DB internals |
| `workspace/.heartbeat/*.done`, `workspace/memory/*.md`, `workspace/tmp/*`, logs | 30 | **Never recover** — generated runtime state, superseded by current `memory-bank/` system |
| `workspace/Constellation.Gate.Node`, `workspace/platform-state-service`, `workspace/integrations/gitguardian-telegram-relay` | 3 | **Never recover** — confirmed via `git ls-tree` mode `160000`: dangling git **submodule/gitlink** references with no `.gitmodules` entry. This is what caused `fatal: No url found for submodule path ...` in the CI logs. Actively broken, not content. |
| `.openclaw/shared/CRITICALRULES.md`, `TRIGGERRULES.md`, `CLAUDE.md`, `bin/secure-env.sh`, `config/openclaw.json`, `docs/SKILLS-REFERENCE.md`, `workspace/AGENTS.md`, `workspace/MEMORY.md`, `workspace/SKILLS.md`, `.github/workflows/l9-validate.yml`, `workspace/skills/graphiti/*`, `workspace/skills/skill_creator/*` | 29 (all `modified`, not `added`) | **Never recover** — these are 3-month-old deltas to files that have independently evolved on `main` since April. Per "existing code is source of truth," `main`'s current versions win; blindly reapplying stale diffs risks regressing since-fixed governance files. |
| `workspace/skills/abacus_platform/`, `workspace/ai_platform_union_orchestration_spec_v1.0.0.yaml` | 2 | **Skip — already on `main`** (confirmed via `git ls-tree origin/main`), so nothing to recover |
| **`workspace/IgorBot-Shared/pr-repair/`** (self-contained pipeline: `src/pr_repair/*`, `tests/*`, `README.md`, `README_PR_REPAIR.md`, `DEFERRED.md`, `pr_repair_spec_v1.2.0.yaml`, `oir_*.txt`) | 39 (all `added`, doesn't exist on `main`) | **Recover, with fixes** (below) |
| `pr_repair_phase2_bundle.zip` (10KB, inside pr-repair dir) | 1 | **Decision needed** — binary bundle artifact, contents likely reconstructable from the source dir itself. Default recommendation: exclude (no binary blobs), but flag to you before finalizing. |
| **`workspace/igorbot_browser_copilot_v1_spec_v1.0.0.yaml`** (proposed product spec, not on `main`) | 1 | **Recover as-is** |

**3 validated Codex review findings to fix while recovering `pr-repair/`** (all confirmed against actual PR-head source, not just the bot's claim):

1. **`src/pr_repair/pipeline.py:12`** — `from .connectors import ConnectorResponse` fails because `pr_repair/connectors/` (a package) shadows `pr_repair/connectors.py` (a module) per Python import resolution, and the package's `__init__.py` never exports `ConnectorResponse`.
   - **Root cause confirmed**: the `connectors/` package (`github.py`, `coderabbit.py`, `codecov_cloud.py`) is an **older draft** — `User-Agent: "pr-repair/0.2.0"` — of the exact same connectors that are fully and more completely implemented in the flat `connectors.py` module (`User-Agent: "pr-repair/0.3.0"`, plus `ConnectorResponse`/`BaseHTTPConnector` that the package draft never got).
   - **Fix**: delete the entire `pr_repair/connectors/` package (4 files) — it's dead, superseded code shadowing the real implementation, not a re-export gap to patch.
2. **`src/pr_repair/dedupe.py:16`** — `finding.severity.value > existing.severity.value` compares `Severity(str, Enum)` values (`low/medium/high/critical`) lexicographically, so `"medium" > "high"` is `True` and a lower-severity duplicate can win.
   - **Fix**: compare by enum ordinal/rank (e.g. a fixed `Severity` order tuple) instead of the raw string value.
3. **`src/pr_repair/pipeline.py:88`** — `repair_ready=prs_scanned > 0 and candidate_count >= 0` is always true once any PR is scanned, since a count is never negative.
   - **Fix**: `candidate_count >= 0` → `candidate_count > 0`.

**Execution steps:**

1. Post a closing comment on PR #18 referencing the CI/Sonar root cause (accidentally committed `.venv-precommit/` + broken gitlinks) and the new PR that recovers the real content; `gh pr close 18`.
2. Create branch `feat/pr-repair-pipeline-recovery` off current `main`.
3. Copy in `workspace/IgorBot-Shared/pr-repair/` (minus the zip, pending your call) and `workspace/igorbot_browser_copilot_v1_spec_v1.0.0.yaml` from the fetched PR #18 head (`git show pr18-review:<path>`), apply the 3 fixes above.
4. Run local gates before opening: `python3 ci/validate_repo.py`, `ci/validate_counts.py`, `ci/check_secrets.py`, JSON/YAML validity, `python3 -m py_compile` on the new files, and `pytest workspace/IgorBot-Shared/pr-repair/tests/` (not a CI-enforced gate today, but worth running for confidence since it exists).
5. Push branch, open PR against `main` with a description linking back to PR #18 and listing the 3 fixes.

## PR #27 — apply the one validated SonarCloud fix

**File:** `deploy.sh:116` — `command_exists() { command -v "$1" >/dev/null 2>&1; }`
**Rule:** `shelldre:S7679` (MAJOR / MEDIUM maintainability, non-blocking — Quality Gate already passes)
**Fix:** `command_exists() { local target="$1"; command -v "$target" >/dev/null 2>&1; }`

Push this single-line fix to the existing branch `chore/remove-venture-forge-toolbox`, re-verify all 8 existing green CI checks stay green (Architecture & Wiring, Config Coherence, New Skill Wiring, Pre-commit Hooks, Syntax & Format, SonarCloud, CodeQL ×2), no commit/push beyond this one line.

## Gate

Per this repo's git governance rules, nothing above executes without your explicit go-ahead at each commit/push point (closing PR #18, pushing the new branch, opening the new PR, pushing to PR #27's branch) — this plan sets up exactly what will happen so you can approve it as a whole or step by step.
