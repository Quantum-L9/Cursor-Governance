# Resolve-then-export L9_MEMORY_INTERPRETER from ops.memory.runtime_binding.
# Not a second resolver: binding is the only brain. Callers export a proven
# interpreter into the parent process (install.sh / SessionStart / cloud env).
# Also strips the retired provider transport from this process.
#
# Usage: . this file; bind_l9_memory_interpreter <python> <gov-root>
bind_l9_memory_interpreter() {
  local py="${1:-}" gov="${2:-}" interp=""
  unset GRAPHITI_MCP_URL GRAPHITI_MCP_TOKEN
  [ -n "$py" ] && [ -x "$py" ] && [ -n "$gov" ] || return 0
  interp="$(
    PYTHONPATH="$gov${PYTHONPATH:+:$PYTHONPATH}" "$py" -c \
      'from ops.memory.runtime_binding import resolve_runtime_binding
b = resolve_runtime_binding()
print((b.interpreter or "") if b.status in ("exact", "compatible") else "")'
  )" || interp=""
  if [ -n "$interp" ]; then
    export L9_MEMORY_INTERPRETER="$interp"
  fi
}
