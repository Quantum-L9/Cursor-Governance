"""Expose the controller test-support module under pytest importlib mode.

The repository uses pytest's importlib mode to prevent collisions between
same-named test modules. That mode intentionally does not add each test
module's directory to ``sys.path``, while this controller suite shares the
explicit support module ``helpers.py``. Keep the path grant local to this test
suite instead of weakening the repository-wide import policy.
"""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
