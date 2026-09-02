from __future__ import annotations

import ast
import unittest
from pathlib import Path

import yaml
from peer_execution.errors import CanonicalErrorCode, canonical_code_for, load_error_mapping

SUBSYSTEM = Path(__file__).resolve().parents[1]


def _emitted_codes(source: str) -> set[str]:
    """String literals assigned to `adapter_error_code`, by name or keyword."""
    codes: set[str] = set()
    tree = ast.parse(source)
    values: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "adapter_error_code"
            for target in node.targets
        ):
            values.append(node.value)
        elif isinstance(node, ast.keyword) and node.arg == "adapter_error_code":
            values.append(node.value)

    def _results(node: ast.AST) -> None:
        # Only literals in result position count: a comparison operand inside
        # the condition (`gates["x"] != "PASS"`) is not a code being emitted.
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            codes.add(node.value)
        elif isinstance(node, ast.IfExp):
            _results(node.body)
            _results(node.orelse)

    for value in values:
        _results(value)
    return codes


class FailureMappingTests(unittest.TestCase):
    def test_required_canonical_errors_are_mapped(self) -> None:
        path = SUBSYSTEM / "registry/EXECUTION_ERROR_MAPPING.yaml"
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        text = str(value)
        for code in (
            "PROGRAM_LOCK_STALE",
            "AUTHORIZATION_INFLATION",
            "REPOSITORY_STATE_DRIFT",
            "SCOPE_VIOLATION",
            "VALIDATION_FAILURE",
            "EVIDENCE_INVALID_OR_STALE",
            "LEASE_EXPIRED",
        ):
            self.assertIn(code, text)

    def test_the_mapping_registry_is_executable(self) -> None:
        mapping = load_error_mapping()
        self.assertEqual(mapping["HOST_EXECUTION_FAILED"], CanonicalErrorCode.VALIDATION_FAILURE)
        self.assertEqual(
            canonical_code_for("TARGET_STATE_DRIFT"), CanonicalErrorCode.REPOSITORY_STATE_DRIFT
        )
        self.assertIsNone(canonical_code_for("NOT_A_REGISTERED_CODE"))
        self.assertIsNone(canonical_code_for(None))

    def test_every_adapter_code_an_adapter_emits_is_registered(self) -> None:
        """A code an adapter reports must resolve to a canonical code."""
        registered = set(load_error_mapping())
        emitted: dict[str, set[str]] = {}
        for path in (SUBSYSTEM / "adapters").rglob("*.py"):
            if "tests" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            if "adapter_error_code" not in text:
                continue
            for code in _emitted_codes(text):
                emitted.setdefault(code, set()).add(str(path.relative_to(SUBSYSTEM)))
        self.assertTrue(emitted, "no adapter names its failures")
        unregistered = {code: files for code, files in emitted.items() if code not in registered}
        self.assertEqual(unregistered, {})


if __name__ == "__main__":
    unittest.main()
