from __future__ import annotations

import sys
import unittest

from helpers import SCRIPTS

sys.path.insert(0, str(SCRIPTS))
from pec.contracts import ContractError, normalize_repo_path, path_allowed


class ScopeTest(unittest.TestCase):
    def test_scope_fail_closed(self):
        self.assertTrue(path_allowed("docs/result.txt", ["docs/"]))
        self.assertFalse(path_allowed("src/result.txt", ["docs/"]))
        with self.assertRaises(ContractError):
            normalize_repo_path("../escape.txt")


if __name__ == "__main__":
    unittest.main()
