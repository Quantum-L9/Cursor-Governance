#!/usr/bin/env bash
# Surface identity SSOT (shell twin of ops/autonomy/surface_detect.py).
# Echoes: cursor | claude-code | claude-code-remote | codex | gemini | manus | unknown
# shellcheck shell=bash

# Detect the agent surface from the environment.
# Explicit L9_GOVERNANCE_SURFACE wins when it is a known id; otherwise markers
# break ties toward the adapter. unknown means "do not skip gates".
l9_detect_surface() {
  local explicit
  explicit="$(printf '%s' "${L9_GOVERNANCE_SURFACE:-}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
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

  if [ -n "${CURSOR_AGENT:-}" ]; then
    printf '%s\n' "cursor"
    return 0
  fi

  printf '%s\n' "unknown"
  return 0
}

# True (exit 0) when Claude gate-class hooks should evaluate.
l9_is_claude_gate_surface() {
  case "$(l9_detect_surface)" in
    claude-code|claude-code-remote) return 0 ;;
    *) return 1 ;;
  esac
}
