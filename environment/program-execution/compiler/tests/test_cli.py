"""Gate E — minimal front-door UX (contract §15)."""

from __future__ import annotations

from pathlib import Path

from compiler.blueprint_validate import validate
from compiler.cli import run


def _fixture_repo(tmp_path: Path, *, with_git: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text(
        "Owner: Igor Beylin\n\nTest command: `pytest -q`\n", encoding="utf-8"
    )
    (repo / ".python-version").write_text("3.12\n", encoding="utf-8")
    if with_git:
        import subprocess

        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "remote",
                "add",
                "origin",
                "https://github.com/Quantum-L9/Cursor-Governance.git",
            ],
            check=True,
        )
    return repo


def test_happy_path_no_questionnaire(tmp_path: Path, capsys) -> None:
    repo = _fixture_repo(tmp_path)
    output = tmp_path / "blueprint"
    code = run(
        [
            "intent",
            "Evolve l9-devpack-compiler so a minimal goal compiles into a "
            "validator-clean Blueprint v2",
            "--repo-root",
            str(repo),
            "--output",
            str(output),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Intent parsed" in captured.out
    assert "Blueprint validation PASS" in captured.out
    assert "Program prepared for lock" in captured.out
    assert validate(output, mode="instantiated").ok


def test_target_flag_used_when_repo_evidence_absent(tmp_path: Path, capsys) -> None:
    repo = _fixture_repo(tmp_path, with_git=False)
    output = tmp_path / "blueprint"
    code = run(
        [
            "intent",
            "Simplify user invocation while preserving output quality",
            "--target",
            "Quantum-L9/Cursor-Governance",
            "--repo-root",
            str(repo),
            "--output",
            str(output),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Quantum-L9/Cursor-Governance" in captured.out


def test_missing_target_blocks_without_inventing_one(tmp_path: Path, capsys) -> None:
    repo = tmp_path / "bare"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("Owner: Igor Beylin\n", encoding="utf-8")
    output = tmp_path / "blueprint"
    code = run(
        [
            "intent",
            "Simplify user invocation while preserving output quality",
            "--repo-root",
            str(repo),
            "--output",
            str(output),
        ]
    )
    captured = capsys.readouterr()
    assert code != 0
    assert "no invented target" in captured.err
    assert not output.exists()


def test_authority_bearing_decision_asks_only_for_that(tmp_path: Path, capsys) -> None:
    repo = _fixture_repo(tmp_path)
    output = tmp_path / "blueprint"
    code = run(
        [
            "intent",
            "Make repo X achieve Y and keep going until verified",
            "--repo-root",
            str(repo),
            "--output",
            str(output),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "questionnaire" not in captured.out.lower()
