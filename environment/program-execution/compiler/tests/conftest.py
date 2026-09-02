"""Compiler test support: expose the Program Execution layer for imports.

Follows the repository convention from environment/program-execution/tests/
(test_probe_command.py): the PE layer is importable via
PYTHONPATH=environment/program-execution; root pytest runs with repo-root on
sys.path, so the PE root is inserted here for collection under both.
"""

from __future__ import annotations

import sys
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
# APPEND, never insert(0): Program Execution needs its own PE-exclusive
# packages here, but `scripts` is a top-level name it SHARES with the
# repository root. Prepending would hand PE's `scripts/` that name for the
# whole process. See peer_execution.imports.pe_script.
if str(PE_ROOT) not in sys.path:
    sys.path.append(str(PE_ROOT))
