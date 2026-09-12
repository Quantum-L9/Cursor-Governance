# Resolve-then-export L9_MEMORY_INTERPRETER from ops.memory.runtime_binding.
# Not a second resolver: binding is the only brain. Callers export a proven
# interpreter into the parent process (install.sh / SessionStart / cloud env).
# Also strips the retired provider transport from this process.
#
# Fail closed (PR #548 review, F-548-006): every call either exports a path
# proven by THIS resolution or leaves L9_MEMORY_INTERPRETER unset. The first
# version only assigned inside `if [ -n "$interp" ]`, so a cached shell that
# already exported an obsolete path kept it when resolution failed —
# runtime_binding prefers the environment value, a deleted venv there resolves
# to nothing, and the stale export then satisfied the projection's
# `_requires_env`, rendered the memory server, and was persisted again.
#
# Order of proof: a value already in the environment is a CANDIDATE and is
# re-proven first (a deliberately pinned interpreter must not be replaced by
# the governance python merely because both work); if it does not prove, it is
# discarded and the supplied governance python is proven on its own. Nothing
# unproven survives either step.
#
# Usage: . this file; bind_l9_memory_interpreter <python> <gov-root>
bind_l9_memory_interpreter() {
  local py="${1:-}" gov="${2:-}" interp="" prior=""
  unset GRAPHITI_MCP_URL GRAPHITI_MCP_TOKEN
  prior="${L9_MEMORY_INTERPRETER:-}"
  # Cleared BEFORE any resolution, so no path below can republish it unproven.
  unset L9_MEMORY_INTERPRETER
  [ -n "$py" ] && [ -x "$py" ] && [ -n "$gov" ] || return 0
  if [ -n "$prior" ]; then
    interp="$(_l9_resolve_memory_interpreter "$py" "$gov" "$prior")" || interp=""
  fi
  if [ -z "$interp" ]; then
    interp="$(_l9_resolve_memory_interpreter "$py" "$gov" "")" || interp=""
  fi
  if [ -n "$interp" ] && [ -x "$interp" ]; then
    export L9_MEMORY_INTERPRETER="$interp"
  fi
}

# One resolution attempt. $3 is the candidate handed to the resolver through
# its own environment precedence (empty means "none: prove the governance
# python"). Prints the proven interpreter, or nothing.
_l9_resolve_memory_interpreter() {
  local py="$1" gov="$2" candidate="$3"
  if [ -n "$candidate" ]; then
    L9_MEMORY_INTERPRETER="$candidate" PYTHONPATH="$gov${PYTHONPATH:+:$PYTHONPATH}" "$py" -c \
      'from ops.memory.runtime_binding import resolve_runtime_binding
b = resolve_runtime_binding()
print((b.interpreter or "") if b.status in ("exact", "compatible") else "")'
  else
    PYTHONPATH="$gov${PYTHONPATH:+:$PYTHONPATH}" "$py" -c \
      'from ops.memory.runtime_binding import resolve_runtime_binding
b = resolve_runtime_binding()
print((b.interpreter or "") if b.status in ("exact", "compatible") else "")'
  fi
}
