"""One grammar, three consumers, no divergence.

The defect this guards: the grammar used to live only inside the Claude
permission renderer, so a producer could emit a command that died at provider
dispatch. These cases are asserted against the shared validator *and* against
every consumer, because a shared module that consumers quietly bypass is not
actually shared.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
# APPEND, never insert(0): Program Execution needs its own PE-exclusive
# packages here, but `scripts` is a top-level name it SHARES with the
# repository root. Prepending would hand PE's `scripts/` that name for the
# whole process. See peer_execution.imports.pe_script.
if str(PE_ROOT) not in sys.path:
    sys.path.append(str(PE_ROOT))

from peer_execution.validation_command import (  # noqa: E402
    ValidationCommandError,
    validate_validation_command,
    validation_command_error,
)

# Composed shell, redirects, substitution and inline interpreters: each of these
# is refused by the peer permission ceiling, so no PE layer may emit one.
INADMISSIBLE = (
    "grep -q foo a.py && grep -q foo b.py",
    "ls -1 a b >/dev/null",
    'test -z "$(git status --porcelain)"',
    "python3 -c \"print('x')\"",
    'sh -c "echo x"',
    "gh pr view 123",
    "git add file",
)

# Single-operation commands a worker may run to prove its own work.
ADMISSIBLE = (
    "grep -q is_tracked ops/scripts/claude_projection.py",
    "test -s docs/file.md",
    "python3 -m pytest tests/ops/scripts -q",
    "bash -n scripts/example.sh",
    "git status --short",
    "git diff --check",
    "git ls-files ops/scripts/foo.py",
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SharedValidatorTests(unittest.TestCase):
    def test_inadmissible_commands_are_refused(self) -> None:
        for command in INADMISSIBLE:
            with self.subTest(command=command):
                with self.assertRaises(ValidationCommandError):
                    validate_validation_command(command)
                self.assertIsNotNone(validation_command_error(command))

    def test_admissible_commands_pass_through_unchanged(self) -> None:
        for command in ADMISSIBLE:
            with self.subTest(command=command):
                self.assertEqual(validate_validation_command(command), command)
                self.assertIsNone(validation_command_error(command))

    def test_empty_and_multiline_are_refused(self) -> None:
        for command in ("", "   ", "a\nb", "a\rb"):
            with self.subTest(command=command):
                with self.assertRaises(ValidationCommandError):
                    validate_validation_command(command)

    def test_error_is_a_valueerror_for_existing_callers(self) -> None:
        # The renderer's callers caught ValueError before the grammar moved out.
        self.assertTrue(issubclass(ValidationCommandError, ValueError))


class ConsumerParityTests(unittest.TestCase):
    """Every consumer must agree with the shared validator, case for case."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.renderer = _load(
            "permission_renderer_parity",
            PE_ROOT / "adapters/claude-code/permission_renderer.py",
        )
        cls.launchability = _load("launchability_parity", PE_ROOT / "scripts/launchability.py")
        cls.compiler = _load(
            "compile_campaign_source_parity", PE_ROOT / "scripts/compile_campaign_source.py"
        )

    def _render(self, command: str) -> dict:
        return self.renderer.render_permissions(
            {"allowed_actions": ["inspect"], "denied_actions": []},
            {"validation_commands": [command]},
        )

    def test_claude_permission_renderer_matches_the_shared_grammar(self) -> None:
        for command in INADMISSIBLE:
            with self.subTest(command=command, consumer="renderer"):
                with self.assertRaises(ValueError):
                    self._render(command)
        for command in ADMISSIBLE:
            with self.subTest(command=command, consumer="renderer"):
                self.assertIn(f"Bash({command})", self._render(command)["allowed"])

    def test_launchability_matches_the_shared_grammar(self) -> None:
        for command in INADMISSIBLE:
            with self.subTest(command=command, consumer="launchability"):
                task = {
                    "id": "TASK-001",
                    "execution_kind": "repo_local",
                    "definition_status": "ready",
                    "validation": [{"method": "command", "command_or_inspection": command}],
                }
                report = self.launchability.check_tasks([task], PE_ROOT, infer=False)
                codes = {
                    finding["code"]
                    for finding in report["findings"]
                    if finding["severity"] == "blocker"
                }
                self.assertIn("invalid_validation_command", codes)
        for command in ADMISSIBLE:
            with self.subTest(command=command, consumer="launchability"):
                task = {
                    "id": "TASK-001",
                    "execution_kind": "repo_local",
                    "definition_status": "ready",
                    "validation": [{"method": "command", "command_or_inspection": command}],
                }
                report = self.launchability.check_tasks([task], PE_ROOT, infer=False)
                codes = {finding["code"] for finding in report["findings"]}
                self.assertNotIn("invalid_validation_command", codes)

    def test_source_preflight_matches_the_shared_grammar(self) -> None:
        # The compiler consults the same validator; prove it rejects and accepts
        # the same set rather than re-deriving a private opinion.
        for command in INADMISSIBLE:
            with self.subTest(command=command, consumer="preflight"):
                self.assertIsNotNone(self.compiler.validation_command_error(command))
        for command in ADMISSIBLE:
            with self.subTest(command=command, consumer="preflight"):
                self.assertIsNone(self.compiler.validation_command_error(command))


class SynthesisInvariantTests(unittest.TestCase):
    """Launchability must be incapable of synthesizing an inadmissible command."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.launchability = _load("launchability_synthesis", PE_ROOT / "scripts/launchability.py")

    def test_multiple_writable_paths_become_separate_valid_commands(self) -> None:
        task = {
            "id": "TASK-001",
            "execution_kind": "repo_local",
            "definition_status": "ready",
            "writable_paths": ["docs/a.md", "docs/b.md", "docs/c.md"],
        }
        commands = self.launchability.infer_validation_commands(task, PE_ROOT)
        self.assertEqual(
            commands,
            ["test -s docs/a.md", "test -s docs/b.md", "test -s docs/c.md"],
        )
        for command in commands:
            self.assertEqual(validate_validation_command(command), command)
        self.assertFalse(
            any(">" in command or "ls -1" in command for command in commands),
            msg="the redirect form that died at provider dispatch came back",
        )

    def test_single_path_still_synthesizes_one_presence_check(self) -> None:
        task = {
            "id": "TASK-001",
            "execution_kind": "repo_local",
            "definition_status": "ready",
            "writable_paths": ["docs/only.md"],
        }
        commands = self.launchability.infer_validation_commands(task, PE_ROOT)
        self.assertEqual(commands, ["test -s docs/only.md"])
        self.assertEqual(validate_validation_command(commands[0]), commands[0])

    def test_every_synthesis_shape_is_admissible(self) -> None:
        shapes = (
            ["tests/test_thing.py"],
            ["scripts/example.sh", "scripts/other.bash"],
            ["docs/a.md", "docs/b.md"],
        )
        for paths in shapes:
            with self.subTest(paths=paths):
                task = {
                    "id": "TASK-001",
                    "execution_kind": "repo_local",
                    "definition_status": "ready",
                    "writable_paths": paths,
                }
                for command in self.launchability.infer_validation_commands(task, PE_ROOT):
                    self.assertEqual(validate_validation_command(command), command)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
