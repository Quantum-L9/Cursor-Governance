#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# L9 Governance — Claude Code SessionStart bootstrap (CLI · Web · Mobile).
#
# Mobile-safe by construction: git-tracked, no ~/.cursor dependency, no editor
# machine state. Locates the governance clone, surfaces resume context, injects
# Autonomy Surface Profile doctrine, compiles bounded-autonomy campaign state,
# and emits a Claude Code SessionStart `additionalContext` JSON blob on stdout.
#
# Registered from .claude/settings.json (see settings.template.json). Copy this
# file to <consumer-repo>/.claude/hooks/ and COMMIT it — on Claude Code Web and
# Mobile only committed files survive the clone into the sandbox.
#
# Contract: FAIL-OPEN. A hook must never block a session. Every failure degrades
# to a smaller context blob; the script always exits 0.
#
# Spec: environment/agents/adapters/claude-code/hooks/SESSION_START_SPEC.md
# Profile SSOT: ops/autonomy/surface_profile.yaml
# ---------------------------------------------------------------------------
set -uo pipefail

resolve_governance_dir() {
  local d="$HOME/.cursor-governance"
  if [ -n "${L9_GOVERNANCE_DIR:-}" ] && [ "${L9_GOVERNANCE_DIR}" != "$d" ]; then
    : # ignored — shared contract is always $HOME/.cursor-governance
  fi
  [ -f "$d/CANONICAL_LAW.md" ] && { printf '%s' "$d"; return 0; }
  return 1
}

json_escape() {
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/\\n}
  s=${s//$'\r'/}
  s=${s//$'\t'/\\t}
  printf '%s' "$s"
}

emit() {
  local ctx
  ctx=$(json_escape "$1")
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ctx"
  exit 0
}

# Cursor also loads projected .claude/settings.json in this repo. This hook is
# Claude Code SessionStart only. Running it under Cursor scores that session
# with cloud account-field drift, broker probes, and never_ran installer
# receipts that cannot pass here. Skip unless a Claude Code runtime marker is
# present. CURSOR_AGENT alone is not Claude Code.
_l9_claude_runtime=0
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] && _l9_claude_runtime=1
[ -n "${CLAUDECODE:-}" ] && _l9_claude_runtime=1
[ -n "${CLAUDE_CODE_ENTRYPOINT:-}" ] && _l9_claude_runtime=1
[ -n "${CLAUDE_CODE_SESSION_ID:-}" ] && _l9_claude_runtime=1
if [ "$_l9_claude_runtime" -eq 0 ]; then
  emit ""
fi
unset _l9_claude_runtime

WORKSPACE="${CLAUDE_PROJECT_DIR:-$PWD}"
LINES=()
LINES+=("L9 Governance — Claude Code session")
LINES+=("workspace: $WORKSPACE")

# --- Cloud-only governance refresh (CLAUDE_CODE_REMOTE=true) -----------------
# Anthropic documents CLAUDE_CODE_REMOTE=true as the supported discriminator
# for cloud-session-only setup. In cloud, the governance clone is an ephemeral
# environment artifact: refresh it from origin/main so every session starts on
# the current tip, and record the exact revision. On a local developer
# checkout (CLI / Desktop) NEVER reset — inspect and report only.
# The receipt is JSON with a UTC timestamp and a TTL (INV-2). It used to be the
# single word `fresh` plus a short SHA — a claim with no expiry, so a receipt
# written at environment-build time still read `fresh 941ab77` days later while
# the clone sat four commits behind main (audit B-05). A receipt that cannot go
# stale is a receipt that always reads healthy. `state` here is the AT-WRITE
# value; every reader recomputes it from refreshed_at + ttl_seconds and from the
# recorded SHAs (see ops/scripts/governance_refresh_receipt.py).
CLOUD_REFRESH_RECEIPT="${L9_GOV_REFRESH_RECEIPT:-$HOME/.l9/claude/gov-refresh.json}"

