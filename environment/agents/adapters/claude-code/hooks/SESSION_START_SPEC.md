# SESSION_START_SPEC — Claude Code governance bootstrap

**Status:** authoritative contract for `session_start_claude_governance.sh`
**Profile SSOT:** `ops/autonomy/surface_profile.yaml`
**Install:** `ops/scripts/reconcile_claude_settings.py` copies this script into
`<repo>/.claude/hooks/` as a **committed file** (Mobile/Web survival).

## Hard constraints

1. **Fail-open** — always exit 0; never block a session.
2. Resolve governance only at `$HOME/.cursor-governance` (ignore other `L9_GOVERNANCE_DIR`).
3. Emit Claude SessionStart JSON envelope with `additionalContext`.
4. **Mobile-safe** — committed consumer copy must not require `~/.cursor`.
5. **No new brains** under `environment/agents/adapters/claude-code/` — call `ops/autonomy/*` and
   `environment/program-execution/peer_execution/autonomy/bootstrap.py` only.
6. Reconcile (`reconcile_claude_settings`) is **install-time**, not SessionStart-critical.

## Must emit when governance found

1. Governance rev (branch@sha) — on `CLAUDE_CODE_REMOTE=true` the ephemeral
   governance clone is refreshed from `origin/main` first (fetch, reset, record
   exact revision); on local/Desktop the checkout is **never reset** — report
   revision + drift against origin/main only.
2. Authority order including Autonomy Surface Profile
3. Verbatim Profile `session_start_block` via `ops/autonomy/profile_loader.py` (stdlib-only extract; no PyYAML required on SessionStart path)
4. Read-only autonomy `bootstrap.py` context when available
5. Skill-router readiness hint (`ops/generated/skill-registry.json`)
6. **L9 Claude environment status block** projected from
   `~/.l9/claude/bootstrap-state.json` (schema `l9.claude-bootstrap.v1`, written
   by `install.sh`): surface, execution (anthropic-cloud / local), governance
   rev, bootstrap, settings, capability broker, memory, skills, rules. An
   absent receipt is stated as such ("run `make claude-install` once"), never
   invented.
7. On cloud sessions: a session-deps line from `hooks/session_deps_cloud.sh`
   (fingerprint-cached toolchain PER REPOSITORY + pre-commit warm; bounded
   budget, self-detaches to background on expiry).

## Acceptance

- stdout is one JSON object with `hookSpecificOutput.hookEventName=SessionStart`
- exit code 0 even when gov missing
- When gov present, context contains `Autonomy Velocity Doctrine` (from Profile)
- Profile block sha256 matches `profile_loader.block_sha256()`
- When a bootstrap receipt exists, context contains the `L9 Claude environment`
  block with the receipt's per-step statuses; when absent, the absence is named

## Non-goals

- Skill scoring / Graphiti client / plugin classify / autonomy scheduler
- Blocking a session on a dependency install: the cloud session-deps helper is
  fingerprint-cached and budget-bounded, and the hook stays fail-open
