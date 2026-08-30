# Setup script — paste-ready

**Field:** claude.ai/code → environment → **Setup script**
**Revision:** `2026-08-29.3` · **Checksum:** `e94e1da822905021`
**Applies to:** NEW sessions only.

Source of truth: `environment/agents/adapters/claude-code/web/setup.bootstrap.sh`.
Paste the stub, never `web/setup.sh`. The field is a copy, not a live link, so a
full script pasted into it drifts from `main` on every edit; the stub is stable
and hands off to `web/setup.sh` from the governance clone, which means setup.sh
changes reach every new session with no re-paste.

## Before you paste — copy the current field out first

A field cannot be read back from inside the sandbox, so whatever is in it now is
the only copy. If `verify_account_env.py` reports the field is **ahead** of HEAD,
it is running bootstrap code that exists in no commit: copy it out, diff it
against the stub below, and commit anything it added. Pasting over an ahead field
destroys that code silently.

```bash
python3 environment/agents/adapters/claude-code/verify_account_env.py   # names the direction
```

## Paste this

Copy **only** the script itself: the first line of the block below is
`#!/usr/bin/env bash`, immediately followed by an `L9-PASTE-BEGIN` marker, and
the last is an `L9-PASTE-END` marker just after `exit 0`. Do **not** include
the triple-backtick fence lines that open and close the block, this heading, or
the prose that follows the block.

Selecting a rendered page accurately is fiddly, so prefer copying the raw file —
it is byte-identical to the block below and carries no fence to catch:

```bash
cat environment/agents/adapters/claude-code/web/setup.bootstrap.sh
```

> **Why the fence lines matter.** A markdown fence is three backticks. Bash reads
> that as an empty command substitution plus one leftover backtick, which opens a
> substitution that swallows the entire stub. Measured on 2026-08-22, pasting the
> fence executed the stub's English comments as shell commands, ran `git clone`
> with an empty target directory, and ended in `exit 127` with the environment
> half-built and no line naming the cause. The stub is now backtick-free and
> detects the contaminated paste itself, refusing with a `FATAL` line that names
> the fence — but the environment still will not build until you re-paste
> without the fence lines.

