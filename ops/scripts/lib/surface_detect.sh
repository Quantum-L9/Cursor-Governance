#!/usr/bin/env bash
# Surface identity SSOT (shell twin of ops/autonomy/surface_detect.py).
# Echoes: cursor | claude-code | claude-code-remote | codex | gemini | manus | unknown
# shellcheck shell=bash

# Detect the agent surface from the environment.
# A Cursor host marker overrides a projected Claude explicit surface. Other
# known explicit ids still win. Otherwise markers break ties. unknown = do
# not skip.
# Cursor host markers: CURSOR_AGENT, CURSOR_CONVERSATION_ID,
# CURSOR_EXTENSION_HOST_ROLE. The last two stay set when a hook child does
# not receive CURSOR_AGENT.
l9_cursor_host_present() {
  [ -n "${CURSOR_AGENT:-}" ] && return 0
  [ -n "${CURSOR_CONVERSATION_ID:-}" ] && return 0
  [ -n "${CURSOR_EXTENSION_HOST_ROLE:-}" ] && return 0
  return 1
}

l9_detect_surface() {
  local explicit
  explicit="$(printf '%s' "${L9_GOVERNANCE_SURFACE:-}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  if l9_cursor_host_present; then
    case "$explicit" in
      claude-code|claude-code-remote)
        printf '%s\n' "cursor"
        return 0
        ;;
    esac
  fi
  case "$explicit" in
    cursor|claude-code|claude-code-remote|codex|gemini|manus)
      printf '%s\n' "$explicit"
      return 0
      ;;
  esac

  case "${CLAUDE_CODE_REMOTE:-}" in
    true|TRUE|True)
      printf '%s\n' "claude-code-remote"
      return 0
      ;;
  esac

  if [ -n "${CLAUDECODE:-}" ] || [ -n "${CLAUDE_CODE_ENTRYPOINT:-}" ] || [ -n "${CLAUDE_CODE_SESSION_ID:-}" ]; then
    printf '%s\n' "claude-code"
    return 0
  fi

  if l9_cursor_host_present; then
    printf '%s\n' "cursor"
    return 0
  fi

  printf '%s\n' "unknown"
  return 0
}

# True for a live Claude process. A projected L9_GOVERNANCE_SURFACE value is
# not a runtime; Cursor loads that string from .claude/settings.json.
l9_claude_runtime_present() {
  case "${CLAUDE_CODE_REMOTE:-}" in
    true|TRUE|True) return 0 ;;
  esac
  if [ -n "${CLAUDECODE:-}" ] || [ -n "${CLAUDE_CODE_ENTRYPOINT:-}" ] || [ -n "${CLAUDE_CODE_SESSION_ID:-}" ]; then
    return 0
  fi
  return 1
}

# True (exit 0) when Claude gate-class hooks should evaluate.
l9_is_claude_gate_surface() {
  case "$(l9_detect_surface)" in
    claude-code|claude-code-remote) return 0 ;;
    *) return 1 ;;
  esac
}