# Written with printf rather than through python3 on purpose: this hook must
# still leave a trace on a runtime where no interpreter is usable, which is
# precisely the runtime whose staleness we are trying to detect.
# Any value interpolated below is squashed to a single token first. A receipt
# writer must not be able to emit invalid JSON no matter what git hands it.
json_token() { printf '%s' "$1" | tr -d '\n\r\t"\\' | head -c 64; }

write_refresh_receipt() {
  local outcome="$1" local_sha="$2" origin_sha="$3" behind="$4" state="$5" ts
  outcome="$(json_token "$outcome")"
  local_sha="$(json_token "$local_sha")"
  origin_sha="$(json_token "$origin_sha")"
  state="$(json_token "$state")"
  case "$behind" in (''|*[!0-9-]*) behind=-1 ;; esac
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 'unknown')"
  mkdir -p "$(dirname "$CLOUD_REFRESH_RECEIPT")" 2>/dev/null || return 0
  printf '{\n' > "$CLOUD_REFRESH_RECEIPT"
  printf '  "schema": "l9.governance-refresh.v1",\n' >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "outcome": "%s",\n' "$outcome" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "local_sha": "%s",\n' "$local_sha" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "origin_sha": "%s",\n' "$origin_sha" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "refreshed_at": "%s",\n' "$ts" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "ttl_seconds": %s,\n' "${L9_GOV_REFRESH_TTL:-3600}" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "commits_behind": %s,\n' "$behind" >> "$CLOUD_REFRESH_RECEIPT"
  printf '  "state": "%s"\n' "$state" >> "$CLOUD_REFRESH_RECEIPT"
  printf '}\n' >> "$CLOUD_REFRESH_RECEIPT"
}

# A depth-1 clone has no ancestry to walk, so a numeric distance is frequently
# uncomputable. Report -1 for "unknown" rather than 0, which would read as
# up-to-date — the same class of lie this section is removing.
commits_behind() {
  git -C "$1" rev-list --count "$2..$3" 2>/dev/null || echo -1
}

