"""Runtime binding: foreign, stale, and ambiguous runtimes must not silently win."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest
from memory_boundary_fixtures import canonical_schemas

from ops.memory import runtime_binding as rb

CONTRACT = "memory-control-plane/v1"
EXPECTED_VERSION = rb.BindingManifest.load().expected_package_version
#: The audited release digest the manifest pins; the fake install carries it.
ARTIFACT_SHA256 = rb.BindingManifest.load().artifact_sha256


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
        schema_export: dict[str, Any] | None = None,
        artifact_sha256: str | None = "__manifest__",
        record_digest: str | None = None,
        editable: bool = False,
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
        self.schema_export = (
            {"schemas": canonical_schemas(), "module": self.module, "error": None, "missing": []}
            if schema_export is None
            else schema_export
        )
        # Installed-artifact provenance as PEP 610 records it (CG-P1-03).
        if artifact_sha256 == "__manifest__":
            artifact_sha256 = ARTIFACT_SHA256
        self.direct_url = (
            {
                "url": f"file:///build/l9_graphite_memory-{version}-py3-none-any.whl",
                "archive_info": {"hashes": {"sha256": artifact_sha256}},
            }
            if artifact_sha256
            else ({"url": "file:///checkout", "dir_info": {"editable": True}} if editable else None)
        )
        self.record_digest = record_digest
        self.editable = editable
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
        if args[0] == str(self.interpreter) and args[1] == "-c" and "schemas" in args[2]:
            # The contract-schema export probe (CG-P1-02).
            return subprocess.CompletedProcess(args, 0, json.dumps(self.schema_export) + "\n", "")
        if args[0] == str(self.interpreter) and args[1] == "-c":
            payload = {
                "interpreter": str(self.interpreter),
                "prefix": str(self.root),
                "version": self.version,
                "module": self.module if self.version else None,
                "error": None if self.version else "PackageNotFoundError: l9-graphite-memory",
                "direct_url": self.direct_url,
                "record_digest": self.record_digest,
                "editable": self.editable,
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
    assert proof["ok"] is True
    assert "status" not in proof
    assert proof["memory_cli"] == str(env.cli)
    assert proof["memory_version"] == EXPECTED_VERSION
    assert proof["contract_version"] == CONTRACT
    assert proof["runtime_mode"] == rb.MODE_PINNED
    assert proof["path_shadow"] is None
    assert [str(env.cli), "capabilities"] in env.calls
    # The bound release's own contracts came back with the binding.
    assert binding.contract_schemas and "CloseReceipt" in binding.contract_schemas
    assert binding.schema_digest and len(binding.schema_digest) == 64


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
    # The binding policy forbids floating refs: source.ref is either the full
    # commit SHA or the vX.Y.Z release tag, and a tag is only a name — the
    # commit it must resolve to is pinned beside it as release_evidence.memory_sha
    # (the cross-repo proof peels the tag and refuses any other commit).
    assert manifest.source_ref
    sha_re = re.compile(r"^[0-9a-f]{40}$")
    tag_re = re.compile(r"^v\d+\.\d+\.\d+$")
    ref = manifest.source_ref
    assert sha_re.match(ref) or tag_re.match(ref), ref
    raw = json.loads(Path(manifest.path).read_text(encoding="utf-8"))
    memory_sha = str(raw["release_evidence"]["memory_sha"])
    assert sha_re.match(memory_sha), memory_sha
    if sha_re.match(manifest.source_ref):
        assert manifest.source_ref == memory_sha


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


# ---------------------------------------------------------------------------
# CG-P1-03: STATUS_EXACT must mean the exact artifact
#
# Version + contract + "module under the interpreter prefix" are satisfied
# identically by every build of a version. A status named EXACT reachable from
# those alone says nothing about which build is installed, which is the whole
# question a pinned release binding exists to answer.
# ---------------------------------------------------------------------------


def test_1_the_expected_artifact_is_exact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    binding = bind(Environment(tmp_path))
    assert binding.status == rb.STATUS_EXACT
    assert binding.is_exact is True
    assert binding.artifact_provenance == rb.PROVENANCE_ARTIFACT_DIGEST
    assert binding.installed_artifact_digest == ARTIFACT_SHA256


def test_2_same_version_different_artifact_is_not_exact(tmp_path: Path, monkeypatch) -> None:
    """The case the old check could not see: the pinned version, a foreign build."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    binding = bind(Environment(tmp_path, artifact_sha256="b" * 64))
    assert binding.status == rb.STATUS_UNBOUND
    assert binding.is_exact is False
    assert any("same version, different build" in r for r in binding.reasons)


