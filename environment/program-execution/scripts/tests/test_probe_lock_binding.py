"""PE-F15: probes bind to a real Program Lock or say plainly that they do not."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from peer_execution.imports import pe_script

_cli = pe_script("peer_execution_cli")
_probe = pe_script("probe_execution_adapters")


class ProbeLockBindingTests(unittest.TestCase):
    def test_cli_probe_without_a_lock_digest_is_refused(self) -> None:
        args = unittest.mock.Mock(program_lock_digest=None, runtime=None)
        with unittest.mock.patch.object(_cli, "_binding") as binding:
            binding.return_value = unittest.mock.Mock(provider_ref="cursor-foreground")
            with (
                tempfile.TemporaryDirectory() as raw,
                unittest.mock.patch.dict("os.environ", {"L9_PROGRAM_ADAPTER_RUNTIME": raw}),
                self.assertRaises(ValueError) as ctx,
            ):
                _cli.command_probe(args)
        self.assertIn("--program-lock-digest is required", str(ctx.exception))

    def test_inventory_sentinel_is_named_and_confined(self) -> None:
        digest, kind = _probe._lock_binding(None)
        self.assertEqual(kind, "inventory_sentinel")
        self.assertEqual(digest, _probe.INVENTORY_PROBE_LOCK_DIGEST)
        real = "sha256:" + "a" * 64
        self.assertEqual(_probe._lock_binding(real), (real, "program_lock"))
        with tempfile.TemporaryDirectory() as raw:
            runtime = Path(raw) / "programs" / "live-campaign"
            argv = ["probe_execution_adapters.py", "--runtime", str(runtime)]
            with (
                unittest.mock.patch.object(sys, "argv", argv),
                unittest.mock.patch.dict("os.environ", {"L9_PROGRAM_LOCK_DIGEST": ""}),
                redirect_stderr(io.StringIO()) as err,
                self.assertRaises(SystemExit) as ctx,
            ):
                _probe.main()
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn("sentinel-bound receipts", err.getvalue())
