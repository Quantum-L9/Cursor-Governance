#!/usr/bin/env bash
# beforeShellExecution — deny git commit / make push when gate not satisfied
set -uo pipefail
REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
exec "$(dirname "$REAL_HOOK")/graphiti_gate_runner.sh" shell
