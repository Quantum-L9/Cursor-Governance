"""Suite-local wiring for the memory boundary tests.

Helpers live in ``memory_boundary_fixtures`` (a plain module) rather than
here, so tests import them by a name that cannot collide with the repository's
root ``conftest`` under pytest's rootdir import mode. The fixtures are
re-exported through ``importlib`` so import sorting can never hoist them
above the path setup they depend on.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
for entry in (str(HERE), str(ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

_fixtures = importlib.import_module("memory_boundary_fixtures")
bound = _fixtures.bound
fake_cli = _fixtures.fake_cli
