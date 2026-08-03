from __future__ import annotations

import unittest

from adapters.common.contracts import validate_contract

from conformance.helpers import valid_contract


class ContractBindingTests(unittest.TestCase):
    def test_valid_contract_binds_exact_digests(self) -> None:
        contract = valid_contract()
        binding = validate_contract(
            contract,
            expected_program_lock_digest=contract["program_digest"],
        )
        self.assertEqual(binding.task_id, "TASK-001")
        self.assertEqual(binding.program_lock_digest, contract["program_digest"])
        self.assertEqual(
            binding.rendered_contract_digest,
            contract["contract_digest"],
        )

    def test_changed_body_invalidates_contract_digest(self) -> None:
        contract = valid_contract()
        contract["objective"] = "Tampered objective"
        with self.assertRaises(Exception):
            validate_contract(contract)


if __name__ == "__main__":
    unittest.main()
