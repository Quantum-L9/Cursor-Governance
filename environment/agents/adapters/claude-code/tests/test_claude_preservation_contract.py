#!/usr/bin/env python3
"""Non-regression suite for the Claude Code Preservation Contract.

Contract: ``docs/CLAUDE_CODE_PRESERVATION_CONTRACT.md``.

Claude Code is an independent consumer of the canonical L9 skill corpus. Work
that virtualizes, bounds, or otherwise reshapes *Cursor* skill discovery must
leave Claude Code's discovery, availability, invocation tier, and routing
untouched. These tests are the mechanical form of that promise, one test class
per validation clause:

    V-CC-001  projection equivalence      -> ClaudeProjectionEquivalenceTests
    V-CC-002  no Cursor dependency        -> ClaudeIndependenceTests
    V-CC-003  no cardinality regression   -> ClaudeCardinalityTests
    V-CC-004  no removal regression       -> ClaudeRemovalTests
    V-CC-005  no adapter mutation         -> ClaudeAdapterOwnershipTests

The suite is deliberately *baseline-attested* rather than value-hardcoded. A
route target or invocation tier pinned inline would either rot on every
legitimate change or invite a silent edit. Pinning the whole surface to one
reviewed baseline file means any Claude Code behavior change fails here and can
only be cleared by re-attesting the baseline on purpose — which is exactly the
"independent justification" CC-006 requires.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "CANONICAL_LAW.md").is_file():
            return parent
    raise RuntimeError(f"governance repo root not found from {start}")


ROOT = _repo_root(Path(__file__).resolve().parent)
SNAPSHOT = ROOT / "ops" / "scripts" / "claude_projection_snapshot.py"
BASELINE = (
    ROOT
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "baseline"
    / "claude-projection-baseline.json"
)
RECONCILE_SKILLS = ROOT / "ops" / "scripts" / "reconcile_claude_l9_skills.py"
CLAUDE_ADAPTER_DIR = ROOT / "environment" / "agents" / "adapters" / "claude-code"
CURSOR_ADAPTER_DIR = ROOT / "environment" / "agents" / "adapters" / "cursor"


def _run(*argv: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *argv],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class ClaudeProjectionEquivalenceTests(unittest.TestCase):
    """V-CC-001 — the Claude projection equals the attested baseline."""

    def test_projection_matches_baseline(self) -> None:
        result = _run(str(SNAPSHOT), "--root", str(ROOT), "--check")
        self.assertEqual(
            0,
            result.returncode,
            "Claude Code projection drifted from the attested baseline "
            "(CC-001/CC-006). Drift detail:\n" + result.stdout + result.stderr,
        )

    def test_baseline_is_committed_and_wellformed(self) -> None:
        self.assertTrue(BASELINE.is_file(), f"missing attested baseline: {BASELINE}")
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.assertEqual("l9.claude-projection-snapshot.v1", data["schema"])
        self.assertGreater(data["canonical_skill_count"], 0)
        self.assertEqual(
            data["canonical_skill_count"],
            len(data["canonical_skills"]),
            "baseline skill count disagrees with its own skill list",
        )


class ClaudeIndependenceTests(unittest.TestCase):
    """V-CC-002 / CC-007 / CC-009 — Claude works with Cursor entirely absent."""

    def test_snapshot_is_repository_pure(self) -> None:
        """No Cursor runtime state, no receipt, no gateway, and no HOME reliance."""
        with tempfile.TemporaryDirectory() as temp:
            empty_home = Path(temp) / "home"
            empty_home.mkdir()
            env = dict(os.environ)
            env["HOME"] = str(empty_home)
            env.pop("CURSOR_CONVERSATION_ID", None)

            first = _run(str(SNAPSHOT), "--root", str(ROOT), env=env)
            self.assertEqual(0, first.returncode, first.stderr)

            # Same tree, real HOME: the surface must not depend on the caller.
            second = _run(str(SNAPSHOT), "--root", str(ROOT))
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertEqual(
                first.stdout,
                second.stdout,
                "Claude projection changed with HOME — it reads runtime state it must not",
            )

            leaked = sorted(p.name for p in empty_home.iterdir())
            self.assertEqual([], leaked, f"snapshot wrote runtime state into HOME: {leaked}")

    def test_no_cursor_runtime_imports_in_claude_adapter(self) -> None:
        """CC-007 — the Claude adapter must not import Cursor-only modules."""
        # Cursor-plane modules: route receipts, per-conversation identity, and
        # canonical-path materialization all belong to the Cursor boundary.
        forbidden = ("receipt", "session_locator", "materialize")
        offenders: list[str] = []
        for path in sorted(CLAUDE_ADAPTER_DIR.rglob("*.py")):
            if "tests" in path.parts:
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for module in forbidden:
                    # Import forms only, so prose and unrelated identifiers
                    # (a local `receipt` variable) do not raise a false alarm.
                    if f"skill_routing.{module}" in stripped or f"import {module}" in stripped:
                        offenders.append(f"{path.relative_to(ROOT)}:{lineno} -> {module}")
        self.assertEqual(
            [],
            offenders,
            f"Claude adapter gained a Cursor-plane runtime dependency (CC-007): {offenders}",
        )


class ClaudeCardinalityTests(unittest.TestCase):
    """V-CC-003 — a newly added canonical skill still reaches Claude Code."""

    def _fixture(self, root: Path, names: tuple[str, ...]) -> None:
        for name in names:
            skill = root / "skills" / name
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: fixture skill\n---\n",
                encoding="utf-8",
            )
        generated = root / "ops" / "generated"
        generated.mkdir(parents=True)
        (generated / "skill-registry.json").write_text(
            json.dumps(
                {
                    "source_manifest_sha256": "fixture",
                    "skills": [{"name": n, "path": f"skills/{n}"} for n in names],
                }
            ),
            encoding="utf-8",
        )
        rules = root / "environment" / "generated" / "llm-rules"
        rules.mkdir(parents=True)
        (rules / "l9-skill-routing.md").write_text("# routing\n", encoding="utf-8")

    def test_added_canonical_skill_is_projected_to_claude(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "governance"
            workspace = base / "workspace"
            workspace.mkdir()
            # A corpus that grew by one skill relative to the prior generation.
            self._fixture(root, ("l9-alpha", "l9-beta", "l9-newly-added"))

            result = _run(
                str(RECONCILE_SKILLS),
                "--root",
                str(root),
                "--scope",
                "project",
                "--workspace",
                str(workspace),
            )
            self.assertEqual(0, result.returncode, result.stderr)

            projected = workspace / ".claude" / "skills" / "l9-newly-added"
            self.assertTrue(
                projected.is_symlink(),
                "a new canonical skill did not reach Claude Code discovery "
                "(V-CC-003): Claude cardinality must track the canonical corpus, "
                "never a bounded native projection",
            )

    def test_added_canonical_skill_reaches_user_scope(self) -> None:
        """CC-002 names both roots; ~/.claude/skills must track the corpus too."""
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "governance"
            home = base / "home"
            home.mkdir()
            self._fixture(root, ("l9-alpha", "l9-newly-added"))

            env = dict(os.environ)
            env["HOME"] = str(home)
            result = _run(
                str(RECONCILE_SKILLS),
                "--root",
                str(root),
                "--scope",
                "user",
                env=env,
            )
            self.assertEqual(0, result.returncode, result.stderr)

            projected = home / ".claude" / "skills" / "l9-newly-added"
            self.assertTrue(
                projected.is_symlink(),
                "a new canonical skill did not reach ~/.claude/skills (CC-002): "
                f"stdout={result.stdout}",
            )

    def test_claude_projection_tracks_full_canonical_corpus(self) -> None:
        """Claude is not a bounded-discovery surface: every skill is projected."""
        snapshot = json.loads(_run(str(SNAPSHOT), "--root", str(ROOT)).stdout or "{}")
        corpus = sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file())
        self.assertEqual(
            corpus,
            snapshot["canonical_skills"],
            "Claude Code's projected skill set diverged from the canonical corpus "
            "under skills/ (CC-002/CC-005)",
        )


class ClaudeRemovalTests(unittest.TestCase):
    """V-CC-004 — no canonical skill silently leaves Claude Code."""

    def test_no_baseline_skill_was_removed(self) -> None:
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        current = json.loads(_run(str(SNAPSHOT), "--root", str(ROOT)).stdout or "{}")
        missing = sorted(set(baseline["canonical_skills"]) - set(current["canonical_skills"]))
        self.assertEqual(
            [],
            missing,
            f"skills disappeared from Claude Code discovery (V-CC-004): {missing}",
        )

    def test_claude_skill_roots_are_not_suppressed(self) -> None:
        """CC-002 — the Claude adapter still declares its own discovery roots."""
        roots_file = ROOT / "environment" / "skill-adapters" / "SKILL_ADAPTER_ROOTS.yaml"
        text = roots_file.read_text(encoding="utf-8")
        self.assertIn(
            ".claude/skills",
            text,
            "the Claude Code skill root was removed from SKILL_ADAPTER_ROOTS.yaml (CC-002/CC-003)",
        )


class ClaudeAdapterOwnershipTests(unittest.TestCase):
    """V-CC-005 / CC-003 / CC-010 — Cursor tooling never writes Claude state."""

    def test_cursor_adapter_does_not_write_claude_paths(self) -> None:
        if not CURSOR_ADAPTER_DIR.is_dir():
            self.skipTest("no Cursor adapter directory in this tree")

        write_markers = (
            "write_text",
            "os.replace",
            "shutil.copy",
            "shutil.rmtree",
            "unlink(",
            "mkdir(",
            "symlink",
        )
        offenders: list[str] = []
        for path in sorted(CURSOR_ADAPTER_DIR.rglob("*.py")):
            if "tests" in path.parts:
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if ".claude" not in line:
                    continue
                if any(marker in line for marker in write_markers):
                    offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
        self.assertEqual(
            [],
            offenders,
            "Cursor adapter code mutates Claude Code adapter state (V-CC-005): "
            + "; ".join(offenders),
        )

    def test_claude_reconcilers_remain_the_claude_authority(self) -> None:
        """CC-003 — Claude skill/settings ownership stays with its own reconcilers."""
        for script in (
            ROOT / "ops" / "scripts" / "reconcile_claude_l9_skills.py",
            ROOT / "ops" / "scripts" / "reconcile_claude_settings.py",
        ):
            self.assertTrue(
                script.is_file(),
                f"the authoritative Claude Code reconciler is missing: {script}",
            )


if __name__ == "__main__":
    unittest.main()