def test_3_unproven_artifact_is_compatible_not_exact(tmp_path: Path, monkeypatch) -> None:
    """Only version and contract provable -> the weaker status, by name."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    binding = bind(Environment(tmp_path, artifact_sha256=None))
    assert binding.status == rb.STATUS_COMPATIBLE
    assert binding.is_exact is False
    assert binding.ok is True  # usable, but never called exact
    assert binding.artifact_provenance == rb.PROVENANCE_UNPROVEN
    assert any("cannot be verified in place" in r for r in binding.reasons)


def test_3b_an_unhashed_install_names_the_record_digest_to_pin(tmp_path: Path, monkeypatch) -> None:
    """uv installing a local wheel records no PEP 610 archive hash, so the
    reason has to say what *can* be pinned instead of what is missing."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    manifest = tmp_path / "binding.json"
    _manifest_with(manifest, installed_record_digest=None)
    env = Environment(tmp_path / "env", artifact_sha256=None, record_digest="e" * 64)
    binding = bind(env, manifest_path=manifest)
    assert binding.status == rb.STATUS_COMPATIBLE
    assert binding.installed_artifact_digest == "e" * 64
    assert any("installed_record_digest" in r and "e" * 64 in r for r in binding.reasons)


def test_3c_the_record_digest_mechanism_works_when_a_digest_is_pinned(
    tmp_path: Path, monkeypatch
) -> None:
    """The fallback proof is real where a stable digest exists: a match binds
    exactly, a mismatch is contradiction rather than a compatible build."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    manifest = tmp_path / "binding.json"
    _manifest_with(manifest, installed_record_digest="c" * 64)
    match = Environment(tmp_path / "a", artifact_sha256=None, record_digest="c" * 64)
    assert bind(match, manifest_path=manifest).status == rb.STATUS_EXACT
    other = Environment(tmp_path / "b", artifact_sha256=None, record_digest="e" * 64)
    refused = bind(other, manifest_path=manifest)
    assert refused.status == rb.STATUS_UNBOUND
    assert any("same version, different build" in r for r in refused.reasons)


def test_3d_the_real_manifest_pins_no_record_digest(tmp_path: Path) -> None:
    """Deliberate, and evidence-backed: three memory-cross-repo runs installed
    the byte-identical wheel and produced three different installed-RECORD
    digests, so the RECORD is not a deterministic function of the wheel here.
    Pinning one would make the binding flap on an unchanged release."""
    manifest = rb.BindingManifest.load()
    assert manifest.artifact_sha256, "the audited wheel digest is still recorded"
    assert manifest.installed_record_digest is None


def test_4_wrong_version_is_still_rejected(tmp_path: Path) -> None:
    binding = bind(Environment(tmp_path, version="2.2.0"))
    assert binding.status == rb.STATUS_UNBOUND


def test_5_wrong_contract_version_is_still_rejected(tmp_path: Path) -> None:
    env = Environment(tmp_path, capabilities=capabilities_payload(contract="memory/v2"))
    binding = bind(env)
    assert binding.status == rb.STATUS_UNBOUND
    assert any("contract" in r for r in binding.reasons)


def test_6_editable_install_is_never_production_exact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    binding = bind(Environment(tmp_path, artifact_sha256=None, editable=True))
    assert binding.status == rb.STATUS_COMPATIBLE
    assert binding.is_exact is False
    assert any("editable install" in r for r in binding.reasons)


def test_7_development_checkout_keeps_its_own_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    checkout = tmp_path / "l9-graphiti-memory"
    (checkout / "src" / "l9_graphite_memory").mkdir(parents=True)
    (checkout / "src" / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    env = Environment(checkout / ".venv", artifact_sha256=None)
    env.module = str(checkout / "src" / "l9_graphite_memory" / "__init__.py")
    binding = rb.resolve_runtime_binding(env={rb.ENV_DEV_CHECKOUT: str(checkout)}, runner=env.run)
    assert binding.status == rb.STATUS_DEVELOPMENT
    assert binding.is_exact is False


def test_8_foreign_install_of_the_same_version_is_refused(tmp_path: Path, monkeypatch) -> None:
    """A wheel someone else built from the same tag: right version, right
    contract, right layout, different bytes."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    foreign = Environment(tmp_path, artifact_sha256="f" * 64)
    assert bind(foreign).status == rb.STATUS_UNBOUND
    assert bind(foreign).installed_artifact_digest == "f" * 64


