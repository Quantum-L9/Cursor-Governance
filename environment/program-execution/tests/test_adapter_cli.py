from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from adapters.common.digests import digest_object
from conformance.helpers import PROGRAM_DIGEST, valid_contract


class AdapterCliTests(unittest.TestCase):
    def _run(
        self,
        root: Path,
        args: list[str],
        environment: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(root / "scripts/adapter_cli.py"), *args],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def test_probe_dispatch_collect_across_processes(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            candidate = temporary / "candidate"
            candidate.mkdir()
            (candidate / "stable.txt").write_text("stable\n", encoding="utf-8")
            runtime = temporary / "runtime"
            contract = valid_contract(
                requested_actions=["verify"],
                allowed_actions=["verify"],
            )
            contract.update(
                {
                    "candidate_directory": str(candidate),
                    "verification_commands": [["python3", "-c", "print('verified')"]],
                    "candidate_sha": "3" * 40,
                    "declared_changed_files": ["stable.txt"],
                    "observed_changed_files": ["stable.txt"],
                }
            )
            contract.pop("contract_digest")
            contract["contract_digest"] = digest_object(contract)
            contract_path = temporary / "contract.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")

            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(root)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["L9_PROGRAM_HOME"] = str(temporary)

            probe = self._run(
                root,
                [
                    "probe",
                    "--adapter",
                    "ci-generic-shell",
                    "--runtime",
                    str(runtime),
                    "--program-lock-digest",
                    PROGRAM_DIGEST,
                ],
                environment,
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)

            dispatch = self._run(
                root,
                [
                    "dispatch",
                    "--adapter",
                    "ci-generic-shell",
                    "--runtime",
                    str(runtime),
                    "--contract",
                    str(contract_path),
                ],
                environment,
            )
            self.assertEqual(dispatch.returncode, 0, dispatch.stderr)
            dispatch_id = json.loads(dispatch.stdout)["prepare"]["dispatch_id"]

            collect = self._run(
                root,
                [
                    "collect",
                    "--adapter",
                    "ci-generic-shell",
                    "--runtime",
                    str(runtime),
                    "--dispatch-id",
                    dispatch_id,
                ],
                environment,
            )
            self.assertEqual(collect.returncode, 0, collect.stderr)
            result = json.loads(collect.stdout)
            self.assertEqual(
                result["schema"],
                "program-execution-controller.verification-receipt.v2",
            )


if __name__ == "__main__":
    unittest.main()
