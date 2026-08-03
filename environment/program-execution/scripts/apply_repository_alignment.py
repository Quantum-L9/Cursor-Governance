from __future__ import annotations

import argparse
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
    path.write_text(text + separator + block.lstrip("\n"), encoding="utf-8")
    return True


def apply(repository_root: Path) -> list[str]:
    root = repository_root.expanduser().resolve()
    changed: list[str] = []
    for relative, block in BLOCKS.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        marker = block.splitlines()[1]
        if _append_once(path, marker, block):
            changed.append(relative)
    makefile = root / "Makefile"
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
