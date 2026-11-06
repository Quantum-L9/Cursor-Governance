#!/usr/bin/env bash
# Retired stdio/HMAC entrypoint. Native Memory requires an admitted owner client.
set -euo pipefail

# Preserve the old flag without resolving, reading, or executing its target.
if [ "${1:-}" = "--governance" ]; then
  if [ "$#" -lt 2 ]; then
    printf '%s\n' 'manus-memory-mcp ERROR: --governance needs a path' >&2
    exit 2
  fi
  shift 2
fi
if [ "$#" -ne 0 ]; then
  printf '%s\n' 'manus-memory-mcp ERROR: unexpected argument' >&2
  exit 2
fi
printf '%s\n' 'manus-memory-mcp UPSTREAM_BLOCKED: stdio/HMAC launch retired; native authenticated Streamable HTTP package/client unavailable; Manus client UNBOUND; live admission UNKNOWN' >&2
exit 2
