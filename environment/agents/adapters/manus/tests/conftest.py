"""Fixtures for the Manus governance tool-surface tests."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ADAPTER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ADAPTER_ROOT.parents[3]
if str(ADAPTER_ROOT) not in sys.path:
    sys.path.insert(0, str(ADAPTER_ROOT))

from tools.base import RuntimeContext  # noqa: E402


class RecordingRunner:
    """Deterministic subprocess stand-in; records every command it was given."""

    def __init__(self, responses: dict[str, dict[str, Any]] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[list[str]] = []

    def __call__(self, command: list[str], *, cwd: Path, timeout: int = 120) -> dict[str, Any]:
        self.calls.append(list(command))
        joined = " ".join(command)
        for needle, response in self.responses.items():
            if needle in joined:
                return {
                    "status": "completed",
                    "command": command,
                    "exit_code": 0,
                    "stdout": "",
                    "stderr": "",
                    **response,
                }
        return {
            "status": "completed",
            "command": command,
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
        }


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def make_context(tmp_path: Path) -> Callable[..., RuntimeContext]:
    def _make(
        responses: dict[str, dict[str, Any]] | None = None, runner: Any = None
    ) -> RuntimeContext:
        active = runner or RecordingRunner(responses)
        return RuntimeContext(tmp_path, runner=active)

    return _make


@pytest.fixture
def binding_payload() -> dict[str, Any]:
    return {
        "schema": "l9.host-binding.v1",
        "host": "manus",
        "status": "BOUND",
        "authority_root": "/home/l9/.github",
        "canonical_binding_ref": "l9.projection/cursor-governance-operating-plane@2",
        "default": {"status": "BOUND", "reason": None, "ref": "l9.projection/x@2"},
        "activations": ["always"],
        "blockers": [],
        "domains": {},
        "fail_open": True,
    }


@pytest.fixture
def binding_json(binding_payload: dict[str, Any]) -> str:
    return json.dumps(binding_payload)
