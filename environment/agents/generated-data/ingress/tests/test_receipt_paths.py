"""Receipt filenames are built from a validated segment, never a raw caller string."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

INGRESS = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
for entry in (str(INGRESS), str(REPO)):
    if entry not in sys.path:
        sys.path.insert(0, entry)


@pytest.fixture
def receipts(tmp_path, monkeypatch):
    monkeypatch.setenv("L9_RUNTIME_ROOT", str(tmp_path / "runtime"))
    spec = importlib.util.spec_from_file_location(
        "generated_data_ingress_receipts_under_test", INGRESS / "receipts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "digest", ["../../escape", "a/b", "..", ".", "", ".hidden", "x\\y", "sha 256", "a\x00b"]
)
def test_traversal_shaped_digests_are_refused(receipts, digest):
    with pytest.raises(ValueError):
        receipts._path(digest)
    with pytest.raises(ValueError):
        receipts.packet_evidence_path(digest)
    with pytest.raises(ValueError):
        receipts.quarantine_meta({"packet_digest": digest})


def test_a_non_string_digest_is_refused(receipts):
    with pytest.raises(ValueError):
        receipts._path(None)


@pytest.mark.parametrize("digest", ["a" * 64, "acc1", "none", "unknown", "0-9._A-Z"])
def test_safe_segments_are_accepted(receipts, digest, tmp_path):
    path = receipts._path(digest)
    assert path.name == f"{digest}.json"
    assert path.parent == receipts.generated_data_receipt_root() / "ingress"
    assert (tmp_path / "runtime") in path.parents


def test_write_ingress_refuses_before_writing_outside_the_receipt_root(receipts, tmp_path):
    body = {
        "acceptance_receipt_digest": "../../escape",
        "source_kind": "accepted_subagent_result",
        "outcome": "REJECTED",
        "reason": "test",
        "processor_job_id": None,
        "processing_status": "NOT_STARTED",
    }
    with pytest.raises(ValueError):
        receipts.write_ingress(body)
    assert not (tmp_path / "escape.json").exists()
    assert not list(tmp_path.rglob("escape.json"))


def test_load_ingress_refuses_traversal(receipts):
    with pytest.raises(ValueError):
        receipts.load_ingress("../../etc/passwd")


def test_environment_root_is_honoured(receipts, tmp_path):
    assert str(receipts._path("a" * 64)).startswith(os.environ["L9_RUNTIME_ROOT"])
