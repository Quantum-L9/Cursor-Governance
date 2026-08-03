from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

MARKER_PREFIX = "<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:"

BLOCKS = {
    "CANONICAL_LAW.md": """
<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:CANONICAL_LAW -->

## Program Execution subsystem

`environment/program-execution/` is the canonical Program Execution subsystem.
Its sealed `core/` owns program-level truth, Program Locks, Controller state law,
and canonical worker and verification receipts. Root `autonomy/` is a subordinate
local enforcement provider, not a second Program Execution Controller.

Program Execution adapters may narrow authority but must never widen it. Mutable
program runtime, leases, attempts, receipts, and health state live outside this
repository under `$HOME/.l9/programs/`.
""",
    "AGENTS.md": """
<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:AGENTS -->

## Program Execution adapter layer

The reusable subsystem lives at `environment/program-execution/`. Do not copy its
core schemas, root `autonomy/`, the Claude bounded-autonomy scheduler, the agent
registry, or the Graphiti client into an adapter.

Program Execution tasks use the Program Execution Controller lease as the sole
authoritative work claim. They must not acquire a competing Graphiti task claim.
A Graphiti projection is observability only and is never authoritative.

Validation:

```bash
make program-execution-core-validate
make program-execution-adapters
make program-execution-conformance
make program-execution-probe
make pr
```
""",
    "README.md": """
<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:README -->

## Program Execution

`environment/program-execution/` contains the sealed Program Execution core,
replaceable execution adapters, conformance contracts, routing policy, and bridges
to existing Cursor-Governance runtimes. Mutable program state remains outside Git
under `$HOME/.l9/programs/`.
""",
    "environment/agents/docs/WORK_CLAIM_PROTOCOL.md": """
<!-- PROGRAM_EXECUTION_ADAPTER_LAYER_V1:WORK_CLAIM -->

## Program Execution lease precedence

- Non-program work continues to use Graphiti task claims.
- Program Execution tasks use the Controller lease as the sole authoritative claim.
- Program adapters must not create a competing Graphiti claim.
- A derived Graphiti claim projection is non-authoritative observability only.
""",
}

MAKE_BLOCK = """
# PROGRAM_EXECUTION_ADAPTER_LAYER_V1
PE_ROOT := environment/program-execution
.PHONY: program-execution-core-validate program-execution-adapters \
	program-execution-conformance program-execution-probe

program-execution-core-validate:
	PYTHONDONTWRITEBYTECODE=1 python3 -B $(PE_ROOT)/core/scripts/validate_pair.py \
		$(PE_ROOT)/core --mode template

program-execution-adapters:
	PYTHONDONTWRITEBYTECODE=1 python3 -B \
		$(PE_ROOT)/scripts/validate_execution_adapters.py

program-execution-conformance:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) python3 -B \
		$(PE_ROOT)/scripts/run_conformance.py

program-execution-probe:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) python3 -B \
		$(PE_ROOT)/scripts/probe_execution_adapters.py
"""


def _append_once(path: Path, marker: str, block: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return False
    separator = "" if text.endswith("\n") else "\n"
    # Path is confined by _confine_to_allowed_root / _child_file before write.
    path.write_text(  # NOSONAR python:S2083
        text + separator + block.lstrip("\n"),
        encoding="utf-8",
    )
    return True


def _confine_to_allowed_root(path: Path) -> Path:
    """Resolve path and require it stay under cwd or the system temp root."""
    resolved = path.expanduser().resolve()
    allowed = (Path.cwd().resolve(), Path(tempfile.gettempdir()).resolve())
    for root in allowed:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise ValueError(f"path escapes allowed roots: {path}")


def _child_file(root: Path, name: str) -> Path:
    """Join a single trusted filename under an already-confined root."""
    if name != Path(name).name or "/" in name or "\\" in name or name in {"", ".", ".."}:
        raise ValueError(f"unsafe file name: {name!r}")
    path = (root / name).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {name}") from exc
    return path


def apply(repository_root: Path) -> list[str]:
    root = _confine_to_allowed_root(repository_root)
    if not root.is_dir():
        raise NotADirectoryError(root)
    changed: list[str] = []
    for name, block in BLOCKS.items():
        path = _child_file(root, name)
        if not path.is_file():
            raise FileNotFoundError(path)
        marker = block.splitlines()[1]
        if _append_once(path, marker, block):
            changed.append(name)
    makefile = _child_file(root, "Makefile")
    if not makefile.is_file():
        raise FileNotFoundError(makefile)
    if _append_once(
        makefile,
        "# PROGRAM_EXECUTION_ADAPTER_LAYER_V1",
        MAKE_BLOCK,
    ):
        changed.append("Makefile")
    return sorted(changed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repository_root", nargs="?", default=".")
    args = parser.parse_args()
    changed = apply(Path(args.repository_root))
    for path in changed:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
