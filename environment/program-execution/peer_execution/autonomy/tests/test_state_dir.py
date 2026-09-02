"""Every consumer of L9_AUTONOMY_STATE_DIR must resolve to the same root.

Commit 9f421ca moved the state directory out of the worktree and spelled it two
ways in the same change: ``~/.l9/autonomy`` in ``settings.template.json`` and
``$HOME/.l9/autonomy`` in ``web/environment.env.example``. Those are not
interchangeable to ``Path.expanduser()``, which expands ``~`` only.

``ops/autonomy/l4_local.py`` substitutes ``$HOME`` itself, so it resolved
correctly either way, while these modules did not. With the ``$HOME`` spelling —
the one ``verify_account_env.py`` told a human to paste — L4 wrote to the real
home directory and peer-execution wrote to ``<workspace>/$HOME/.l9/autonomy``:
autonomy state split across two roots, one of them a junk ``$HOME`` directory
inside the repository working tree.

These tests lock the equivalence rather than the spelling, so neither file can
drift away from the other again without failing here.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autonomy.bootstrap import _state_root
from autonomy.state_dir import expand_state_dir

from autonomy.cli import _root

SPELLINGS = ("~/.l9/autonomy", "$HOME/.l9/autonomy", "${HOME}/.l9/autonomy")


class StateDirEquivalenceTests(unittest.TestCase):
    def test_every_home_spelling_resolves_to_the_same_absolute_root(self) -> None:
        expected = Path.home() / ".l9" / "autonomy"
        for spelling in SPELLINGS:
            with self.subTest(spelling=spelling):
                self.assertEqual(expected, expand_state_dir(spelling))

    def test_no_spelling_leaves_a_literal_variable_component(self) -> None:
        """The failure mode was a path component named ``$HOME``."""
        for spelling in SPELLINGS:
            with self.subTest(spelling=spelling):
                parts = expand_state_dir(spelling).parts
                self.assertNotIn("$HOME", parts)
                self.assertNotIn("${HOME}", parts)

    def test_bootstrap_and_cli_agree_with_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for spelling in SPELLINGS:
                with (
                    self.subTest(spelling=spelling),
                    patch.dict(os.environ, {"L9_AUTONOMY_STATE_DIR": spelling}, clear=False),
                ):
                    self.assertEqual(_state_root(workspace), _root(None))
                    self.assertNotIn("$HOME", _state_root(workspace).parts)

    def test_l4_local_agrees_with_peer_execution(self) -> None:
        """The two independent implementations must not diverge again."""
        repo = Path(__file__).resolve().parents[5]
        import sys

        sys.path.insert(0, str(repo))
        from ops.autonomy import l4_local

        for spelling in SPELLINGS:
            with self.subTest(spelling=spelling):
                self.assertEqual(
                    l4_local._expand_state_dir(spelling, repo),
                    expand_state_dir(spelling),
                )

    def test_relative_value_stays_relative(self) -> None:
        """A relative default is the caller's to resolve, not this helper's."""
        self.assertFalse(expand_state_dir(".l9/autonomy").is_absolute())
        self.assertFalse(expand_state_dir(None).is_absolute())
        self.assertFalse(expand_state_dir("  ").is_absolute())

    def test_env_example_uses_a_spelling_plain_expanduser_handles(self) -> None:
        """The account variables field is stored literally and never shell-expanded.

        So whatever is pasted reaches Python as characters. ``~`` is the only
        spelling ``Path.expanduser()`` resolves on its own, which is what makes
        it the canonical one for a consumer that has not been hardened.
        """
        repo = Path(__file__).resolve().parents[5]
        example = repo / "environment/agents/adapters/claude-code/web/environment.env.example"
        line = next(
            ln
            for ln in example.read_text(encoding="utf-8").splitlines()
            if ln.startswith("L9_AUTONOMY_STATE_DIR=")
        )
        value = line.split("=", 1)[1]
        self.assertEqual(Path.home() / ".l9" / "autonomy", Path(value).expanduser())


if __name__ == "__main__":
    unittest.main()