if [ "${CLAUDE_CODE_REMOTE:-}" = "true" ]; then
  if GOV=$(resolve_governance_dir); then
    GOV_REMOTE="${L9_GOVERNANCE_REMOTE:-https://github.com/Quantum-L9/Cursor-Governance.git}"
    GOV_BRANCH="${L9_GOVERNANCE_BRANCH:-main}"
    # The reset below is `checkout -f`, which DISCARDS uncommitted work and moves
    # HEAD off whatever branch is checked out. That is correct for the ephemeral
    # cloud clone it is written for, and destructive for anything else. It ran
    # unguarded, so a governance checkout carrying in-flight work — reachable
    # here whenever $HOME/.cursor-governance resolves to a working clone rather
    # than the throwaway one — lost that work silently, HEAD included. The reset
    # only ever has something to do on a clean clone, so refusing a dirty one
    # costs the intended path nothing and makes the destructive case impossible.
    # TRACKED changes only. `checkout -f` discards tracked modifications and
    # staged content — what this session actually lost — but leaves untracked
    # files alone, so counting them would refuse a reset that was never
    # dangerous and strand the ephemeral clone (a fresh one legitimately
    # carries untracked bootstrap residue).
    gov_dirty=$(git -C "$GOV" status --porcelain --untracked-files=no 2>/dev/null | head -c 1)
    if [ -n "$gov_dirty" ]; then
      local_sha=$(git -C "$GOV" rev-parse --verify --quiet HEAD 2>/dev/null || echo 'unknown')
      write_refresh_receipt reset-skipped-dirty "$local_sha" unknown -1 stale
      LINES+=("governance refresh: WARN $GOV has uncommitted changes — reset SKIPPED (refusing to discard in-flight work)")
    elif git -C "$GOV" fetch --depth 1 origin "$GOV_BRANCH" >/dev/null 2>&1; then
      remote_sha=$(git -C "$GOV" rev-parse --verify --quiet FETCH_HEAD 2>/dev/null || echo 'unknown')
      if git -C "$GOV" checkout -f -B "$GOV_BRANCH" "origin/$GOV_BRANCH" >/dev/null 2>&1; then
        local_sha=$(git -C "$GOV" rev-parse --verify --quiet HEAD 2>/dev/null || echo 'unknown')
        write_refresh_receipt fetched "$local_sha" "$remote_sha" \
          "$(commits_behind "$GOV" HEAD FETCH_HEAD)" fresh
        LINES+=("governance refresh: cloud session — reset ephemeral clone to origin/$GOV_BRANCH")
      else
        local_sha=$(git -C "$GOV" rev-parse --verify --quiet HEAD 2>/dev/null || echo 'unknown')
        write_refresh_receipt reset-failed "$local_sha" "$remote_sha" \
          "$(commits_behind "$GOV" HEAD FETCH_HEAD)" stale
        LINES+=("governance refresh: WARN reset to origin/$GOV_BRANCH failed — reusing clone")
      fi
    else
      local_sha=$(git -C "$GOV" rev-parse --verify --quiet HEAD 2>/dev/null || echo 'unknown')
      # The fetch failed, so origin is genuinely unknown — not "equal to local".
      write_refresh_receipt fetch-failed "$local_sha" unknown -1 unknown
      LINES+=("governance refresh: WARN fetch origin/$GOV_BRANCH failed — reusing clone (may be stale)")
    fi
    # Per-session, per-repository dependency work (consumer workspace toolchain
    # + pre-commit warm) moved out of the cached account Setup script.
    DEPS_HELPER="$GOV/environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh"
    if [ -f "$DEPS_HELPER" ]; then
      DEPS_LINE=$(bash "$DEPS_HELPER" --workspace "$WORKSPACE" 2>&1 | tail -1)
      LINES+=("session deps: ${DEPS_LINE:-unknown}")
    fi
  fi
fi

