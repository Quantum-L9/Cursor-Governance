"""trailing-whitespace must preserve Markdown hard line breaks.

Two trailing spaces are a Markdown hard line break, not stray whitespace.
`run_pr_precommit.sh` runs THIS config against consumer workspaces
(`--config "$GOV_PRECOMMIT_CONFIG"`), so a missing flag here rewrites
generator-owned bytes in every governed repo: l9-harness
`scripts/update_manifest.py` emits ``Package: `…`  `` and its
`scripts/verify_generated.py` compares raw bytes, turning the strip into
"generated artifact drift" that the generator immediately undoes — a
formatter/generator oscillation with no fixed point.

`mdc` is required alongside `md`: `rules/*.mdc` bodies are copied verbatim
into `environment/generated/llm-rules/*.md` by `project_llm_rules.py`, so
protecting only the projection strips the source and propagates the loss
into a generated file on the next sync.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".pre-commit-config.yaml"

# Extensions whose two-space hard breaks must survive the writer hook.
REQUIRED_MARKDOWN_EXTS = {"md", "mdc"}

HARD_BREAK = "Package: `l9-harness`  \n"
SINGLE_TRAILING = "accidental single trailing space \n"
BLANK_WITH_SPACES = "   \n"
FIXTURE = f"# Manifest\n\n{HARD_BREAK}next line\n{SINGLE_TRAILING}{BLANK_WITH_SPACES}tail\n"


def _hook(hook_id: str) -> dict:
    data = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    for repo in data["repos"]:
        for hook in repo.get("hooks") or []:
            if hook.get("id") == hook_id:
                return hook
    raise AssertionError(f"hook {hook_id} missing from {CONFIG}")


def _declared_markdown_exts() -> set[str]:
    """Extensions declared via --markdown-linebreak-ext, normalized."""
    exts: set[str] = set()
    for arg in _hook("trailing-whitespace").get("args") or []:
        if arg.startswith("--markdown-linebreak-ext="):
            value = arg.split("=", 1)[1]
            exts |= {part.strip().lstrip(".").lower() for part in value.split(",")}
    return exts


def test_trailing_whitespace_declares_markdown_hardbreak_exts() -> None:
    """The config arg that makes the hook Markdown-aware must be present."""
    assert REQUIRED_MARKDOWN_EXTS <= _declared_markdown_exts()


def test_declared_exts_cover_every_markdown_source_in_tree() -> None:
    """Any tracked extension carrying real hard breaks must be declared.

    Guards the projection pair: protecting `.md` while leaving `.mdc`
    unprotected strips the source and regenerates the loss downstream.
    """
    tracked = subprocess.run(
        ["git", "ls-files", "*.md", "*.mdc"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()

    carrying: set[str] = set()
    for rel in tracked:
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line in text.splitlines():
            # A hard break is non-blank content followed by >= 2 spaces.
            if line.strip() and line.endswith("  "):
                carrying.add(path.suffix.lstrip(".").lower())
                break

    assert carrying <= _declared_markdown_exts(), (
        f"extensions carrying Markdown hard breaks but not declared: "
        f"{sorted(carrying - _declared_markdown_exts())}"
    )


@pytest.mark.skipif(
    shutil.which("pre-commit") is None,
    reason="pre-commit CLI absent; the gate itself fails closed on this (run_pr_precommit.sh)",
)
@pytest.mark.parametrize("suffix", sorted(REQUIRED_MARKDOWN_EXTS))
def test_hook_preserves_hard_break_and_still_cleans_junk(tmp_path: Path, suffix: str) -> None:
    """Behavioral proof against the real pinned hook, per declared extension."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    target = tmp_path / f"MANIFEST.{suffix}"
    target.write_text(FIXTURE, encoding="utf-8")

    subprocess.run(
        [
            "pre-commit",
            "run",
            "trailing-whitespace",
            "--config",
            str(CONFIG),
            "--files",
            str(target),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    result = target.read_text(encoding="utf-8")
    # The semantic hard break survives byte-for-byte.
    assert HARD_BREAK in result
    # Ordinary hygiene is unchanged: junk whitespace is still removed.
    assert SINGLE_TRAILING not in result
    assert "accidental single trailing space\n" in result
    assert BLANK_WITH_SPACES not in result


@pytest.mark.skipif(
    shutil.which("pre-commit") is None,
    reason="pre-commit CLI absent; the gate itself fails closed on this (run_pr_precommit.sh)",
)
def test_non_markdown_still_loses_trailing_whitespace(tmp_path: Path) -> None:
    """The flag is extension-scoped: non-Markdown text is untouched by it."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    target = tmp_path / "notes.txt"
    target.write_text(HARD_BREAK, encoding="utf-8")

    subprocess.run(
        ["pre-commit", "run", "trailing-whitespace", "--config", str(CONFIG), "--files", str(target)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert target.read_text(encoding="utf-8") == "Package: `l9-harness`\n"
