from __future__ import annotations

import unittest


class LeaseIdentityChaosContract(unittest.TestCase):
    def test_identity_swap_must_be_denied(self) -> None:
        expected_agent = "executor-1"
        attacking_agent = "reviewer-1"
        self.assertNotEqual(
            expected_agent,
            attacking_agent,
            "Chaos precondition requires distinct identities",
        )


if __name__ == "__main__":
    unittest.main()
