"""Runtime binding: foreign, stale, and ambiguous runtimes must not silently win."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from ops.memory import runtime_binding as rb

CONTRACT = "memory-control-plane/v1"
EXPECTED_VERSION = rb.BindingManifest.load().expected_package_version


def capabilities_payload(
    *, version: str = EXPECTED_VERSION, contract: str = CONTRACT, drop: Sequence[str] = ()
) -> dict[str, Any]:
    cli_ops = {
        "resolve": "resolve",
        "health": "health",
        "capabilities": "capabilities",
        "hydrate": "hydrate",
        "search": "search",
        "get": "get",
        "ingest": "write",
        "ingest_governed_candidate": "ingest-governed-candidate",
        "close": "close",
        "conflicts": "conflicts",
        "phase_lock": "phase-lock",
        "verify_phase_lock": "verify-phase-lock",
    }
    for name in drop:
        cli_ops.pop(name, None)
    return {
        "package": "l9-graphite-memory",
        "package_version": version,
        "schema_version": "2.2.0",
        "contract_version": contract,
        "transports": [
            {"transport": "cli", "operations": cli_ops},
            {"transport": "mcp", "operations": {"close": "memory.close"}},
        ],
        "exit_codes": {"committed": 0, "dry_run_not_committed": 3},
    }


class Environment:
    """A fake interpreter environment on disk plus a scripted probe/CLI runner."""

    def __init__(
        self,
        root: Path,
        *,
        version: str | None = EXPECTED_VERSION,
        with_cli: bool = True,
        module_inside_prefix: bool = True,
        capabilities: dict[str, Any] | None = None,
        capabilities_rc: int = 0,
    ) -> None:
        self.root = root
        self.bin = root / "bin"
        self.bin.mkdir(parents=True, exist_ok=True)
        self.interpreter = self.bin / "python"
        self.interpreter.write_text("#!/bin/sh\n", encoding="utf-8")
        self.cli = self.bin / "l9-memory"
        if with_cli:
            self.cli.write_text("#!/bin/sh\n", encoding="utf-8")
            self.cli.chmod(0o755)
        self.version = version
        self.module = (
            str(root / "lib" / "l9_graphite_memory" / "__init__.py")
            if module_inside_prefix
            else "/somewhere/else/src/l9_graphite_memory/__init__.py"
        )
        self.capabilities = capabilities_payload() if capabilities is None else capabilities
        self.capabilities_rc = capabilities_rc
        self.calls: list[list[str]] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: str | None = None,
        input_text: str | None = None,
        timeout: float = 30.0,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del cwd, input_text, timeout, env
        args = list(argv)
        self.calls.append(args)
        if args[0] == str(self.interpreter) and args[1] == "-c":
            payload = {
                "interpreter": str(self.interpreter),
                "prefix": str(self.root),
                "version": self.version,
                "module": self.module if self.version else None,
                "error": None if self.version else "PackageNotFoundError: l9-graphite-memory",
            }
            return subprocess.CompletedProcess(args, 0, json.dumps(payload) + "\n", "")
        if args[0] == str(self.cli) and args[1:] == ["capabilities"]:
            return subprocess.CompletedProcess(
                args, self.capabilities_rc, json.dumps(self.capabilities), ""
            )
        raise AssertionError(f"unexpected invocation: {args}")


def bind(env: Environment, **kwargs: Any) -> rb.RuntimeBinding:
    return rb.resolve_runtime_binding(
        interpreter=kwargs.pop("interpreter", str(env.interpreter)),
        env=kwargs.pop("env", {}),
        runner=env.run,
        **kwargs,
    )


def test_exact_binding_reports_the_proof_shape(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _name: None)
    env = Environment(tmp_path)
    binding = bind(env)
    assert binding.ok and binding.status == rb.STATUS_EXACT
    proof = binding.as_dict()
    assert proof["binding_status"] == "exact"
    assert proof["memory_cli"] == str(env.cli)
    assert proof["memory_version"] == EXPECTED_VERSION
    assert proof["contract_version"] == CONTRACT
    assert proof["runtime_mode"] == rb.MODE_PINNED
    assert proof["path_shadow"] is None
    assert env.calls[-1] == [str(env.cli), "capabilities"]


def test_wrong_package_version_is_unbound(tmp_path: Path) -> None:
    binding = bind(Environment(tmp_path, version="2.1.0"))
    assert binding.status == rb.STATUS_UNBOUND
    assert any("does not match expected" in reason for reason in binding.reasons)


def test_missing_package_is_unbound(tmp_path: Path) -> None:
    binding = bind(Environment(tmp_path, version=None))
    assert not binding.ok
    assert any("not importable" in reason for reason in binding.reasons)


def test_missing_console_script_is_unbound(tmp_path: Path) -> None:
    binding = bind(Environment(tmp_path, with_cli=False))
    assert not binding.ok
    assert any("not installed beside" in reason for reason in binding.reasons)


def test_foreign_cli_on_path_is_reported_and_ignored(tmp_path: Path, monkeypatch) -> None:
    foreign = tmp_path / "elsewhere" / "l9-memory"
    foreign.parent.mkdir()
    foreign.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(rb.shutil, "which", lambda _name: str(foreign))
    env = Environment(tmp_path)
    binding = bind(env)
    assert binding.ok
    assert binding.path_shadow == str(foreign)
    assert binding.memory_cli == str(env.cli)
    assert any("first on PATH" in reason for reason in binding.reasons)


def test_editable_sibling_checkout_without_opt_in_is_unbound(tmp_path: Path) -> None:
    binding = bind(Environment(tmp_path, module_inside_prefix=False))
    assert not binding.ok
    assert any(rb.ENV_DEV_CHECKOUT in reason for reason in binding.reasons)


def test_development_checkout_opt_in_is_explicit_and_reported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _name: None)
    checkout = tmp_path / "l9-graphiti-memory"
    (checkout / "src" / "l9_graphite_memory").mkdir(parents=True)
    (checkout / "src" / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    env = Environment(checkout / ".venv")
    env.module = str(checkout / "src" / "l9_graphite_memory" / "__init__.py")
    binding = rb.resolve_runtime_binding(env={rb.ENV_DEV_CHECKOUT: str(checkout)}, runner=env.run)
    assert binding.ok
    assert binding.status == rb.STATUS_DEVELOPMENT
    assert binding.runtime_mode == rb.MODE_DEVELOPMENT
    assert binding.interpreter == str(checkout / ".venv" / "bin" / "python")


def test_development_checkout_serving_a_different_tree_is_unbound(tmp_path: Path) -> None:
    checkout = tmp_path / "l9-graphiti-memory"
    (checkout / "src" / "l9_graphite_memory").mkdir(parents=True)
    (checkout / "src" / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    env = Environment(checkout / ".venv", module_inside_prefix=False)
    binding = rb.resolve_runtime_binding(env={rb.ENV_DEV_CHECKOUT: str(checkout)}, runner=env.run)
    assert not binding.ok
    assert any("not the checkout" in reason for reason in binding.reasons)


def test_development_checkout_without_venv_is_unbound(tmp_path: Path) -> None:
    checkout = tmp_path / "l9-graphiti-memory"
    (checkout / "src" / "l9_graphite_memory").mkdir(parents=True)
    (checkout / "src" / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    binding = rb.resolve_runtime_binding(env={rb.ENV_DEV_CHECKOUT: str(checkout)}, runner=None)
    assert not binding.ok
    assert any(".venv/bin/python" in reason for reason in binding.reasons)


def test_pre_contract_package_is_rejected_even_at_matching_version(tmp_path: Path) -> None:
    """A 2.2.0 artifact predating ADR-082 has no `capabilities`; it must not bind."""

    binding = bind(Environment(tmp_path, capabilities_rc=2))
    assert not binding.ok
    assert any("predates the control-plane contract" in reason for reason in binding.reasons)


def test_contract_mismatch_is_unbound(tmp_path: Path) -> None:
    env = Environment(
        tmp_path, capabilities=capabilities_payload(contract="memory-control-plane/v2")
    )
    binding = bind(env)
    assert not binding.ok
    assert binding.contract_version == "memory-control-plane/v2"


def test_missing_required_operation_is_unbound(tmp_path: Path) -> None:
    binding = bind(Environment(tmp_path, capabilities=capabilities_payload(drop=("close",))))
    assert not binding.ok
    assert any("lacks required operations: close" in reason for reason in binding.reasons)


def test_cli_and_import_disagreeing_on_version_is_unbound(tmp_path: Path) -> None:
    binding = bind(Environment(tmp_path, capabilities=capabilities_payload(version="9.9.9")))
    assert not binding.ok
    assert any("do not agree" in reason for reason in binding.reasons)


def test_manifest_is_the_only_source_of_expectations(tmp_path: Path) -> None:
    manifest = rb.BindingManifest.load()
    assert manifest.distribution == "l9-graphite-memory"
    assert manifest.console_script == "l9-memory"
    assert "close" in manifest.required_cli_operations
    assert manifest.source_ref and len(manifest.source_ref) == 40


@pytest.mark.parametrize("token", ["GRAPHITI_MCP_URL", "GRAPHITI_MCP_TOKEN", "add_memory"])
def test_binding_module_has_no_provider_vocabulary(token: str) -> None:
    assert token not in Path(rb.__file__).read_text(encoding="utf-8")
