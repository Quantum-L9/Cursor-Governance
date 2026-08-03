from __future__ import annotations

import unittest

from adapters.common.contracts import validate_contract
from adapters.common.errors import AdapterFailure, CanonicalErrorCode

from conformance.helpers import valid_contract


class AuthorityNarrowingTests(unittest.TestCase):
    def test_requested_action_must_be_inside_ceiling(self) -> None:
        contract = valid_contract(
            requested_actions=["local_write"],
            allowed_actions=["inspect"],
        )
        with self.assertRaises(AdapterFailure) as context:
            validate_contract(contract)
        self.assertEqual(
            context.exception.code,
            CanonicalErrorCode.AUTHORIZATION_INFLATION,
        )

    def test_merge_is_globally_forbidden(self) -> None:
        contract = valid_contract(
            requested_actions=["merge"],
            allowed_actions=["merge"],
        )
        with self.assertRaises(AdapterFailure):
            validate_contract(contract)


if __name__ == "__main__":
    unittest.main()
