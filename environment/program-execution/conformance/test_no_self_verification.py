from __future__ import annotations

import unittest


def enforce_independent_verifier(worker_adapter_id: str, verifier_adapter_id: str) -> None:
    if worker_adapter_id == verifier_adapter_id:
        raise ValueError("worker adapter cannot independently verify itself")


class NoSelfVerificationTests(unittest.TestCase):
    def test_same_adapter_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            enforce_independent_verifier("claude-code-direct", "claude-code-direct")

    def test_distinct_adapter_is_accepted(self) -> None:
        enforce_independent_verifier("claude-code-direct", "ci-generic-shell")


if __name__ == "__main__":
    unittest.main()
