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
        module: str | None = None,
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
        self.module = module or (
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


# ---------------------------------------------------------------------------
# CG-P2-01: runtime containment is a filesystem relation, not a string prefix
#
# `str(module).startswith(str(prefix))` answers yes for /opt/memory-evil under
# /opt/memory — a different environment whose name merely shares a prefix, its
# package admitted as the bound one. Containment is decided on resolved paths.
# ---------------------------------------------------------------------------


def test_sibling_prefix_is_not_containment() -> None:
    """The canonical case. `/opt/memory-evil` is not inside `/opt/memory`."""
    assert rb._path_contains("/opt/memory", "/opt/memory/lib/l9_graphite_memory/__init__.py")
    assert not rb._path_contains(
        "/opt/memory", "/opt/memory-evil/lib/l9_graphite_memory/__init__.py"
    )
    # The bare sibling directory itself, and the prefix as its own child.
    assert not rb._path_contains("/opt/memory", "/opt/memory-evil")
    assert not rb._path_contains("/opt/memory", "/opt/memory")


def test_sibling_prefix_is_refused_by_the_binding(tmp_path: Path, monkeypatch) -> None:
    """End to end: a same-version package served from the evil twin is unbound."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    good = tmp_path / "memory"
    evil = tmp_path / "memory-evil"
    (evil / "lib" / "l9_graphite_memory").mkdir(parents=True)
    (evil / "lib" / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    env = Environment(good, module=str(evil / "lib" / "l9_graphite_memory" / "__init__.py"))
    binding = bind(env)
    assert binding.status == rb.STATUS_UNBOUND
    assert any("served from outside the interpreter environment" in r for r in binding.reasons)


def test_relative_components_do_not_escape(tmp_path: Path) -> None:
    prefix = tmp_path / "env"
    (prefix / "lib").mkdir(parents=True)
    (tmp_path / "other").mkdir()
    escaped = str(prefix / "lib" / ".." / ".." / "other" / "pkg.py")
    assert not rb._path_contains(str(prefix), escaped)
    assert rb._path_contains(str(prefix), str(prefix / "lib" / ".." / "lib" / "pkg.py"))


def test_symlinked_package_path_compares_by_real_location(tmp_path: Path) -> None:
    """A site-packages entry symlinked out of the environment is not contained."""
    prefix = tmp_path / "env"
    site = prefix / "lib" / "site-packages"
    site.mkdir(parents=True)
    outside = tmp_path / "checkout" / "l9_graphite_memory"
    outside.mkdir(parents=True)
    (outside / "__init__.py").write_text("", encoding="utf-8")
    link = site / "l9_graphite_memory"
    link.symlink_to(outside, target_is_directory=True)
    # Lexically inside the prefix; really a checkout the environment does not own.
    assert str(link / "__init__.py").startswith(str(prefix))
    assert not rb._path_contains(str(prefix), str(link / "__init__.py"))


def test_symlinked_interpreter_prefix_is_still_containment(tmp_path: Path) -> None:
    """The inverse: a symlinked *prefix* must not turn a real child into a foreigner."""
    real = tmp_path / "real-env"
    (real / "lib" / "l9_graphite_memory").mkdir(parents=True)
    module = real / "lib" / "l9_graphite_memory" / "__init__.py"
    module.write_text("", encoding="utf-8")
    alias = tmp_path / "aliased-env"
    alias.symlink_to(real, target_is_directory=True)
    assert not str(module).startswith(str(alias))  # a string test would reject it
    assert rb._path_contains(str(alias), str(module))


def test_pth_injected_path_outside_the_prefix_is_refused(tmp_path: Path, monkeypatch) -> None:
    """A .pth entry makes an arbitrary directory importable; it is not the environment."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    injected = tmp_path / "injected" / "l9_graphite_memory" / "__init__.py"
    injected.parent.mkdir(parents=True)
    injected.write_text("", encoding="utf-8")
    binding = bind(Environment(tmp_path / "env", module=str(injected)))
    assert binding.status == rb.STATUS_UNBOUND
    assert binding.module_path == str(injected)


def test_editable_install_needs_the_development_opt_in(tmp_path: Path, monkeypatch) -> None:
    """Unchanged behaviour, asserted against the new containment test."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    binding = bind(Environment(tmp_path, module_inside_prefix=False))
    assert binding.status == rb.STATUS_UNBOUND
    assert binding.runtime_mode == rb.MODE_PINNED
    assert any(rb.ENV_DEV_CHECKOUT in r for r in binding.reasons)


def test_empty_or_unresolvable_operands_are_not_containment() -> None:
    """Ambiguity fails closed — an empty prefix must never match everything."""
    assert not rb._path_contains("", "/opt/memory/pkg.py")
    assert not rb._path_contains(None, "/opt/memory/pkg.py")
    assert not rb._path_contains("/opt/memory", "")
    assert not rb._path_contains("/opt/memory", None)


def test_case_sensitivity_follows_the_platform(tmp_path: Path) -> None:
    """Documented, not assumed: containment is decided by the filesystem's own
    comparison after resolution, so a case variant matches only where the
    platform itself treats the two paths as the same file."""
    prefix = tmp_path / "Env"
    (prefix / "lib").mkdir(parents=True)
    module = prefix / "lib" / "pkg.py"
    module.write_text("", encoding="utf-8")
    assert rb._path_contains(str(prefix), str(module))
    variant = str(prefix).replace("Env", "ENV") + "/lib/pkg.py"
    expected = Path(variant).resolve().is_relative_to(Path(str(prefix)).resolve())
    assert rb._path_contains(str(prefix), variant) is expected