if GOV=$(resolve_governance_dir); then
  LINES+=("governance SSOT: $GOV (GitHub Quantum-L9/Cursor-Governance)")
  if [ -d "$GOV/.git" ]; then
    br=$(git -C "$GOV" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
    sha=$(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo "?")
    if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
      # Local/Desktop: this is a developer checkout — SessionStart NEVER resets
      # it. Report revision and drift against origin/main instead.
      LINES+=("governance rev: ${br}@${sha} (local checkout — SessionStart never resets it)")
      if [ "$br" != "main" ]; then
        LINES+=("WARN: governance checkout is not on main (branch: $br) — drift is expected for in-flight work; report only")
      fi
      if git -C "$GOV" fetch --depth 1 origin main >/dev/null 2>&1; then
        local_sha=$(git -C "$GOV" rev-parse --short HEAD 2>/dev/null || echo "?")
        remote_sha=$(git -C "$GOV" rev-parse --short FETCH_HEAD 2>/dev/null || echo "?")
        if [ "$local_sha" = "$remote_sha" ]; then
          LINES+=("governance drift: none (HEAD == origin/main @$local_sha)")
        else
          LINES+=("governance drift: local @$local_sha vs origin/main @$remote_sha")
        fi
      fi
    else
      LINES+=("governance rev: ${br}@${sha}")
    fi
  fi
  LINES+=("authority order: CANONICAL_LAW.md > Autonomy Surface Profile > AGENTS.md > skills > agent-invented contracts")
  if [ -d "$GOV/skills" ]; then
    n=$(find "$GOV/skills" -maxdepth 2 -name SKILL.md 2>/dev/null | wc -l | tr -d ' ')
    LINES+=("skills available: $n l9-* skills under \$GOV/skills (invoke by name)")
  fi

  # --- Autonomy Surface Profile doctrine (standing A4) ---------------------
  PROFILE_LOADER="$GOV/ops/autonomy/profile_loader.py"
  if [ -x "$GOV/.venv/bin/python3" ]; then
    PY="$GOV/.venv/bin/python3"
  elif [ -x "$GOV/.venv/bin/python" ]; then
    PY="$GOV/.venv/bin/python"
  else
    PY="python3"
  fi
  # --- Claude projection engine (repair stale managed state; fail-open) ----
  # SessionStart runs the SAME engine as install.sh (setup), so a cached
  # environment whose bootstrap never ran — or ran against an older governance
  # revision — reconciles here: skills/commands symlinks repaired, settings
  # merge-patched, rules mount retargeted, stale managed projections removed.
  # The engine writes ~/.l9/claude/projection-receipt.json. Fail-open: a
  # projection failure degrades to a WARN line, never blocks the session.
  PROJECTION_ENGINE="$GOV/ops/scripts/claude_projection.py"
  if [ "${L9_SKIP_SESSION_PROJECTION:-}" != "1" ] \
     && [ -f "$PROJECTION_ENGINE" ] && command -v "$PY" >/dev/null 2>&1; then
    PROJECTION_LINE=$("$PY" "$PROJECTION_ENGINE" --root "$GOV" --workspace "$WORKSPACE" \
      --summary 2>/dev/null | tail -1)
    case "${PROJECTION_LINE:-}" in
      projection=ok) LINES+=("claude projection: ok (receipt ~/.l9/claude/projection-receipt.json)") ;;
      projection=*)  LINES+=("claude projection: WARN ${PROJECTION_LINE#projection=} — see ~/.l9/claude/projection-receipt.json") ;;
      *)             LINES+=("claude projection: WARN engine produced no summary — run 'make claude-install'") ;;
    esac
  fi

  if [ -f "$PROFILE_LOADER" ] && command -v "$PY" >/dev/null 2>&1; then
    PROFILE_BLOCK=$("$PY" "$PROFILE_LOADER" 2>/dev/null || true)
    if [ -n "$PROFILE_BLOCK" ]; then
      LINES+=("--- autonomy surface profile ---")
      while IFS= read -r line || [ -n "$line" ]; do
        LINES+=("$line")
      done <<< "$PROFILE_BLOCK"
    else
      LINES+=("autonomy profile: unreadable; continue under base governance")
    fi
  else
    LINES+=("autonomy profile: loader unavailable; continue under base governance")
  fi

  # --- Bounded-autonomy campaign context (fail-open; read-only probe) ------
  AUTONOMY_BOOTSTRAP="$GOV/environment/program-execution/peer_execution/autonomy/bootstrap.py"
  if [ -f "$AUTONOMY_BOOTSTRAP" ] && command -v "$PY" >/dev/null 2>&1; then
    AUTONOMY_CONTEXT=$("$PY" "$AUTONOMY_BOOTSTRAP" --workspace "$WORKSPACE" 2>/dev/null || true)
    [ -n "$AUTONOMY_CONTEXT" ] && LINES+=("--- bounded autonomy ---" "$AUTONOMY_CONTEXT")
  else
    LINES+=("bounded autonomy: runtime unavailable; continue under base governance")
  fi

  # --- Claude execution profile (surface personality; fail-open) -----------
  # Claude is the unleashed surface, Cursor is the constrained one. Resolve which
  # applies from the runtime — CLAUDE_CODE_REMOTE=true is the cloud discriminator
  # — never from model identity, and name anything that would silently re-impose
  # a ceiling (L9 lane caps, Claude Code's own subagent limits, workflow sizing).
  EXECUTION_PROFILE="$GOV/ops/autonomy/execution_profile.py"
  if [ -f "$EXECUTION_PROFILE" ] && command -v "$PY" >/dev/null 2>&1; then
    PROFILE_TEXT=$("$PY" "$EXECUTION_PROFILE" --root "$GOV" --workspace "$WORKSPACE" 2>/dev/null || true)
    if [ -n "$PROFILE_TEXT" ]; then
      LINES+=("--- claude execution profile ---")
      while IFS= read -r line || [ -n "$line" ]; do
        LINES+=("$line")
      done <<< "$PROFILE_TEXT"
    else
      LINES+=("claude execution profile: unresolved; continue under base governance")
    fi
  fi

  # Skill-router readiness hint
  if [ -f "$GOV/ops/generated/skill-registry.json" ]; then
    LINES+=("skill-router: ops/generated/skill-registry.json ready (UserPromptSubmit)")
  fi
