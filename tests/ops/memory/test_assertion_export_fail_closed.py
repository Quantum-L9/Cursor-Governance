"""A failed legacy mint cannot source a pre-existing file or preserve stale outputs."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
EXPORTER = ROOT / "ops/memory/export_agent_assertion_env.sh"
OUTPUT_KEYS = (
    "L9_MEMORY_AGENTS_DOOR_SECRET",
    "L9_MEMORY_AGENT_ASSERTION",
    "L9_MEMORY_AGENT_SIGNING_KEYS_JSON",
    "L9_MEMORY_AGENT_GRANTS_JSON",
    "L9_MEMORY_IDENTITY_ASSERTION_JSON",
    "L9_MEMORY_IDENTITY_ASSERTION_HMAC",
)


@pytest.mark.parametrize("mint_rc", [0, 1])
def test_only_successfully_minted_file_is_sourced_and_removed(tmp_path, mint_rc):
    home = tmp_path / "home"
    home.mkdir()
    output = tmp_path / "output.env"
    output.write_text("export L9_MEMORY_AGENT_ASSERTION=fresh-fixture\n", encoding="utf-8")
    output.chmod(0o600)
    maps = tmp_path / "maps.json"
    maps.write_text("{}\n", encoding="utf-8")
    interpreter = tmp_path / "fake-python"
    interpreter.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$FIXTURE_OUTPUT"\nexit "$FIXTURE_RC"\n', encoding="utf-8"
    )
    interpreter.chmod(0o755)
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "L9_MEMORY_AGENT_ID": "manus",
        "L9_MEMORY_SECRET_MAP": str(maps),
        "L9_MEMORY_GRANTS_MAP": str(maps),
        "L9_MEMORY_INTERPRETER": str(interpreter),
        "FIXTURE_OUTPUT": str(output),
        "FIXTURE_RC": str(mint_rc),
        **dict.fromkeys(OUTPUT_KEYS, "stale-fixture"),
    }
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; printf "%s|%s\\n" "$L9_ASSERTION_EXPORT_STATUS" '
            '"${L9_MEMORY_AGENT_ASSERTION-unset}"; env',
            "fixture",
            str(EXPORTER),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    if mint_rc:
        assert result.stdout.startswith("failed|unset\n")
        assert output.exists(), "Failed helper output is not owned and must not be deleted"
        assert "fresh-fixture" not in result.stdout
    else:
        assert result.stdout.startswith("minted|fresh-fixture\n")
        assert not output.exists()
    assert "stale-fixture" not in result.stdout


def test_missing_maps_clear_stale_outputs_without_exiting_sourcing_host(tmp_path):
    result = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; printf "%s|%s\\n" "$L9_ASSERTION_EXPORT_STATUS" '
            '"${L9_MEMORY_AGENT_ASSERTION-unset}"; env',
            "fixture",
            str(EXPORTER),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": os.environ["PATH"],
            "HOME": str(tmp_path),
            "L9_MEMORY_AGENT_ID": "manus",
            **dict.fromkeys(OUTPUT_KEYS, "stale-fixture"),
        },
    )
    assert result.returncode == 0
    assert result.stdout.startswith("skipped|unset\n")
    assert "stale-fixture" not in result.stdout
    assert list(tmp_path.iterdir()) == []