```bash
#!/usr/bin/env bash
# L9-PASTE-BEGIN — the Setup script field starts at the line above (#!/usr/bin/env bash).
# ---------------------------------------------------------------------------
# L9 Claude Code cloud Setup script — startup stub (Web · Mobile · --cloud).
#
# THIS FILE CONTAINS NO BACKTICKS, DELIBERATELY. See tests/test_account_drift_and_platform_blocks.py.
#
# Paste THIS into claude.ai/code -> environment -> Setup script. Clones governance
# @ main, then execs web/setup.sh from that clone. Prefer lib/cloud_account_env.sh
# when the clone carries it; until then a compact legacy fallback runs here.
#
# Companion fields: web/environment.env.example · web/network-policy.md
# Docs: https://code.claude.com/docs/en/cloud-environments
# ---------------------------------------------------------------------------
set -uo pipefail

# --- 0) Paste-integrity guard ----------------------------------------------
_l9_self="${BASH_SOURCE[0]:-$0}"
_l9_fence="$(printf '\140\140\140')"
if [ -r "$_l9_self" ]; then
  if grep -qF "$_l9_fence" "$_l9_self"; then _l9_contaminated=1; else _l9_contaminated=0; fi
else
  if [ "${BASH_SUBSHELL:-0}" -ne 0 ]; then _l9_contaminated=1; else _l9_contaminated=0; fi
fi
unset _l9_self _l9_fence

if [ "$_l9_contaminated" -ne 0 ]; then
  printf '%s\n' \
    'L9 bootstrap FATAL: the Setup script field contains markdown fence lines.' \
    'L9 bootstrap FATAL:   Re-paste ONLY L9-PASTE-BEGIN through L9-PASTE-END — no fences.' >&2
  exit 2
fi
unset _l9_contaminated

L9_STUB_REVISION="2026-08-29.3"
export L9_STUB_REVISION

warn() { printf 'L9 bootstrap WARN: %s\n' "$*" >&2; }
note() { printf 'L9 bootstrap: %s\n' "$*"; }

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Compact fallback until origin/main carries lib/cloud_account_env.sh (chicken-egg
# with a pasted stub ahead of merge). Must not name retired broker env vars here.
_l9_legacy_normalize() {
  export L9_GOVERNANCE_DIR="$GOV_DIR"
  export L9_GOVERNANCE_SURFACE="claude-code"
  : "${GRAPHITI_MCP_URL:=https://memory.quantumaipartners.com/graphiti/mcp}"
  export GRAPHITI_MCP_URL
  local k v
  for k in SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN \
           INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD \
           GRAPHITI_MCP_TOKEN AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN \
           L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN; do
    v="${!k:-}"
    [ -n "$v" ] || continue
    [ "$v" = "proxy-injected" ] && continue
    warn "$k is PROHIBITED on this surface; unsetting"
    unset "$k"
  done
}

_l9_legacy_session_env() {
  local f="$HOME/.l9/cloud-session.env"
  mkdir -p "$(dirname "$f")"
  {
    echo "# Written by L9 setup.bootstrap.sh (legacy fallback) — do not edit."
    echo "export L9_STUB_REVISION=$(printf %q "$L9_STUB_REVISION")"
    echo "export L9_GOVERNANCE_DIR=$(printf %q "$GOV_DIR")"
    echo "export L9_GOVERNANCE_SURFACE=claude-code"
    echo "export GRAPHITI_MCP_URL=$(printf %q "${GRAPHITI_MCP_URL:-}")"
    echo "unset L9_MEMORY_HTTP_URL L9_MEMORY_CLIENT_TOKEN L9_MEMORY_HTTP_TOKEN"
    echo "unset GRAPHITI_MCP_TOKEN INFISICAL_CLIENT_SECRET INFISICAL_TOKEN INFISICAL_PASSWORD"
    echo "unset SONAR_TOKEN SONARCLOUD_TOKEN SEMGREP_APP_TOKEN"
    echo "unset AWS_SECRET_ACCESS_KEY AWS_ACCESS_KEY_ID AWS_SESSION_TOKEN"
  } > "$f"
  if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    cat "$f" >> "$CLAUDE_ENV_FILE"
  else
    for p in "$HOME/.bashrc" "$HOME/.profile"; do
      [ -f "$p" ] || touch "$p"
      grep -qF 'cloud-session.env' "$p" 2>/dev/null \
        || printf '%s\n' '. "$HOME/.l9/cloud-session.env"  # L9 governed session env' >> "$p"
    done
  fi
}

# --- 1) Governance SSOT ----------------------------------------------------
GOV_DIR="$HOME/.cursor-governance"
GOV_REMOTE="${L9_GOVERNANCE_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"

mkdir -p "$(dirname "$GOV_DIR")"
if [ -d "$GOV_DIR/.git" ]; then
  git -C "$GOV_DIR" remote set-url origin "$GOV_REMOTE" 2>/dev/null || true
  if git -C "$GOV_DIR" fetch --depth 1 origin "$GOV_BRANCH" 2>/dev/null; then
    git -C "$GOV_DIR" checkout -f -B "$GOV_BRANCH" "origin/$GOV_BRANCH" 2>/dev/null \
      || git -C "$GOV_DIR" reset --hard "origin/$GOV_BRANCH" 2>/dev/null \
      || warn "could not reset governance clone to origin/$GOV_BRANCH"
  else
    warn "governance fetch failed — reusing existing clone (may be stale)"
  fi
else
  rm -rf "$GOV_DIR"
  git clone --depth 1 --branch "$GOV_BRANCH" "$GOV_REMOTE" "$GOV_DIR" || {
    warn "governance clone FAILED — allowlist github.com (see web/network-policy.md)"
    exit 1
  }
fi

L9_CLOUD_ENV_LIB="$GOV_DIR/environment/agents/adapters/claude-code/lib/cloud_account_env.sh"
SETUP="$GOV_DIR/environment/agents/adapters/claude-code/web/setup.sh"
if [ ! -f "$SETUP" ]; then
  warn "governance clone incomplete — missing web/setup.sh at $SETUP"
  warn "  clone HEAD: $(git -C "$GOV_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
  exit 1
fi

if [ -f "$L9_CLOUD_ENV_LIB" ]; then
  # shellcheck source=../lib/cloud_account_env.sh
  source "$L9_CLOUD_ENV_LIB"
  l9_normalize_cloud_account_env
else
  warn "lib/cloud_account_env.sh not on clone yet — using bootstrap legacy normalize"
  _l9_legacy_normalize
fi

L9_GOVERNANCE_BOOTSTRAPPED=1 bash "$SETUP"
SETUP_RC=$?

if [ -f "$L9_CLOUD_ENV_LIB" ]; then
  l9_write_cloud_session_env "$SETUP_RC" || true
  l9_report_cloud_memory_posture
else
  _l9_legacy_session_env || true
  note "memory front door: ${GRAPHITI_MCP_URL:-unset} (no bearer)"
  note "capability plane: RETIRED (never shipped)"
fi

if [ "$SETUP_RC" -ne 0 ]; then
  warn "cloud bootstrap FAILED — web/setup.sh exited $SETUP_RC"
  warn "  see ~/.l9/claude/bootstrap-state.json"
  exit "$SETUP_RC"
fi
note "cloud bootstrap complete — governance at $GOV_DIR ($GOV_BRANCH)"
exit 0
# L9-PASTE-END — the Setup script field ends at the line above (exit 0).
```

## Verify the paste took

Start a NEW session, then:

```bash
grep L9_STUB_REVISION ~/.l9/cloud-session.env      # expect 2026-08-29.3
make claude-env                                    # structural + RUNTIME verdicts
```

If `~/.l9/cloud-session.env` does not exist at all, the stub did not run to
completion. Read the environment's setup log and look for a line beginning
`L9 bootstrap FATAL:` — the paste-integrity guard names the fence contamination
explicitly rather than leaving you to read a wall of "command not found".

The stub records its own revision into `~/.l9/cloud-session.env` on every run, so
a later session can answer "is the pasted stub current?" without reading the field.