else
  LINES+=("governance SSOT: NOT FOUND — web/setup.sh must clone GitHub main to \$HOME/.cursor-governance")
  LINES+=("remote: https://github.com/Quantum-L9/Cursor-Governance (branch main)")
fi

# memory-bank/ retired — resume from Graphiti inject/PICKUP only (no T0 excerpt)

# --- Memory: single front door = Cursor Graphiti (CANONICAL_LAW §8)
LINES+=("shared memory: Cursor Graphiti front door only (ops/graphiti inject / write); no L9_MEMORY_HTTP side door; memory-bank retired; memory never gates repository writes")

# --- L9 Claude environment status (from the installer receipt) --------------
# The canonical installer writes ~/.l9/claude/bootstrap-state.json
# (schema l9.claude-bootstrap.v1). Project it compactly so the model — and the
# operator on mobile — sees what is actually available instead of discovering
# bootstrap breakage when a later memory or publish operation fails.
emit_bootstrap_status() {
  local py="$1"
  local reader="$GOV/ops/scripts/claude_bootstrap_receipt.py"
  local refresh_reader="$GOV/ops/scripts/governance_refresh_receipt.py"

  # The projection used to parse the receipt inline, with its own idea of what
  # the fields mean. That second parser had no notion of an ABSENT receipt or an
  # EXPIRED one, so it reported silence as nothing-to-say and a stale receipt as
  # current — the same class of defect the receipt rewrite removed one layer
  # down (B-04, B-05). One reader, one set of rules.
  if [ -z "$py" ] || ! command -v "$py" >/dev/null 2>&1 || [ ! -f "$reader" ]; then
    LINES+=("L9 Claude environment: receipt reader unavailable — state UNKNOWN")
    return 0
  fi

  # Repair, do not reprint. The receipt carries its own remediation string and
  # SessionStart used to print it and move on, so a DEGRADED verdict was
  # inherited across sessions and days while the fix sat one line away. The
  # attempt is keyed on the GOVERNANCE REVISION, not on wall-clock time: the
  # installer writes a receipt stamped with the current revision, so a
  # successful repair suppresses the next attempt and a revision bump is the
  # only thing that re-arms it. That is what makes this converge instead of
  # re-running every session. Fail-open throughout — a repair that cannot run
  # degrades the session, it never blocks it.
  local state revision marker installer
  state="$("$py" "$reader" --read --json 2>/dev/null \
    | "$py" -c 'import json,sys
try:
    print(json.load(sys.stdin).get("state", ""))
except Exception:
    print("")' 2>/dev/null || true)"
  revision="$(git -C "$GOV" rev-parse HEAD 2>/dev/null || echo unknown)"
  marker="$HOME/.l9/claude/bootstrap-repair-${revision}.attempted"
  installer="$GOV/environment/agents/adapters/claude-code/install.sh"
  case "$state" in
    ready|"") : ;;
    *)
      if [ ! -f "$marker" ] && [ -f "$installer" ]; then
        mkdir -p "$HOME/.l9/claude"
        LINES+=("bootstrap repair: receipt was '$state' at ${revision:0:8} — running the installer once")
        if timeout "${L9_BOOTSTRAP_REPAIR_BUDGET:-90}" bash "$installer" \
          >"$HOME/.l9/claude/bootstrap-repair-${revision}.log" 2>&1; then
          : >"$marker"
        fi
      fi
      ;;
  esac

  local block
  block="$("$py" "$reader" --read 2>/dev/null || true)"
  if [ -n "$block" ]; then
    LINES+=("--- L9 Claude environment ---")
    while IFS= read -r line || [ -n "$line" ]; do
      LINES+=("$line")
    done <<< "$block"
  else
    LINES+=("L9 Claude environment: bootstrap receipt unreadable — run 'make claude-install'")
  fi

  if [ -f "$refresh_reader" ]; then
    local refresh
    refresh="$("$py" "$refresh_reader" --read 2>/dev/null || true)"
    [ -n "$refresh" ] && LINES+=("$refresh")
  fi

  # A receipt written for a different directory reports READY for artifacts this
  # session never loads, so compare the wired workspace against this project.
  local wired
  wired="$("$py" -c 'import json,sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("workspace",""))
