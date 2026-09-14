#!/usr/bin/env bash
set -uo pipefail
ROOT=/tmp/l9-ci-preflight-audit
cd "$ROOT"
for rev in b1a491414ed04bb18d665f8a8755de80947c8200 f546f122d33601ea5a4b2592e3482c5c39eddd82 0c487747b0fcd172edaefe9e843dac818de8fc12; do
  short="${rev:0:8}"
  dir="$ROOT/rev-check/$short"
  echo "===== SDK revision $short ====="
  mkdir -p "$dir" && git -C "$dir" init -q && git -C "$dir" remote add origin https://github.com/Quantum-L9/l9-ci-sdk.git
  git -C "$dir" -c protocol.version=2 fetch -q --depth=1 origin "$rev"
  git -C "$dir" checkout -q --detach FETCH_HEAD
  actual=$(git -C "$dir" rev-parse HEAD)
  echo "checked out: $actual"
  if [ ! -f "$dir/.l9/integration-contract.yaml" ]; then echo "CONTRACT FILE MISSING"; else
    schema=$(grep -m1 'schema:' "$dir/.l9/integration-contract.yaml" | awk '{print $2}')
    exe=$(grep -m1 'executable:' "$dir/.l9/integration-contract.yaml" | awk '{print $2}')
    echo "contract schema=$schema executable=$exe"
  fi
  if [ -f "$dir/pyproject.toml" ]; then ver=$(grep -m1 '^version' "$dir/pyproject.toml"); echo "pyproject: $ver"; else echo "pyproject: ABSENT"; fi
  uv venv "$dir/venv" --python 3.11 >/dev/null 2>&1
  if [ -f "$dir/requirements.txt" ]; then
    uv pip install --python "$dir/venv/bin/python" -r "$dir/requirements.txt" >/dev/null 2>&1 && echo "deps: installed from requirements.txt" || echo "deps: INSTALL FAILED"
  else
    echo "deps: requirements.txt ABSENT (pip install skipped)"
  fi
  fails=0
  for path in "providers detect" "semgrep run" "semgrep normalize" "gate evaluate" "bundle validate" "bundle project-agent-payload" "bundle project-sarif" "compatibility check" "baseline compare-tests" "baseline scan-packet-envelope" "baseline compare-scan" "baseline validate-ledger"; do
    out=$(cd "$dir" && PYTHONPATH="$dir" "$dir/venv/bin/python" -m l9_ci $path --help 2>&1); rc=$?
    if [ $rc -ne 0 ]; then echo "  MISSING [$path] rc=$rc :: $(echo "$out" | tail -1 | cut -c1-100)"; fails=$((fails+1)); fi
  done
  echo "probe failures: $fails/12"
done
