"""Shared helpers for the l9-skill-compiler stage scripts.

`scan_skill_topology.py` has imported `REPO`, `emit`, `fail` and `load_json`
from here since f2b0ad3d (#341), but the module was never added — so the stage
was unimportable by any `sys.path`, its test failed at collection, and the
`dag_skill_ownership` invariant it enforces never ran.

Nothing here is invented. Each symbol is pinned by how the caller already uses
it:

* `main()` does `return fail(...)` and `return emit(...)` under
  `sys.exit(main(sys.argv))`, so both are exit codes — non-zero for the usage
  error, zero for a successful stage.
* `emit` receives a payload the caller has already shaped (`stage`, `decision`,
  `decided_by`, `evidence`, `candidates`), so it serializes and does not wrap.
* The serialization matches `skills/l9-intelligence-harvest/scripts/_common.py`:
  JSON, `indent=2`, `sort_keys=True`, trailing newline. That pack keeps the
  bare `_common` name (its meta/package-integrity.json hashes the path); this
  one is `_compiler_common` because under pytest's rootdir-relative import mode
  both resolved to the single global module name `_common`, so whichever pack's
  tests ran first won `sys.modules` and the other pack's scripts imported the
  wrong helper — which is how this stage's test broke at collection a second
  time, after this module was added to fix it breaking the first time.
* `REPO` is joined with `"skills"` to locate the live pack directory, so it is
  the repository root — three parents above this file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]


def load_json(path):
    """Read a JSON document from `path`."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(obj, path=None):
    """Serialize `obj` as the house JSON shape, to `path` or stdout."""
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def emit(payload, path=None):
    """Write a stage payload and return the success exit code."""
    dump(payload, path)
    return 0


def fail(message, code=2):
    """Report a stage failure on stderr and return a non-zero exit code."""
    print(message, file=sys.stderr)
    return code