def test_9_record_digest_proves_the_artifact_when_pinned(tmp_path: Path, monkeypatch) -> None:
    """Where an install left no archive hash, the installed RECORD digest is
    the fallback proof — and it is a pin, not a self-report."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    manifest = tmp_path / "binding.json"
    _manifest_with(manifest, installed_record_digest="c" * 64)
    env = Environment(tmp_path / "env", artifact_sha256=None, record_digest="c" * 64)
    binding = bind(env, manifest_path=manifest)
    assert binding.status == rb.STATUS_EXACT
    assert binding.artifact_provenance == rb.PROVENANCE_RECORD_DIGEST

    other = Environment(tmp_path / "env2", artifact_sha256=None, record_digest="d" * 64)
    assert bind(other, manifest_path=manifest).status == rb.STATUS_UNBOUND


def test_10_tampered_provenance_is_refused(tmp_path: Path, monkeypatch) -> None:
    """A marker claiming the audited digest while the install is something
    else is a contradiction, not weak evidence."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    manifest = tmp_path / "binding.json"
    _manifest_with(manifest, artifact_sha256="a" * 64)
    binding = bind(Environment(tmp_path / "env", artifact_sha256="0" * 64), manifest_path=manifest)
    assert binding.status == rb.STATUS_UNBOUND
    assert any("is not the audited release" in r for r in binding.reasons)


