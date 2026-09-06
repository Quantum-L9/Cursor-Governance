"""Prove which exact memory package and CLI Cursor will run (INV-11).

Responsibilities, and nothing else:

- find the installed ``l9-graphite-memory`` distribution in one interpreter
- read its version and the location it is served from
- resolve the ``l9-memory`` console script belonging to that same environment
- refuse ambiguous or foreign resolution (PATH-first CLI, editable sibling
  checkout, wrong version, wrong contract)
- report interpreter, executable, version, contract, and binding status

It never resolves Graphiti, never searches sibling repositories, and treats
a development checkout as an explicit opt-in that is *reported* as
``runtime_mode = development_checkout`` rather than silently winning.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ops.memory.receipts import CapabilitiesReceipt, InvalidReceiptError

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = _REPO_ROOT / "ops" / "config" / "memory-binding.json"

ENV_DEV_CHECKOUT = "L9_MEMORY_DEV_CHECKOUT"
ENV_INTERPRETER = "L9_MEMORY_INTERPRETER"

MODE_PINNED = "pinned_environment"
MODE_DEVELOPMENT = "development_checkout"

STATUS_EXACT = "exact"
#: Version and contract agree with the manifest, but the *artifact* was not
#: proved (audit CG-P1-03). Two different builds of one version satisfy
#: version + contract + containment identically, so a status named EXACT must
#: not be reachable from those alone. This is the weaker, honest verdict.
STATUS_COMPATIBLE = "compatible"
STATUS_DEVELOPMENT = "development_checkout"
STATUS_UNBOUND = "unbound"

#: Turns STATUS_COMPATIBLE from "usable, and reported as unproved" into
#: "refused". Set by the cross-repo proof and by production callers that
#: require the audited artifact rather than a compatible build.
ENV_REQUIRE_EXACT = "L9_MEMORY_REQUIRE_EXACT_ARTIFACT"

PROVENANCE_ARTIFACT_DIGEST = "artifact_sha256"
PROVENANCE_RECORD_DIGEST = "installed_record_digest"
PROVENANCE_UNPROVEN = "unproven"

Runner = Callable[..., "subprocess.CompletedProcess[str]"]

# Runs inside the *target* interpreter: it must not assume this repository's
# environment, only the standard library.
_PROBE = r"""
import hashlib, json, sys
dist, pkg = sys.argv[1], sys.argv[2]
out = {"interpreter": sys.executable, "prefix": sys.prefix, "version": None, "module": None}
out["error"] = None
out["direct_url"] = None
out["record_digest"] = None
out["editable"] = None
try:
    from importlib.metadata import version
    out["version"] = version(dist)
except Exception as exc:
    out["error"] = f"{type(exc).__name__}: {exc}"
try:
    import importlib
    module = importlib.import_module(pkg)
    out["module"] = getattr(module, "__file__", None)
except Exception as exc:
    out["error"] = out["error"] or f"{type(exc).__name__}: {exc}"
try:
    # Installed-artifact provenance. direct_url.json is PEP 610: pip and uv
    # record the archive a wheel was installed from, with its hash when the
    # install named one. RECORD lists every installed file with its own
    # sha256, so a digest over it distinguishes two builds of one version.
    from importlib.metadata import distribution
    installed = distribution(dist)
    try:
        raw_direct = installed.read_text("direct_url.json")
    except Exception:
        raw_direct = None
    if raw_direct:
        out["direct_url"] = json.loads(raw_direct)
        info = out["direct_url"].get("dir_info") or {}
        out["editable"] = bool(info.get("editable"))
    record = installed.read_text("RECORD") or ""
    rows = []
    for line in record.splitlines():
        parts = line.rsplit(",", 2)
        if len(parts) != 3 or parts[0].endswith("/RECORD") or not parts[1]:
            continue
        rows.append(parts[0].replace("\\", "/") + "," + parts[1] + "," + parts[2])
    if rows:
        joined = "\n".join(sorted(rows)).encode("utf-8")
        out["record_digest"] = hashlib.sha256(joined).hexdigest()
