---
name: Claude binary resolution fix
overview: "Fix exit-127 \"claude: not found\" when the Cursor plugin launches scripts/claude-deepseek.sh by resolving the claude binary explicitly (Option B), independent of the caller's PATH."
todos:
  - id: edit-script
    content: Replace exec claude with CLAUDE_BIN resolution block in scripts/claude-deepseek.sh
    status: completed
  - id: validate
    content: Run bash -n, the env -i minimal-PATH simulation, and the CLAUDE_BIN negative test
    status: completed
  - id: user-verify
    content: Have user relaunch Claude Code via Cursor plugin to confirm fix
    status: completed
isProject: false
---

# Fix claude-deepseek.sh binary resolution (Option B)

## Objective

The Cursor Claude Code plugin launches [scripts/claude-deepseek.sh](scripts/claude-deepseek.sh) with a minimal environment (no zsh profile), so `PATH` lacks `/opt/homebrew/bin` and the nvm bin dir. Line 38 (`exec claude "$@"`) fails with exit 127. Make the script resolve the `claude` binary explicitly so it works regardless of the caller's `PATH`.

## Ground truth (verified)

- `claude` exists at `/opt/homebrew/bin/claude` and `~/.nvm/versions/node/v22.17.0/bin/claude` (confirmed via `which -a claude`).
- Both are symlinks to `@anthropic-ai/claude-code/bin/claude.exe`, a native Mach-O arm64 executable (confirmed via `file`) — no `node`-on-PATH dependency, so resolving the binary alone is sufficient.
- The two installs differ in age (Homebrew: Aug 14; nvm: Jul 21), so candidate ordering below is deliberate: Homebrew before nvm.
- The script currently ends with:

```36:38:scripts/claude-deepseek.sh
echo "Claude Code -> ${ANTHROPIC_BASE_URL} (${ANTHROPIC_MODEL})"
cd "$ROOT"
exec claude "$@"
```

## Change (single file)

Replace `exec claude "$@"` in [scripts/claude-deepseek.sh](scripts/claude-deepseek.sh) with a resolution block:

```bash
# The Cursor plugin launches this wrapper with a minimal PATH that lacks
# Homebrew/nvm dirs, so resolve the claude binary explicitly.
CLAUDE_BIN="${CLAUDE_BIN:-}"
if [[ -z "$CLAUDE_BIN" ]]; then
  for candidate in \
    "$(command -v claude 2>/dev/null || true)" \
    /opt/homebrew/bin/claude \
    "$HOME"/.nvm/versions/node/*/bin/claude \
    "$HOME/.local/bin/claude" \
    /usr/local/bin/claude; do
    if [[ -n "$candidate" && -x "$candidate" ]]; then
      CLAUDE_BIN="$candidate"
      break
    fi
  done
fi

if [[ -z "$CLAUDE_BIN" || ! -x "$CLAUDE_BIN" ]]; then
  echo "ERROR: claude binary not found or not executable (CLAUDE_BIN='${CLAUDE_BIN:-}'). Install Claude Code or fix CLAUDE_BIN." >&2
  exit 127
fi

echo "claude binary: ${CLAUDE_BIN}"
exec "$CLAUDE_BIN" "$@"
```

Design points:
- `CLAUDE_BIN` env override wins, so the user (or plugin config) can pin a specific binary — but the final guard also checks `-x`, so a stale/typo'd override fails closed with a clear message instead of an opaque bash exec error.
- `command -v claude` is tried first, so a normal terminal launch behaves exactly as today.
- Homebrew is tried before nvm because it is the more recently updated install (verified above).
- The nvm glob survives Node version upgrades (no hardcoded `v22.17.0`). Glob expansion is lexicographic, so with multiple nvm Node versions the first match wins — acceptable because Homebrew outranks nvm here and `CLAUDE_BIN` can pin exactly.
- Echoing the resolved path makes any future misresolution diagnosable from the plugin error output.
- Fail-closed with the same 127 exit code if nothing usable is found.
- No secrets touched; the env-loading and DeepSeek routing logic above line 36 is unchanged, preserving the repo rule that this wrapper is the only sanctioned Claude Code entry point.

## Scope out

- No change to `.env.local`, `claudeCode.claudeProcessWrapper` setting, or the governance copy at `~/.cursor-governance/scripts/claude-deepseek.sh`.
- No PATH mutation (Option A rejected per user choice).

## Validation

1. `bash -n scripts/claude-deepseek.sh` — syntax check.
2. Simulate the plugin's stripped environment: `env -i HOME="$HOME" PATH=/usr/bin:/bin bash scripts/claude-deepseek.sh --version` — must print the routing banner, the resolved `claude binary:` path (expected `/opt/homebrew/bin/claude`, since `command -v` fails under the stripped PATH and the loop falls through to the Homebrew candidate — this exercises the exact failure path from the bug), and a Claude Code version.
3. Negative test (fail-closed guard): `CLAUDE_BIN=/nonexistent bash scripts/claude-deepseek.sh --version` — must print the ERROR line and exit 127, not an opaque bash exec error.
4. Normal-terminal run: `scripts/claude-deepseek.sh --version` — unchanged behavior, resolved via `command -v`.
5. User relaunches Claude Code from the Cursor plugin to confirm the original error is gone (only step needing the user).

## Risks / stress test

- Node-script dependency risk: eliminated with evidence — both installs are native arm64 executables, so no `node` is needed on `PATH` at exec time.
- Glob matches multiple nvm versions: lexicographic first match wins; low impact since Homebrew outranks nvm in the loop and `CLAUDE_BIN` can pin exactly.
- `set -e` interaction: the `command -v ... || true` guard prevents an early exit when `claude` is absent from PATH; the glob candidate is a literal non-matching string when no nvm install exists, rejected by the `-x` check.
- Steps 2–4 launch only `claude --version`, which is read-only and does not bill Anthropic (DeepSeek routing env vars are exported before exec).

## Rollback

Single-file change. The script is currently untracked (`??` in git status), so `git checkout` cannot restore it — copy it aside (`cp scripts/claude-deepseek.sh scripts/claude-deepseek.sh.bak`) before editing, and delete the backup after validation passes.

## Unknowns / residual

- The exact `PATH` the Cursor plugin uses is unobserved; irrelevant after the fix since resolution no longer depends on it. If the plugin error persists post-fix, verify `claudeCode.claudeProcessWrapper` actually points at this script (per repo rule).
- Duplicate `claude` installs (Homebrew + nvm, different versions) are pre-existing entropy; consolidation is out of scope but recommended separately.
