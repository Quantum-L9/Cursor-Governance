#!/usr/bin/env bash
# Ensure Graphiti SSH tunnel is up before health/prefetch. Fail-open — never block session.
set -uo pipefail

graphiti_load_env() {
  # shellcheck disable=SC1090
  local defaults=""
  for p in "$HOME/Dropbox/cursor governance/GlobalCommands/ops/graphiti/graphiti.env.defaults" \
           "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/graphiti/graphiti.env.defaults"; do
    [ -f "$p" ] && defaults="$p" && break
  done
  [ -n "$defaults" ] && set -a && source "$defaults" && set +a
  [ -f "$HOME/.cursor/graphiti.env" ] && set -a && source "$HOME/.cursor/graphiti.env" && set +a
  [ -f "$HOME/.cursor/secrets/graphiti.env" ] && set -a && source "$HOME/.cursor/secrets/graphiti.env" && set +a
  if [ -z "${GRAPHITI_MCP_TOKEN:-}" ]; then
    GRAPHITI_MCP_TOKEN="$(security find-generic-password -s graphiti-mcp-token -w 2>/dev/null || true)"
    export GRAPHITI_MCP_TOKEN
  fi
}

resolve_ssh_key_file() {
  SSH_KEY_FILE=""
  if [ -n "${GRAPHITI_SSH_KEY:-}" ] && [ -f "${GRAPHITI_SSH_KEY/#\~/$HOME}" ]; then
    SSH_KEY_FILE="${GRAPHITI_SSH_KEY/#\~/$HOME}"
    return 0
  fi
  if [ -n "${GRAPHITI_SSH_KEYCHAIN_SERVICE:-}" ]; then
    local tmp
    tmp="$(mktemp)"
    if security find-generic-password -s "$GRAPHITI_SSH_KEYCHAIN_SERVICE" -w >"$tmp" 2>/dev/null; then
      chmod 600 "$tmp"
      SSH_KEY_FILE="$tmp"
      SSH_KEY_TEMP=1
      return 0
    fi
    rm -f "$tmp"
  fi
  for candidate in "$HOME/.ssh/Hetzner-C1-nopass" "$HOME/.cursor/c1_ssh_key"; do
    if [ -f "$candidate" ]; then
      SSH_KEY_FILE="$candidate"
      return 0
    fi
  done
  # Last resort: repo .env.local C1_SSH (inline key)
  local repo="${CURSOR_PROJECT_DIR:-}"
  local env_local="$repo/.env.local"
  if [ -f "$env_local" ]; then
    local out="$HOME/.ssh/Hetzner-C1-nopass"
    mkdir -p "$HOME/.ssh"
    if python3 - "$env_local" "$out" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(encoding="utf-8")
m = re.search(r"C1_SSH=(-----BEGIN OPENSSH PRIVATE KEY-----.*?-----END OPENSSH PRIVATE KEY-----)", text, re.DOTALL)
if not m:
    sys.exit(1)
key = m.group(1).replace("\\n", "\n")
if "\\n" not in m.group(1) and "-----END" in key:
    pass
Path(sys.argv[2]).write_text(key.strip() + "\n", encoding="utf-8")
PY
    then
      chmod 600 "$out"
      SSH_KEY_FILE="$out"
      return 0
    fi
  fi
  return 1
}

port_open() {
  local port="${1:-8100}"
  python3 - "$port" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
s.settimeout(0.5)
try:
    s.connect(("127.0.0.1", port))
    sys.exit(0)
except OSError:
    sys.exit(1)
finally:
    s.close()
PY
}

tunnel_running() {
  local port="${GRAPHITI_TUNNEL_LOCAL_PORT:-8100}"
  pgrep -f "ssh.*-L[[:space:]]*${port}:127.0.0.1" >/dev/null 2>&1
}

start_tunnel() {
  local host="${GRAPHITI_SSH_HOST:-}"
  local user="${GRAPHITI_SSH_USER:-root}"
  local local_port="${GRAPHITI_TUNNEL_LOCAL_PORT:-8100}"
  local remote_port="${GRAPHITI_TUNNEL_REMOTE_PORT:-8100}"
  if [ -z "$host" ] || [ -z "$SSH_KEY_FILE" ]; then
    echo "tunnel: skip (missing host or key)"
    return 1
  fi
  local logdir="$HOME/.cursor/logs_llm"
  mkdir -p "$logdir"
  local ssh_bin
  ssh_bin="$(command -v ssh)"
  # Background tunnel; ServerAlive keeps it up between sessions
  nohup "$ssh_bin" -N \
    -o "ServerAliveInterval=30" \
    -o "ServerAliveCountMax=3" \
    -o "StrictHostKeyChecking=accept-new" \
    -o "ExitOnForwardFailure=yes" \
    -i "$SSH_KEY_FILE" \
    -L "${local_port}:127.0.0.1:${remote_port}" \
    "${user}@${host}" >>"$logdir/graphiti-tunnel.log" 2>>"$logdir/graphiti-tunnel.err" &
  echo $! >"$HOME/.cursor/graphiti-tunnel.pid"
  # Wait up to 5s for port
  local i=0
  while [ "$i" -lt 10 ]; do
    if port_open "$local_port"; then
      echo "tunnel: started (pid $(cat "$HOME/.cursor/graphiti-tunnel.pid" 2>/dev/null || echo ?))"
      return 0
    fi
    sleep 0.5
    i=$((i + 1))
  done
  echo "tunnel: start attempted but port ${local_port} not yet open"
  return 1
}

SSH_KEY_TEMP=0
graphiti_load_env

if [ "${GRAPHITI_MEMORY_ENABLED:-1}" = "0" ]; then
  echo "tunnel: disabled"
  exit 0
fi

local_port="${GRAPHITI_TUNNEL_LOCAL_PORT:-8100}"
if port_open "$local_port"; then
  echo "tunnel: already open on ${local_port}"
  exit 0
fi

if tunnel_running; then
  echo "tunnel: ssh process running, waiting for port ${local_port}..."
  for _ in 1 2 3 4 5; do
    sleep 0.5
    port_open "$local_port" && { echo "tunnel: port open"; exit 0; }
  done
fi

if ! resolve_ssh_key_file; then
  echo "tunnel: no SSH key (set GRAPHITI_SSH_KEY, keychain, or C1_SSH in .env.local)"
  exit 0
fi

start_tunnel
[ "$SSH_KEY_TEMP" = "1" ] && [ -n "$SSH_KEY_FILE" ] && rm -f "$SSH_KEY_FILE"
exit 0