except Exception as exc:
    out["error"] = out["error"] or f"{type(exc).__name__}: {exc}"
print(json.dumps(out))
"""

#: Receipt models Cursor accepts as authoritative. The canonical schema for
#: each is exported from the *bound* release (CG-P1-02), never restated here.
CANONICAL_RECEIPT_MODELS: tuple[str, ...] = (
    "CapabilitiesReceipt",
    "HealthReceipt",
    "ResolveReceipt",
    "HydrationReceipt",
    "SearchReceipt",
    "WriteReceipt",
    "CandidateReceipt",
    "CloseReceipt",
    "ConflictsReceipt",
    "PhaseLockReceipt",
    "PhaseLockVerificationReceipt",
)

# Also runs inside the *target* interpreter. It exports the pinned release's
# own pydantic models as JSON Schema so Cursor validates against the contract
# the bound package actually ships, across the interpreter boundary that makes
# an in-process import impossible in pinned mode.
_SCHEMA_PROBE = r"""
import json, sys
names = [n for n in sys.argv[1].split(",") if n]
out = {"schemas": {}, "module": None, "error": None, "missing": []}
try:
    import importlib
    contracts = importlib.import_module("l9_graphite_memory.contracts")
    out["module"] = getattr(contracts, "__file__", None)
    for name in names:
        model = getattr(contracts, name, None)
        exporter = getattr(model, "model_json_schema", None) if model is not None else None
        if exporter is None:
            out["missing"].append(name)
            continue
        try:
            out["schemas"][name] = exporter()
        except Exception as exc:
            out["missing"].append(name)
            out["error"] = out["error"] or f"{name}: {type(exc).__name__}: {exc}"
except Exception as exc:
    out["error"] = f"{type(exc).__name__}: {exc}"
