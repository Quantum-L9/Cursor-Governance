#!/usr/bin/env python3
"""The receipt plane's ratchet, and the regressions the audit found unpinned.

Every check here is static, AST, or a subprocess against a temporary
workspace. None of them asserts anything about a receipt file in CI, and
none may be changed to: these receipts live under gitignored `.l9/`, so a CI
job that required one would be unsatisfiable by construction and the only
thing it could teach is how to bypass it (CANONICAL_LAW §6.2.9 item 7).

What is ratcheted:

1. One writer per plane — `test_kernel_receipt_writers.py` owns the
   kernel-receipt case; this file generalizes the shape to any module that
   claims to be a receipt library.
2. A verifier re-derives. A reader that decides from recorded fields alone
   has reintroduced the trusted-verdict defect even if the schema looks v2.
3. A receipt module with zero importers is dead law. `kernel_predicates.py`
   sat complete, untested, and unimported while the gate it was written for
   kept accepting honor-system stamps; nothing detected that.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OPS = REPO / "ops"
PYTHON = sys.executable

# Modules whose job is to serve a receipt plane. Each must be imported by
# something, or it is a claim about behavior the running system does not have.
RECEIPT_LIBRARIES = (
    OPS / "autonomy" / "kernel_predicates.py",
    OPS / "autonomy" / "receipt_binding.py",
)

# (reader, at least one symbol it must call to re-derive rather than trust)
RECEIPT_READERS = (
    (
        OPS / "autonomy" / "kernel_gate.py",
        "verify_tree",
        {"run_predicates", "kernel_shas"},
    ),
    (
        OPS / "autonomy" / "l4_local.py",
        "_allow_from_receipt",
        {"tree_digest", "current_head"},
    ),
)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found — the ratchet is pinned to a function that moved")


def _called_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


class ReceiptLibrariesAreWired(unittest.TestCase):
    def test_no_receipt_library_sits_with_zero_importers(self) -> None:
        """Dead law reads as shipped hardening. It is not.

        `kernel_predicates.py` was a complete implementation of the evidence
        contract with no importers, while the gate it was written for still
        accepted a stamp. Nothing failed, so nothing was noticed.
        """
        sources = {
            path: path.read_text(encoding="utf-8") for path in OPS.rglob("*.py") if path.is_file()
        }
        for library in RECEIPT_LIBRARIES:
            module = library.stem
            importers = [
                path.relative_to(REPO).as_posix()
                for path, text in sources.items()
                if path != library
                and (f"import {module}" in text or f"from {module} import" in text)
            ]
            self.assertTrue(
                importers,
                f"{library.relative_to(REPO)} has zero importers under ops/ — "
                "wire it into the plane it serves or delete it",
            )

    def test_receipt_binding_is_a_library_not_a_writer(self) -> None:
        tree = _parse(OPS / "autonomy" / "receipt_binding.py")
        written = _called_names(tree)
        for forbidden in ("write_text", "write_bytes", "dump"):
            self.assertNotIn(
                forbidden,
                written,
                "receipt_binding must decide no policy and write no receipt, or it "
                "becomes a second writer of every plane it serves",
            )


class VerifiersReDerive(unittest.TestCase):
    def test_each_receipt_reader_recomputes_instead_of_trusting(self) -> None:
        """A v2 schema with a trusted read is the v1 defect wearing a new name."""
        for path, func_name, required in RECEIPT_READERS:
            with self.subTest(reader=f"{path.name}:{func_name}"):
                called = _called_names(_function(_parse(path), func_name))
                self.assertTrue(
                    called & required,
                    f"{path.relative_to(REPO)}:{func_name} calls none of {sorted(required)} — "
                    "it appears to decide from recorded receipt fields alone",
                )

    def test_kernel_gate_rejects_the_superseded_schema_by_name(self) -> None:
        """Item 5: reject with an upgrade path, never read as unknown."""
        source = (OPS / "autonomy" / "kernel_gate.py").read_text(encoding="utf-8")
        self.assertIn("SCHEMA_V1", source)
        self.assertIn("l9.kernel_receipt.v1", source)


class UnpinnedRegressionsFromTheAudit(unittest.TestCase):
    """Three behaviors that were already correct and could be silently lost."""

    def test_bare_record_kernels_is_refused(self) -> None:
        """Without both verdicts the CLI must not advance anything.

        `record-kernels` reads as "do the kernel step" to an agent in a hurry.
        It records a claim about work already done, so a bare invocation has
        nothing to record and must name both missing verdicts rather than
        default either one to passed.
        """
        proc = subprocess.run(
            [PYTHON, str(OPS / "autonomy" / "l4_local.py"), "record-kernels"],
            capture_output=True,
            text=True,
            cwd=str(REPO),
        )
        self.assertEqual(proc.returncode, 2)
        combined = proc.stdout + proc.stderr
        self.assertIn("--recursive-alignment", combined)
        self.assertIn("--validate-repair", combined)

    def test_make_l4_record_kernels_without_verdicts_exits_2(self) -> None:
        """The Makefile guard, pinned. Its removal would be a silent default."""
        env = dict(os.environ, L9_L4_LOCAL_AUTONOMY="1")
        proc = subprocess.run(
            ["make", "-n", "l4-record-kernels"],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            env=env,
        )
        # -n prints the recipe without running it, so the guard's text is the
        # assertion target: a real run needs the gov venv this test must not build.
        self.assertIn("RA and VR are required", proc.stdout + proc.stderr)
        self.assertIn("exit 2", proc.stdout + proc.stderr)

    def test_the_gmp_executor_does_not_record_kernels(self) -> None:
        """An executor cannot attest judgement it did not exercise.

        This was the falsification route in INC-2026-09-14-001: a program run
        stamping the receipt that is supposed to gate its own publication.
        """
        executor = REPO / "workflows" / "gmp_executor.py"
        tree = _parse(executor)
        called = _called_names(tree)
        self.assertNotIn("record", called, "gmp_executor must not call record()")
        source = executor.read_text(encoding="utf-8")
        self.assertNotIn("import kernel_gate", source)
        self.assertNotIn("from kernel_gate", source)


class CorpusExemptionSurvives(unittest.TestCase):
    """`/ff` is the flow the reverted coupling broke. It stays unbroken.

    `authorize_release` has no changed-path context, so it cannot distinguish
    a corpus-only changeset from a code one; requiring a kernel receipt there
    is forbidden (CANONICAL_LAW §6.2.9 item 6). The behavioral pin lives in
    `test_l4_local.py`; this is the static half, so a future agent cannot
    reintroduce the requirement and then adjust one test.
    """

    def test_authorize_release_never_requires_a_kernel_receipt(self) -> None:
        tree = _parse(OPS / "autonomy" / "l4_local.py")
        blocker = _function(tree, "kernel_evidence_blocker")
        source = ast.unparse(blocker)
        self.assertIn(
            "load_receipt(root) is None",
            source,
            "absence of a kernel receipt must return None (authorize), not a blocker",
        )

    def test_the_exemption_verdict_is_read_not_recomputed(self) -> None:
        """Only the changed-path reader may compute the exemption."""
        l4 = (OPS / "autonomy" / "l4_local.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "changed_are_corpus_only",
            l4,
            "l4_local must not recompute the corpus exemption — it has no changed-path "
            "context, which is exactly why eace25ed reverted the earlier coupling",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