def test_11_required_exactness_refuses_a_compatible_build(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    env = Environment(tmp_path, artifact_sha256=None)
    assert bind(env).status == rb.STATUS_COMPATIBLE
    strict = rb.resolve_runtime_binding(
        interpreter=str(env.interpreter), env={rb.ENV_REQUIRE_EXACT: "1"}, runner=env.run
    )
    assert strict.status == rb.STATUS_UNBOUND
    assert any(rb.ENV_REQUIRE_EXACT in r for r in strict.reasons)


def test_12_a_manifest_without_a_digest_cannot_yield_exact(tmp_path: Path, monkeypatch) -> None:
    """The honest failure mode: nothing pinned means nothing proved, and the
    status says so rather than borrowing the name."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    manifest = tmp_path / "binding.json"
    _manifest_with(manifest, artifact_sha256=None, installed_record_digest=None)
    binding = bind(Environment(tmp_path / "env"), manifest_path=manifest)
    assert binding.status == rb.STATUS_COMPATIBLE
    assert any("records no artifact digest" in r for r in binding.reasons)


def test_13_the_proof_shape_carries_the_artifact_evidence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    proof = bind(Environment(tmp_path)).as_dict()
    assert proof["binding_status"] == "exact"
    assert proof["ok"] is True
    assert proof["artifact_provenance"] == rb.PROVENANCE_ARTIFACT_DIGEST
    assert proof["installed_artifact_digest"] == ARTIFACT_SHA256
    assert proof["expected_artifact_digest"] == ARTIFACT_SHA256


def _manifest_with(path: Path, **evidence: Any) -> None:
    """A copy of the real manifest with the release evidence overridden."""
    raw = json.loads(rb.DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    raw["release_evidence"] = {**(raw.get("release_evidence") or {}), **evidence}
    path.write_text(json.dumps(raw), encoding="utf-8")


# ---------------------------------------------------------------------------
# The schema-export probe, executed for real (CG-P1-02 follow-up)
#
# The first CI run of the required proof reported "bound release exports no
# schema for" seven of eleven models: `l9_graphite_memory.contracts` is a
# *package* whose __init__ re-exports only some of them, and the probe looked
# nowhere else. No unit test covered the probe body, so nothing caught it.
# These run the actual probe source in a real interpreter against a package
# shaped the way the release's is.
# ---------------------------------------------------------------------------


def _run_probe(root: Path, names: Sequence[str], modules: Sequence[str] = ()) -> dict[str, Any]:
    import os

    env = {**os.environ, "PYTHONPATH": str(root)}
    result = subprocess.run(
        # -S keeps the target interpreter's site-packages (now the published
        # wheel) from leaking into a synthetic-tree probe.
        [sys.executable, "-S", "-c", rb._SCHEMA_PROBE, ",".join(names), ",".join(modules)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_probe_finds_models_that_the_package_init_does_not_reexport(tmp_path: Path) -> None:
    """The exact shape that failed in CI: four models re-exported, the rest
    reachable only through a submodule."""
    root = tmp_path / "site"
    exported = ["SearchReceipt", "WriteReceipt"]
    submodule_only = ["HealthReceipt", "CapabilitiesReceipt", "ConflictsReceipt"]
    pkg = root / "l9_graphite_memory" / "contracts"
    pkg.mkdir(parents=True)
    (root / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    model = (
        "class {name}:\n"
        "    @staticmethod\n"
        "    def model_json_schema():\n"
        "        return {{'title': '{name}', 'type': 'object'}}\n"
    )
    (pkg / "receipts.py").write_text(
        "".join(model.format(name=n) for n in submodule_only), encoding="utf-8"
    )
    (pkg / "__init__.py").write_text(
        "".join(model.format(name=n) for n in exported), encoding="utf-8"
    )

    payload = _run_probe(root, exported + submodule_only)
    assert payload["error"] is None
    assert payload["missing"] == []
    assert sorted(payload["schemas"]) == sorted(exported + submodule_only)


def test_probe_reports_a_model_the_release_really_lacks(tmp_path: Path) -> None:
    root = tmp_path / "site"
    pkg = root / "l9_graphite_memory" / "contracts"
    pkg.mkdir(parents=True)
    (root / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text(
        "class SearchReceipt:\n"
        "    @staticmethod\n"
        "    def model_json_schema():\n"
        "        return {'title': 'SearchReceipt'}\n",
        encoding="utf-8",
    )
    payload = _run_probe(root, ["SearchReceipt", "NoSuchReceipt"])
    assert list(payload["schemas"]) == ["SearchReceipt"]
    assert payload["missing"] == ["NoSuchReceipt"]


def test_probe_reports_an_absent_contracts_package(tmp_path: Path) -> None:
    payload = _run_probe(tmp_path / "empty", ["CloseReceipt"])
    assert payload["schemas"] == {}
    assert payload["error"] and "ModuleNotFoundError" in payload["error"]


def test_probe_reports_every_model_the_release_exports(tmp_path: Path) -> None:
    """A name Cursor guessed wrong must be diagnosable, not mute: the probe
    lists what the package actually exports alongside what it could not find."""
    root = tmp_path / "site"
    pkg = root / "l9_graphite_memory" / "contracts"
    pkg.mkdir(parents=True)
    (root / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text(
        "class MemoryHealth:\n"
        "    @staticmethod\n"
        "    def model_json_schema():\n"
        "        return {'title': 'MemoryHealth'}\n",
        encoding="utf-8",
    )
    payload = _run_probe(root, ["HealthReceipt"])
    assert payload["missing"] == ["HealthReceipt"]
    assert "MemoryHealth" in payload["available"]


def test_binding_reasons_name_what_the_release_exports(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    export = {
        "schemas": {"CloseReceipt": {"type": "object"}},
        "module": "contracts/__init__.py",
        "error": None,
        "missing": ["HealthReceipt"],
        "available": ["CloseReceipt", "MemoryHealth"],
    }
    binding = bind(Environment(tmp_path, schema_export=export))
    reason = next(r for r in binding.reasons if "exports no schema for" in r)
    assert "HealthReceipt" in reason and "MemoryHealth" in reason


def test_probe_resolves_a_model_under_the_release_s_own_name(tmp_path: Path) -> None:
    """The release calls it HealthReport; Cursor's view is HealthReceipt. The
    alias is declared in the binding manifest and the schema comes back keyed
    by the name Cursor validates under."""
    root = tmp_path / "site"
    pkg = root / "l9_graphite_memory" / "contracts"
    pkg.mkdir(parents=True)
    (root / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text(
        "class HealthReport:\n"
        "    @staticmethod\n"
        "    def model_json_schema():\n"
        "        return {'title': 'HealthReport'}\n",
        encoding="utf-8",
    )
    payload = _run_probe(root, ["HealthReceipt=HealthReport"])
    assert payload["missing"] == []
    assert payload["schemas"]["HealthReceipt"]["title"] == "HealthReport"


def test_manifest_declares_the_aliases_the_release_actually_uses() -> None:
    aliases = rb.BindingManifest.load().contract_model_aliases
    assert aliases["HealthReceipt"] == ("HealthReport",)
    assert aliases["HydrationReceipt"] == ("HydrationResult",)
    assert aliases["CapabilitiesReceipt"] == ("ControlPlaneCapabilities",)
    assert "_note" not in aliases


# ---------------------------------------------------------------------------
# The bound release's real contract surface (verified at ref 7691c076)
#
# Every name below was read from the merged source, then proved end to end:
# the probe resolves 11 of 11 against the installed 2.3.0 wheel. They are
# pinned here so a future edit cannot quietly drop one back to a guess.
# ---------------------------------------------------------------------------

RELEASE_MODEL_NAMES = {
    "CapabilitiesReceipt": "ControlPlaneCapabilities",
    "HealthReceipt": "HealthReport",
    "ResolveReceipt": "GroupResolution",
    "HydrationReceipt": "HydrationResult",
    "CandidateReceipt": "MemoryCandidateIngestionResult",
    "ConflictsReceipt": "ConflictReport",
    "PhaseLockVerificationReceipt": "PhaseLockVerification",
}


def test_every_requested_model_resolves_by_its_own_name_or_a_declared_alias() -> None:
    """No model Cursor requests may be left to a guess: it either matches the
    release's own name or carries a declared, verified alias."""
    manifest = rb.BindingManifest.load()
    aliases = manifest.contract_model_aliases
    same_name = {"SearchReceipt", "WriteReceipt", "CloseReceipt", "PhaseLockReceipt"}
    for name in rb.CANONICAL_RECEIPT_MODELS:
        if name in same_name:
            assert name not in aliases, f"{name} matches the release; it needs no alias"
        else:
            assert aliases.get(name) == (RELEASE_MODEL_NAMES[name],), (
                f"{name} is not exported by the release under that name; it must alias "
                f"{RELEASE_MODEL_NAMES[name]}"
            )


def test_the_probe_searches_group_resolver_as_well_as_contracts() -> None:
    """GroupResolution (Cursor's ResolveReceipt) is a BaseModel in
    group_resolver.py and is NOT re-exported from the contracts package, so
    walking contracts alone silently loses it."""
    modules = rb.BindingManifest.load().contract_model_modules
    assert "l9_graphite_memory.contracts" in modules
    assert "l9_graphite_memory.group_resolver" in modules


def test_the_binding_names_the_release_tag_and_the_commit_it_resolves_to() -> None:
    """RU-P1-01: the binding names the live release tag and the commit it peels to.

    source.ref carries the TAG NAME and release_evidence.memory_sha the commit
    it peels to. A moved tag fails the proof instead of silently rebinding.
    Live target is v2.3.1 (first PyPI upload). v2.3.0 stays immutable.
    """
    manifest = rb.BindingManifest.load()
    raw = json.loads(rb.DEFAULT_MANIFEST_PATH.read_text(encoding="utf-8"))
    evidence = raw["release_evidence"]
    assert raw["source"]["ref"] == "v2.3.1"
    assert evidence["memory_tag"] == "v2.3.1"
    assert evidence["memory_tag_object_sha"] == "f65ff2bb1c8cb43a55b78732c4ab74f711ee8c2f"
    assert manifest.memory_sha == "84eedcdfab83020776eab290599751b3b6af8dbf"
    assert manifest.artifact_sha256 == (
        "b3b045e482fd157a0242d5ad861a3609057c6d66dd2095673f55f1efe888ff89"
    )


def test_a_tag_ref_is_re_resolved_on_the_remote_every_proof() -> None:
    """A tag is a movable name, so recording it proves nothing on its own.

    The proof workflow must peel it on the memory remote and refuse any commit
    other than release_evidence.memory_sha, and must refuse a ref that is
    neither a full SHA nor a vX.Y.Z tag — a floating ref (a branch) would make
    the binding mean something different on every run.
    """
    workflow = (
        rb.DEFAULT_MANIFEST_PATH.parent.parent.parent
        / ".github"
        / "workflows"
        / "memory-cross-repo.yml"
    ).read_text(encoding="utf-8")
    assert "print(f\"memory_sha={ev['memory_sha']}\")" in workflow
    assert "floating refs are forbidden" in workflow
    assert "refs/tags/${MEMORY_REF}^{}" in workflow
    assert "does not exist on" in workflow
    assert 'if [ "${resolved}" != "${MEMORY_SHA}" ]' in workflow


def test_probe_resolves_an_alias_from_a_second_declared_module(tmp_path: Path) -> None:
    """The GroupResolution shape, exercised for real: the model lives outside
    the contracts package and is reachable only because the manifest names its
    module."""
    root = tmp_path / "site"
    pkg = root / "l9_graphite_memory" / "contracts"
    pkg.mkdir(parents=True)
    (root / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (root / "l9_graphite_memory" / "group_resolver.py").write_text(
        "class GroupResolution:\n"
        "    @staticmethod\n"
        "    def model_json_schema():\n"
        "        return {'title': 'GroupResolution'}\n",
        encoding="utf-8",
    )
    contracts_only = _run_probe(root, ["ResolveReceipt=GroupResolution"])
    assert contracts_only["missing"] == ["ResolveReceipt"]
    both = _run_probe(
        root,
        ["ResolveReceipt=GroupResolution"],
        modules=["l9_graphite_memory.contracts", "l9_graphite_memory.group_resolver"],
    )
    assert both["missing"] == []
    assert both["schemas"]["ResolveReceipt"]["title"] == "GroupResolution"


def test_a_manifest_module_the_release_lacks_is_reported_even_when_nothing_is_missing(
    tmp_path: Path,
) -> None:
    """Completeness elsewhere must not hide manifest drift.

    A binding that names a module the bound release does not have is drifted
    from the release, whether or not the remaining modules happen to supply
    every canonical model. Swallowing that is CG-P1-02's own shape — declared
    but not enforced — so the probe reports the unimportable module separately
    from `missing`.
    """
    root = tmp_path / "site"
    pkg = root / "l9_graphite_memory" / "contracts"
    pkg.mkdir(parents=True)
    (root / "l9_graphite_memory" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text(
        "class SearchReceipt:\n"
        "    @staticmethod\n"
        "    def model_json_schema():\n"
        "        return {'title': 'SearchReceipt'}\n",
        encoding="utf-8",
    )
    payload = _run_probe(
        root,
        ["SearchReceipt"],
        modules=["l9_graphite_memory.contracts", "l9_graphite_memory.no_such_module"],
    )
    assert payload["missing"] == []
    assert list(payload["schemas"]) == ["SearchReceipt"]
    assert any("no_such_module" in item for item in payload["unimportable"])


def test_binding_reasons_name_a_manifest_module_the_release_lacks(
    tmp_path: Path, monkeypatch
) -> None:
    """And the verdict carries it, so a drifted manifest is visible in the
    binding rather than only in the probe payload."""
    monkeypatch.setattr(rb.shutil, "which", lambda _n: None)
    export = {
        "schemas": {"CloseReceipt": {"type": "object"}},
        "module": "contracts/__init__.py",
        "error": None,
        "missing": [],
        "available": ["CloseReceipt"],
        "unimportable": ["l9_graphite_memory.gone: ModuleNotFoundError: no module"],
    }
    binding = bind(Environment(tmp_path, schema_export=export))
    reason = next(r for r in binding.reasons if "does not have" in r)
    assert "l9_graphite_memory.gone" in reason
