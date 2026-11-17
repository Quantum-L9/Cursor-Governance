"""A relayed close never asks the hosted store to supersede a local record id.

Observed 2026-11-17: the first relayed close in a container that had closed
earlier through the local carrier carried ``supersedes: [<local id>]``, and the
hosted MemoryService refused the whole continuation candidate ("supersession
refused: superseded record does not exist"). Supersession now only follows a
reference admitted by the same carrier.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ops.graphiti.hydration import close_session as cs
from ops.graphiti.hydration import session_latches as latches
from ops.memory.hook_carrier import CARRIER_ENV

SESSION = "sess-relay-supersede"
REF = "273f1156-8a55-4d35-8b3a-fe53eeec6e82"


def _receipt(project: Path, **fields: object) -> None:
    latches.write_receipt(
        project,
        SESSION,
        {"status": latches.STATUS_CLOSED_CANONICALLY, "continuation_reference": REF, **fields},
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    return tmp_path


def test_a_local_reference_is_not_superseded_by_a_relayed_close(project: Path) -> None:
    _receipt(project, continuation_carrier="local")
    assert cs._previous_continuation(project, SESSION, "relay") is None


def test_a_receipt_without_a_carrier_counts_as_local(project: Path) -> None:
    _receipt(project)
    assert cs._previous_continuation(project, SESSION, "relay") is None
    assert cs._previous_continuation(project, SESSION, "local") == REF


def test_the_same_carrier_still_supersedes(project: Path) -> None:
    _receipt(project, continuation_carrier="relay")
    assert cs._previous_continuation(project, SESSION, "relay") == REF


def test_the_receipt_records_the_carrier_that_admitted_the_reference(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(CARRIER_ENV, "relay")
    report: dict[str, object] = {"writes": []}
    cs._persist_obligation(
        project,
        SESSION,
        report,
        status=latches.STATUS_CLOSE_INCOMPLETE,
        continuation_reference=REF,
    )
    stored = json.loads(Path(latches.receipt_path(project, SESSION)).read_text(encoding="utf-8"))
    assert stored["continuation_carrier"] == "relay"


def test_an_unresolvable_carrier_supersedes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CARRIER_ENV, "hosted")
    assert cs._hook_carrier() is None
