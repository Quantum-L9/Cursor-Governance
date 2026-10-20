"""Autonomy test namespace.

`stacked_repo` is intentionally declared in the repository-root ``conftest.py``.
The scoped publication runner selects test files across multiple top-level roots;
the root fixture remains available to that composite selection while this local
module stays free of a duplicate fixture definition.

Every test runs against its own empty operator-instruction store. The merge
gate, ``authorize_merge.py`` and ``stack_safe_merge.py`` read the account's
receipt store, so without this a cancellation the host hook recorded in the
developer's own session (CANONICAL_LAW §6.2.14 item 6: a cancellation never
lapses) turned unrelated merge tests red. A test that needs receipts still
writes its own store and points the code at it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_AUTONOMY = Path(__file__).resolve().parents[3] / "ops" / "autonomy"


@pytest.fixture(autouse=True)
def _isolated_operator_instruction_store(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Path:
    store = tmp_path_factory.mktemp("operator-instructions") / "operator-merge-instructions.json"
    # Gate subprocesses inherit this hook-environment override.
    monkeypatch.setenv("L9_OPERATOR_INSTRUCTION_FILE", str(store))
    if str(_AUTONOMY) not in sys.path:
        sys.path.insert(0, str(_AUTONOMY))
    import authorize_merge  # noqa: PLC0415
    import operator_merge_instruction  # noqa: PLC0415

    monkeypatch.setattr(operator_merge_instruction, "account_store_path", lambda: store)
    monkeypatch.setattr(authorize_merge, "account_instruction_path", lambda: store)
    return store
