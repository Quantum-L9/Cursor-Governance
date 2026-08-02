"""Make the subagent-generated-data runtime importable for its test suite.

The package directory name contains hyphens, so it cannot be imported as a
Python package by name. This conftest puts the directory on sys.path (mirroring
the pattern used by environment/claude-code/autonomy) so tests can
``from runtime.pipeline import process_packet``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
