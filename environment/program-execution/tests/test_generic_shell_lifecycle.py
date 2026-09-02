from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adapters.common.digests import digest_object
from adapters.common.models import ProbeContext
from adapters.common.schema_registry import SchemaRegistry
from conformance.helpers import PROGRAM_DIGEST, valid_contract
from peer_execution.imports import pe_script

instantiate = pe_script("provider_loader").instantiate


class GenericShellLifecycleTests(unittest.TestCase):
    def test_probe_dispatch_collect_returns_core_verification_receipt(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            candidate = temporary / "candidate"
            candidate.mkdir()
            (candidate / "example.txt").write_text("stable\n", encoding="utf-8")
            contract = valid_contract(
                requested_actions=["verify"],
                allowed_actions=["verify"],
            )
            contract["candidate_directory"] = str(candidate)
            contract["verification_commands"] = [["python3", "-c", "print('verified')"]]
            contract["candidate_sha"] = "3" * 40
            contract["declared_changed_files"] = ["example.txt"]
            contract["observed_changed_files"] = ["example.txt"]
            contract.pop("contract_digest")
            contract["contract_digest"] = digest_object(contract)

            adapter = instantiate("ci-generic-shell", temporary / "runtime")
            capability = adapter.probe(
                ProbeContext(
                    repository_root=str(root.parents[1]),
                    runtime_root=str(temporary / "runtime"),
                    program_lock_digest=PROGRAM_DIGEST,
                )
            )
            self.assertEqual(capability.status, "PASS")
            prepared = adapter.prepare(contract)
            dispatched = adapter.dispatch({"dispatch_id": prepared.dispatch_id})
            self.assertEqual(dispatched.status, "PASS")
            result = adapter.collect(str(prepared.dispatch_id))
            self.assertEqual(
                result["schema"],
                "program-execution-controller.verification-receipt.v2",
            )
            self.assertEqual(
                SchemaRegistry(root).validate_terminal_receipt(result),
                [],
            )
            self.assertEqual(
                (candidate / "example.txt").read_text(encoding="utf-8"),
                "stable\n",
            )

    def test_failed_verification_receipt_is_collectable(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            candidate = temporary / "candidate"
            candidate.mkdir()
            contract = valid_contract(
                requested_actions=["verify"],
                allowed_actions=["verify"],
            )
            contract["candidate_directory"] = str(candidate)
            contract["verification_commands"] = [["python3", "-c", "raise SystemExit(3)"]]
            contract["candidate_sha"] = "3" * 40
            contract["declared_changed_files"] = []
            contract["observed_changed_files"] = []
            contract.pop("contract_digest")
            contract["contract_digest"] = digest_object(contract)
            adapter = instantiate("ci-generic-shell", temporary / "runtime")
            adapter.probe(
                ProbeContext(
                    repository_root=str(root.parents[1]),
                    runtime_root=str(temporary / "runtime"),
                    program_lock_digest=PROGRAM_DIGEST,
                )
            )
            prepared = adapter.prepare(contract)
            dispatched = adapter.dispatch({"dispatch_id": prepared.dispatch_id})
            self.assertEqual(dispatched.status, "FAIL")
            result = adapter.collect(str(prepared.dispatch_id))
            self.assertEqual(result["verdict"], "FAILED")
            self.assertEqual(
                SchemaRegistry(root).validate_terminal_receipt(result),
                [],
            )


if __name__ == "__main__":
    unittest.main()
