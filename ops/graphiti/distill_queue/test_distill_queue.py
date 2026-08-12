"""Unit tests for S3 distill queue enqueue (mocked aws CLI)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ops.graphiti.distill_queue import enqueue as enq  # noqa: E402


def test_job_content_hash_stable():
    a = enq.job_content_hash(session_id="s1", excerpt="hello")
    b = enq.job_content_hash(session_id="s1", excerpt="hello")
    c = enq.job_content_hash(session_id="s1", excerpt="hello!")
    assert a == b
    assert a != c
    assert len(a) == 64


def test_build_job_caps_excerpt():
    big = "x" * 20000
    job = enq.build_job(
        session_id="s1",
        group_id="cursor-governance",
        agent_id="cursor",
        transcript_excerpt=big,
    )
    assert job["schema_version"] == enq.SCHEMA_VERSION
    assert len(job["transcript_excerpt"]) == enq.EXCERPT_CAP
    assert job["content_hash"] == enq.job_content_hash(
        session_id="s1", excerpt=job["transcript_excerpt"]
    )


def test_enqueue_dry_run(monkeypatch):
    monkeypatch.setenv("MEMORY_DISTILL_S3_BUCKET", "l9-distill-test")
    result = enq.enqueue_job(
        session_id="s1",
        group_id="g",
        agent_id="cursor",
        transcript_excerpt="redacted excerpt",
        dry_run=True,
    )
    assert result["ok"] is True
    assert result["dry_run"] is True
    assert result["key"].endswith(".json")


def test_put_job_s3_calls_aws(monkeypatch):
    monkeypatch.setenv("MEMORY_DISTILL_S3_BUCKET", "l9-distill-test")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    calls: list = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")

    job = enq.build_job(
        session_id="s1",
        group_id="g",
        agent_id="cursor",
        transcript_excerpt="excerpt",
    )
    out = enq.put_job_s3(job, runner=fake_run)
    assert out["ok"] is True
    assert out["bucket"] == "l9-distill-test"
    assert "put-object" in calls[0]
    assert job["content_hash"] in out["key"]


def test_put_job_fail_loud(monkeypatch):
    monkeypatch.setenv("MEMORY_DISTILL_S3_BUCKET", "l9-distill-test")

    def fake_run(cmd, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="AccessDenied")

    job = enq.build_job(
        session_id="s1",
        group_id="g",
        agent_id="cursor",
        transcript_excerpt="excerpt",
    )
    with pytest.raises(RuntimeError, match="AccessDenied"):
        enq.put_job_s3(job, runner=fake_run)


def test_enqueue_enabled(monkeypatch):
    monkeypatch.delenv("MEMORY_DISTILL_S3_BUCKET", raising=False)
    assert enq.enqueue_enabled() is False
    monkeypatch.setenv("MEMORY_DISTILL_S3_BUCKET", "b")
    monkeypatch.setenv("MEMORY_DISTILL_ENQUEUE", "1")
    assert enq.enqueue_enabled() is True
    monkeypatch.setenv("MEMORY_DISTILL_ENQUEUE", "0")
    assert enq.enqueue_enabled() is False
