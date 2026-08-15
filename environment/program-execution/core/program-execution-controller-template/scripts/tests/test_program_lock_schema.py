from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import SCRIPTS, make_blueprint

sys.path.insert(0, str(SCRIPTS))
from pec.blueprint import verify_program_lock, write_program_lock


class ProgramLockSchemaTest(unittest.TestCase):
    def test_writer_lock_validates_and_rejects_extra_fields(self) -> None:
        with TemporaryDirectory() as raw:
            blueprint = make_blueprint(Path(raw) / "blueprint")
            lock_path = Path(raw) / "program-lock.json"
            lock = write_program_lock(blueprint, lock_path)
            self.assertIn("do_not_build", lock)
            self.assertIn("current_state", lock)
            ok, errors = verify_program_lock(lock_path)
            self.assertTrue(ok, errors)
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            payload["unexpected_field"] = True
            lock_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            ok, errors = verify_program_lock(lock_path)
            self.assertFalse(ok)
            self.assertTrue(any("unexpected_field" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