print(json.dumps(out))
"""


def default_runner(
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    input_text: str | None = None,
    timeout: float = 30.0,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - argv list, never a shell string
        list(argv),
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        env=dict(env) if env is not None else None,
    )


def _path_contains(prefix: str | None, candidate: str | None) -> bool:
    """True when ``candidate`` is a path *inside* the directory ``prefix``.

    Filesystem containment, never a string prefix (CG-P2-01). ``startswith``
    answers yes for ``/opt/memory-evil`` under ``/opt/memory``: a sibling
    directory whose name merely begins with the environment's, which is a
    foreign package accepted as the bound one. Both sides are resolved first
    so a symlinked interpreter prefix, a symlinked package directory, and
    ``..`` components all compare by their real location.

    Ambiguity is not containment: an unresolvable path returns ``False``.
    """

    if not prefix or not candidate:
        return False
    try:
        resolved_prefix = Path(prefix).resolve()
        resolved_candidate = Path(candidate).resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    if resolved_candidate == resolved_prefix:
        return False
    return resolved_candidate.is_relative_to(resolved_prefix)


@dataclass(frozen=True)
class BindingManifest:
    distribution: str
    import_package: str
    console_script: str
    expected_package_version: str
    expected_contract_version: str
    required_cli_operations: tuple[str, ...]
    source_ref: str | None
    path: str
    #: Immutable release identity (audit CG-P1-03). ``artifact_sha256`` is the
    #: wheel digest recorded when the release was built and audited;
    #: ``installed_record_digest`` is the digest of that wheel's installed
    #: RECORD, which is verifiable where the install left no direct-URL hash.
    #: Either one proves the artifact; neither being present means exactness
    #: cannot be claimed, only compatibility.
    artifact_sha256: str | None = None
    installed_record_digest: str | None = None
    release_tag: str | None = None
    memory_sha: str | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> BindingManifest:
        manifest_path = Path(path or DEFAULT_MANIFEST_PATH)
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = raw.get("source") or {}
        evidence = raw.get("release_evidence") or {}
        return cls(
            distribution=str(raw["distribution"]),
            import_package=str(raw["import_package"]),
            console_script=str(raw["console_script"]),
            expected_package_version=str(raw["expected_package_version"]),
            expected_contract_version=str(raw["expected_contract_version"]),
            required_cli_operations=tuple(str(item) for item in raw["required_cli_operations"]),
            source_ref=str(source["ref"]) if source.get("ref") else None,
            path=str(manifest_path),
            artifact_sha256=_optional_text(evidence.get("artifact_sha256")),
            installed_record_digest=_optional_text(evidence.get("installed_record_digest")),
            release_tag=_optional_text(evidence.get("release_tag")),
            memory_sha=_optional_text(evidence.get("memory_sha")),
        )


@dataclass(frozen=True)
class RuntimeBinding:
    status: str
    runtime_mode: str
    memory_package: str
    expected_version: str
    expected_contract_version: str
    manifest_path: str
    interpreter: str | None = None
    memory_cli: str | None = None
    memory_version: str | None = None
    contract_version: str | None = None
    module_path: str | None = None
    path_shadow: str | None = None
    capabilities: CapabilitiesReceipt | None = field(default=None, repr=False)
    reasons: tuple[str, ...] = ()
    #: Canonical receipt schemas exported from the bound release (CG-P1-02).
    #: ``None`` means the export did not run or the package ships no contracts
    #: module: the client then has nothing canonical to validate against, and
    #: fails closed where exact validation is required. Schema export never
    #: changes the binding status — an exact runtime that cannot export its
    #: contracts is still exactly bound, just unvalidatable.
    contract_schemas: dict[str, Any] | None = field(default=None, repr=False)
    schema_digest: str | None = None
    schema_source: str | None = None
    #: How the installed artifact was proved, and what it was proved to be
    #: (audit CG-P1-03). ``PROVENANCE_UNPROVEN`` accompanies STATUS_COMPATIBLE.
    artifact_provenance: str = PROVENANCE_UNPROVEN
    installed_artifact_digest: str | None = None
    expected_artifact_digest: str | None = None
    release_tag: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in {STATUS_EXACT, STATUS_COMPATIBLE, STATUS_DEVELOPMENT}

    @property
    def is_exact(self) -> bool:
        """The bound runtime is the audited release artifact, proved.

        Never inferred from version, contract, or path containment: a status
        named EXACT must mean the artifact, or it means nothing.
        """

        return self.status == STATUS_EXACT

    def as_dict(self) -> dict[str, Any]:
        """Bootstrap-diagnostic shape from plan §7. No secrets, no content."""

        return {
            "memory_package": self.memory_package,
            "memory_version": self.memory_version,
            "expected_version": self.expected_version,
            "contract_version": self.contract_version,
            "expected_contract_version": self.expected_contract_version,
            "interpreter": self.interpreter,
            "memory_cli": self.memory_cli,
            "module_path": self.module_path,
            "runtime_mode": self.runtime_mode,
            "binding_status": self.status,
            "artifact_provenance": self.artifact_provenance,
            "installed_artifact_digest": self.installed_artifact_digest,
            "expected_artifact_digest": self.expected_artifact_digest,
            "release_tag": self.release_tag,
            "path_shadow": self.path_shadow,
            "reasons": list(self.reasons),
            "manifest": self.manifest_path,
        }


def _unbound(
    manifest: BindingManifest,
    *,
    mode: str,
    reasons: Sequence[str],
    interpreter: str | None = None,
    memory_cli: str | None = None,
    memory_version: str | None = None,
    module_path: str | None = None,
    path_shadow: str | None = None,
    contract_version: str | None = None,
    artifact_provenance: str = PROVENANCE_UNPROVEN,
    installed_artifact_digest: str | None = None,
) -> RuntimeBinding:
    return RuntimeBinding(
        status=STATUS_UNBOUND,
        artifact_provenance=artifact_provenance,
        installed_artifact_digest=installed_artifact_digest,
        expected_artifact_digest=manifest.artifact_sha256 or manifest.installed_record_digest,
        release_tag=manifest.release_tag,
        runtime_mode=mode,
        memory_package=manifest.distribution,
        expected_version=manifest.expected_package_version,
        expected_contract_version=manifest.expected_contract_version,
        manifest_path=manifest.path,
        interpreter=interpreter,
        memory_cli=memory_cli,
        memory_version=memory_version,
        contract_version=contract_version,
        module_path=module_path,
        path_shadow=path_shadow,
        reasons=tuple(reasons),
    )


def _select_interpreter(
    explicit: str | None, env: Mapping[str, str]
) -> tuple[str | None, str, list[str]]:
    """Return ``(interpreter, runtime_mode, reasons)`` per the manifest order."""

    reasons: list[str] = []
    if explicit:
        return explicit, MODE_PINNED, reasons
    checkout = (env.get(ENV_DEV_CHECKOUT) or "").strip()
    if checkout:
        root = Path(checkout).expanduser()
        package_dir = root / "src" / "l9_graphite_memory" / "__init__.py"
        interpreter = root / ".venv" / "bin" / "python"
        if not package_dir.is_file():
            reasons.append(f"{ENV_DEV_CHECKOUT} does not contain src/l9_graphite_memory: {root}")
            return None, MODE_DEVELOPMENT, reasons
        if not interpreter.is_file():
            reasons.append(f"{ENV_DEV_CHECKOUT} has no .venv/bin/python: {root}")
            return None, MODE_DEVELOPMENT, reasons
        return str(interpreter), MODE_DEVELOPMENT, reasons
    configured = (env.get(ENV_INTERPRETER) or "").strip()
    if configured:
        return configured, MODE_PINNED, reasons
    return sys.executable, MODE_PINNED, reasons


def resolve_runtime_binding(
    *,
    interpreter: str | None = None,
    manifest_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    runner: Runner | None = None,
    timeout: float = 30.0,
) -> RuntimeBinding:
    """Resolve and verify the memory runtime this process is allowed to use."""

    manifest = BindingManifest.load(manifest_path)
    environment = dict(os.environ if env is None else env)
    run = runner or default_runner

    selected, mode, reasons = _select_interpreter(interpreter, environment)
    if selected is None:
        return _unbound(manifest, mode=mode, reasons=reasons)
    interpreter_path = Path(selected)
    if not interpreter_path.is_file():
        return _unbound(
            manifest,
            mode=mode,
            reasons=[*reasons, f"interpreter is not a file: {selected}"],
            interpreter=selected,
        )

    # 1. Package present in *that* interpreter, at the expected version.
    try:
        probe = run(
            [str(interpreter_path), "-c", _PROBE, manifest.distribution, manifest.import_package],
            timeout=timeout,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _unbound(
            manifest,
            mode=mode,
            reasons=[*reasons, f"interpreter probe failed: {type(exc).__name__}: {exc}"],
            interpreter=str(interpreter_path),
        )
    try:
        probe_payload = json.loads((probe.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return _unbound(
            manifest,
            mode=mode,
            reasons=[*reasons, "interpreter probe emitted no JSON", (probe.stderr or "")[:300]],
            interpreter=str(interpreter_path),
        )
    version = probe_payload.get("version")
    module_path = probe_payload.get("module")
    prefix = str(probe_payload.get("prefix") or "")
    if not version or not module_path:
        return _unbound(
            manifest,
            mode=mode,
            reasons=[
                *reasons,
                f"{manifest.distribution} is not importable in {interpreter_path}: "
                f"{probe_payload.get('error') or 'unknown'}",
            ],
            interpreter=str(interpreter_path),
            memory_version=version,
            module_path=module_path,
        )
    if str(version) != manifest.expected_package_version:
        return _unbound(
            manifest,
            mode=mode,
            reasons=[
                *reasons,
                f"package version {version} does not match expected "
                f"{manifest.expected_package_version}",
            ],
            interpreter=str(interpreter_path),
            memory_version=str(version),
            module_path=str(module_path),
        )
    served_from_prefix = _path_contains(prefix, str(module_path))
    if mode == MODE_PINNED and not served_from_prefix:
        # An editable install or a .pth pointing at a checkout: the package
        # would come from somewhere the environment does not own. That is
        # only acceptable with the explicit development opt-in.
        return _unbound(
            manifest,
            mode=mode,
            reasons=[
                *reasons,
                f"package is served from outside the interpreter environment ({module_path}); "
                f"set {ENV_DEV_CHECKOUT} to bind a development checkout explicitly",
            ],
            interpreter=str(interpreter_path),
            memory_version=str(version),
            module_path=str(module_path),
        )
    if mode == MODE_DEVELOPMENT:
        checkout = Path(environment[ENV_DEV_CHECKOUT]).expanduser().resolve()
        if not _path_contains(str(checkout), str(module_path)):
            return _unbound(
                manifest,
                mode=mode,
                reasons=[
                    *reasons,
                    f"development interpreter serves {module_path}, not the checkout {checkout}",
                ],
                interpreter=str(interpreter_path),
                memory_version=str(version),
                module_path=str(module_path),
            )

    # 2. Console script from the same environment — never from PATH.
    memory_cli = interpreter_path.parent / manifest.console_script
    if not memory_cli.is_file() or not os.access(memory_cli, os.X_OK):
        return _unbound(
            manifest,
            mode=mode,
            reasons=[
                *reasons,
                f"{manifest.console_script} is not installed beside {interpreter_path}",
            ],
            interpreter=str(interpreter_path),
            memory_version=str(version),
            module_path=str(module_path),
        )
    on_path = shutil.which(manifest.console_script)
    path_shadow: str | None = None
    if on_path and Path(on_path).resolve() != memory_cli.resolve():
        path_shadow = on_path
        reasons.append(
            f"a different {manifest.console_script} is first on PATH ({on_path}); "
            "it is ignored, the bound executable is used"
        )

    # 3. Contract signal from the bound CLI itself.
    try:
        result = run([str(memory_cli), "capabilities"], timeout=timeout, env=environment)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _unbound(
            manifest,
            mode=mode,
            reasons=[*reasons, f"capabilities probe failed: {type(exc).__name__}: {exc}"],
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
        )
    if result.returncode != 0:
        return _unbound(
            manifest,
            mode=mode,
            reasons=[
                *reasons,
                f"{manifest.console_script} capabilities exited {result.returncode}; the bound "
                "package predates the control-plane contract",
            ],
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
        )
    try:
        capabilities = CapabilitiesReceipt.parse(json.loads(result.stdout))
    except (ValueError, InvalidReceiptError) as exc:
        return _unbound(
            manifest,
            mode=mode,
            reasons=[*reasons, f"capabilities receipt invalid: {exc}"],
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
        )
    if capabilities.contract_version != manifest.expected_contract_version:
        return _unbound(
            manifest,
            mode=mode,
            reasons=[
                *reasons,
                f"contract {capabilities.contract_version} does not match expected "
                f"{manifest.expected_contract_version}",
            ],
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
            contract_version=capabilities.contract_version,
        )
    if capabilities.package_version != str(version):
        return _unbound(
            manifest,
            mode=mode,
            reasons=[
                *reasons,
                f"CLI reports package {capabilities.package_version} but the interpreter "
                f"serves {version}: the executable and the import do not agree",
            ],
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
            contract_version=capabilities.contract_version,
        )
    missing = [
        operation
        for operation in manifest.required_cli_operations
        if operation not in capabilities.cli_operations
    ]
    if missing:
        return _unbound(
            manifest,
            mode=mode,
            reasons=[*reasons, f"CLI lacks required operations: {', '.join(missing)}"],
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
            contract_version=capabilities.contract_version,
        )

    schemas, schema_digest, schema_source, schema_reasons = _export_contract_schemas(
        interpreter_path, run, environment, timeout
    )
    reasons.extend(schema_reasons)

    proven, provenance, installed_digest, provenance_reasons = _verify_artifact_provenance(
        manifest, probe_payload
    )
    reasons.extend(provenance_reasons)
    if provenance == "contradicted":
        # The digest is present and disagrees: a foreign build of the pinned
        # version, which is the case a version check cannot see at all.
        return _unbound(
            manifest,
            mode=mode,
            reasons=reasons,
            artifact_provenance=provenance,
            installed_artifact_digest=installed_digest,
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
            contract_version=capabilities.contract_version,
        )

    if mode == MODE_DEVELOPMENT:
        status = STATUS_DEVELOPMENT
    elif proven:
        status = STATUS_EXACT
    else:
        status = STATUS_COMPATIBLE
    if status is STATUS_COMPATIBLE and _require_exact_artifact(environment):
        return _unbound(
            manifest,
            mode=mode,
            reasons=[
                *reasons,
                f"{ENV_REQUIRE_EXACT} demands the audited artifact and it was not proved",
            ],
            artifact_provenance=provenance,
            installed_artifact_digest=installed_digest,
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
            contract_version=capabilities.contract_version,
        )

    return RuntimeBinding(
        status=status,
        runtime_mode=mode,
        memory_package=manifest.distribution,
        expected_version=manifest.expected_package_version,
        expected_contract_version=manifest.expected_contract_version,
        manifest_path=manifest.path,
        interpreter=str(interpreter_path),
        memory_cli=str(memory_cli),
        memory_version=str(version),
        contract_version=capabilities.contract_version,
        module_path=str(module_path),
        path_shadow=path_shadow,
        capabilities=capabilities,
        reasons=tuple(reasons),
        contract_schemas=schemas,
        schema_digest=schema_digest,
        schema_source=schema_source,
        artifact_provenance=provenance,
        installed_artifact_digest=installed_digest,
        expected_artifact_digest=manifest.artifact_sha256 or manifest.installed_record_digest,
        release_tag=manifest.release_tag,
    )


def _require_exact_artifact(env: Mapping[str, str]) -> bool:
    return str(env.get(ENV_REQUIRE_EXACT, "")).strip().lower() in {"1", "true", "yes", "on"}


def _verify_artifact_provenance(
    manifest: BindingManifest, probe_payload: Mapping[str, Any]
) -> tuple[bool, str, str | None, list[str]]:
    """Decide whether the *installed artifact* is the audited release.

    Returns ``(proven, method, installed_digest, reasons)``. ``proven`` is
    False when the artifact could not be established — which yields
    STATUS_COMPATIBLE, never STATUS_EXACT.

    Version, contract and containment are all satisfied identically by two
    different builds of one version, so none of them is artifact identity.
    What distinguishes builds is a digest of the thing installed:

    - PEP 610 ``direct_url.json``: pip and uv record the archive a wheel came
      from and, when the install named a hash, that hash. This is the wheel
      sha256 the release recorded, verified in place.
    - the installed RECORD digest: RECORD lists every installed file with its
      own sha256, so a digest over it separates builds even when the install
      left no archive hash.

    A digest that is present and *disagrees* is not weak evidence, it is
    contradiction: the caller turns it into UNBOUND rather than COMPATIBLE.
    """

    reasons: list[str] = []
    direct_url = probe_payload.get("direct_url") or {}
    record_digest = _optional_text(probe_payload.get("record_digest"))

    if probe_payload.get("editable"):
        return (
            False,
            PROVENANCE_UNPROVEN,
            record_digest,
            ["installed as an editable install, which has no immutable artifact identity"],
        )

    archive = direct_url.get("archive_info") or {}
    hashes = archive.get("hashes") or {}
    installed_wheel_sha = _optional_text(hashes.get("sha256")) or _optional_text(
        archive.get("hash", "").split("=", 1)[-1] if archive.get("hash") else None
    )
    if manifest.artifact_sha256 and installed_wheel_sha:
        if installed_wheel_sha == manifest.artifact_sha256:
            return True, PROVENANCE_ARTIFACT_DIGEST, installed_wheel_sha, reasons
        return (
            False,
            "contradicted",
            installed_wheel_sha,
            [
                f"installed artifact sha256 {installed_wheel_sha} is not the audited release "
                f"{manifest.artifact_sha256}: same version, different build"
            ],
        )

    if manifest.installed_record_digest and record_digest:
        if record_digest == manifest.installed_record_digest:
            return True, PROVENANCE_RECORD_DIGEST, record_digest, reasons
        return (
            False,
            "contradicted",
            record_digest,
            [
                f"installed RECORD digest {record_digest} is not the audited release "
                f"{manifest.installed_record_digest}: same version, different build"
            ],
        )

    if not manifest.artifact_sha256 and not manifest.installed_record_digest:
        reasons.append(
            "the binding manifest records no artifact digest, so only version and contract "
            "can be proved; this is a compatible build, not the audited release"
        )
    else:
        reasons.append(
            "the installed distribution carries no artifact provenance (no PEP 610 archive "
            "hash and no readable RECORD), so the audited artifact cannot be confirmed"
        )
    return False, PROVENANCE_UNPROVEN, record_digest, reasons


def _export_contract_schemas(
    interpreter_path: Path,
    run: Runner,
    environment: Mapping[str, str],
    timeout: float,
) -> tuple[dict[str, Any] | None, str | None, str | None, list[str]]:
    """Export the bound release's own receipt schemas (CG-P1-02, Model B).

    The memory runtime may be a different interpreter, so ``import
    l9_graphite_memory.contracts`` cannot happen in this process. The schemas
    are therefore mechanically extracted from the exact pinned release and
    carried back, and the client validates against those rather than against a
    reduced Cursor-local shape.

    A failure here is reported, never fatal: the binding is still exact, and
    it is the *client* that decides whether an unvalidatable runtime may be
    used. Returning ``None`` is what makes it fail closed there.
    """

    reasons: list[str] = []
    try:
        probe = run(
            [str(interpreter_path), "-c", _SCHEMA_PROBE, ",".join(CANONICAL_RECEIPT_MODELS)],
            timeout=timeout,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, None, None, [f"contract schema export failed: {type(exc).__name__}: {exc}"]
    try:
        payload = json.loads((probe.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None, None, None, ["contract schema export emitted no JSON"]
    schemas = payload.get("schemas")
    if not isinstance(schemas, dict) or not schemas:
        detail = payload.get("error") or "the bound package exports no receipt contracts"
        return None, None, None, [f"contract schema export empty: {detail}"]
    if payload.get("missing"):
        reasons.append(
            "bound release exports no schema for: " + ", ".join(sorted(payload["missing"]))
        )
    encoded = json.dumps(schemas, sort_keys=True, separators=(",", ":"), default=str)
    return (
        schemas,
        hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        _optional_text(payload.get("module")),
        reasons,
    )


def _optional_text(value: Any) -> str | None:
    return None if value is None else str(value)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Prove the bound memory runtime")
    parser.add_argument("--interpreter", default=None)
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args(argv)
    binding = resolve_runtime_binding(
        interpreter=args.interpreter,
        manifest_path=Path(args.manifest) if args.manifest else None,
    )
    sys.stdout.write(json.dumps(binding.as_dict(), indent=2, sort_keys=True) + "\n")
    return 0 if binding.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