except Exception:
    print("")' "$HOME/.l9/claude/bootstrap-state.json" 2>/dev/null || true)"
  if [ -n "$wired" ] && [ "$wired" != "$WORKSPACE" ]; then
    LINES+=("WARN: bootstrap wired $wired, but this project is $WORKSPACE — .claude mirrors may be missing")
  fi
}

# --- Account-field drift (WS-4.1) -------------------------------------------
# The Setup script and Environment variables fields are copy-pasted and drift
# from main invisibly — there is no way to read a field back from inside the
# sandbox. The stub stamps its revision, so the comparison is possible; doing it
# HERE is what makes it automatic rather than something an operator must
# remember to run (audit B-06, B-07).
emit_account_drift() {
  local py="$1"
  local verifier="$GOV/environment/agents/adapters/claude-code/verify_account_env.py"
  [ -f "$verifier" ] || return 0
  [ -n "$py" ] && command -v "$py" >/dev/null 2>&1 || return 0

  local out
  out="$("$py" "$verifier" 2>/dev/null || true)"
  # Report only when something is wrong; a matching environment stays quiet.
  if printf '%s' "$out" | grep -q 'DRIFT:'; then
    LINES+=("--- account field drift ---")
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in
        *DRIFT:*|*"    "*|*Repair:*) LINES+=("$line") ;;
      esac
    done <<< "$out"
  fi
}

# --- Capability plane (RETIRED 2026-08-29, never shipped) -------------------
emit_capability_readiness() {
  LINES+=("capability_broker=retired (never shipped; not probed)")
  LINES+=("memory: GRAPHITI_MCP_URL / local Graphiti CLI (no broker probe)")
}

# --- Final machine-readable readiness receipt (Phase 7) ---------------------
# One truthful receipt (schema l9.claude-readiness.v1) aggregating projection,
# MCP, Graphiti, Makefile facade, dispatcher, merge-authority posture, secret
# boundary, and governance-SHA freshness. Written to
# ~/.l9/claude/readiness-receipt.json; a compact block is surfaced here so the
# operator sees the real contract, not a symlink-existence guess.
emit_readiness_receipt() {
  local py="$1"
  local emitter="$GOV/ops/scripts/emit_claude_readiness.py"
  [ -f "$emitter" ] || return 0
  [ -n "$py" ] && command -v "$py" >/dev/null 2>&1 || return 0
  local block
  block="$("$py" "$emitter" --root "$GOV" --workspace "$WORKSPACE" --read 2>/dev/null || true)"
  [ -n "$block" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    LINES+=("$line")
  done <<< "$block"
}

emit_bootstrap_status "$PY"
emit_account_drift "$PY"
emit_capability_readiness "$PY"
emit_readiness_receipt "$PY"

CONTEXT=$(printf '%s\n' "${LINES[@]}")
emit "$CONTEXT"
