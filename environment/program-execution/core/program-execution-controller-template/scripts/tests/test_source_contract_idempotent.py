"""Registering the same Source Contract twice is one request, not a conflict.

The existing guard refuses a second registration outright, which is correct for
a *different* contract and wrong for an identical one. Re-preparing a campaign
that is already prepared re-drafts the same contract from the same blueprint, so
the strict guard turned an idempotent operation into a hard failure and forced
the caller to wipe the runtime to get back to a working state.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, register_contract, run_cli, source_contract, write_json


def _register(workspace: Path, path: Path, *extra: str) -> dict:
    return run_cli(
        "register-contract",
        "TASK-001",
        "--workspace",
        str(workspace),
        "--file",
        str(path),
        "--actor",
        "operator",
        *extra,
    )


def _differing_contract(temp: Path, name: str) -> Path:
    """A contract that is valid against the blueprint but is not the same document.

    Only the objective moves. Changing a writable path or a validation command
    would fail blueprint validation before the registration guard is ever
    consulted, which would test the wrong thing.
    """
    contract = source_contract("TASK-001")
    contract["objective"] = f"Write docs/result.txt ({name})"
    return write_json(temp / f"{name}.source.json", contract)


class SourceContractIdempotenceTest(unittest.TestCase):
    def test_registering_an_identical_contract_again_is_accepted(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            path = register_contract(temp, workspace)
            first = _register(workspace, path)

            again = _register(workspace, path)
            self.assertEqual(again["status"], "ALREADY_REGISTERED")
            self.assertEqual(
                again["digest"],
                first["digest"],
                "idempotent path reported a digest the runtime does not hold",
            )

    def test_a_conflicting_contract_still_requires_explicit_replacement(self) -> None:
        """The safety property the guard exists for must survive this change."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)

            with self.assertRaises(AssertionError) as ctx:
                _register(workspace, _differing_contract(temp, "conflicting"))
            self.assertIn("explicit replacement is required", str(ctx.exception))

    def test_the_idempotent_path_does_not_rewrite_the_registration(self) -> None:
        """A no-op must stay a no-op: same digest, same recorded path."""
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            path = register_contract(temp, workspace)
            target = workspace / "contracts" / "source" / "TASK-001.json"
            before = target.read_bytes()

            _register(workspace, path)
            self.assertEqual(target.read_bytes(), before)

    def test_explicit_replacement_of_a_differing_contract_still_works(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)

            result = _register(workspace, _differing_contract(temp, "replacement"), "--replace")
            self.assertEqual(result["status"], "REGISTERED")


if __name__ == "__main__":
    unittest.main()
