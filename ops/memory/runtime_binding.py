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

The interpreter is anchored to a *governance* environment, never to whichever
Python happened to import this module. Resolution order (also declared in
``ops/config/memory-binding.json`` ``interpreter_resolution_order``):

1. an explicit ``interpreter=`` argument
2. ``L9_MEMORY_DEV_CHECKOUT`` (development opt-in, reported)
3. ``L9_MEMORY_INTERPRETER``
4. ``$L9_GOVERNANCE_DIR/.venv/bin/python``
5. ``$HOME/.cursor-governance/.venv/bin/python``
6. this checkout's ``.venv/bin/python``
7. ``sys.executable`` — only when no governance environment exists at all,
   and then reported as ``runtime_mode = caller_interpreter``

A governance candidate whose installed package disagrees with the manifest is
*lock drift*, not memory degradation: it is healed once, deterministically
(:mod:`ops.memory.environment_heal`) and re-probed before the binding gives
up. The outcome is carried on the binding as ``environment_heal``.
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

from ops.memory import environment_heal
from ops.memory.receipt_contract import ReceiptContractError, merge_receipt_schemas
from ops.memory.receipts import CapabilitiesReceipt, InvalidReceiptError

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = _REPO_ROOT / "ops" / "config" / "memory-binding.json"

ENV_DEV_CHECKOUT = "L9_MEMORY_DEV_CHECKOUT"
ENV_INTERPRETER = "L9_MEMORY_INTERPRETER"
#: The governance checkout whose ``.venv`` is the memory runtime. Set by the
#: bootstrap; absent in a bare shell, where ``$HOME/.cursor-governance`` and
#: this checkout are tried in that order.
ENV_GOVERNANCE_DIR = "L9_GOVERNANCE_DIR"
GOVERNANCE_HOME_DIRNAME = ".cursor-governance"
#: A directory counts as a governance checkout only if it carries the boundary
#: this module belongs to; ``.venv`` alone is any Python project.
_GOVERNANCE_MARKER = Path("ops") / "memory" / "control_plane_client.py"

MODE_PINNED = "pinned_environment"
MODE_DEVELOPMENT = "development_checkout"
#: No governance environment was found anywhere, so the caller's own
#: interpreter was probed. Reported, never silent: a binding in this mode is a
#: bootstrap gap even when the package it finds happens to match.
MODE_CALLER = "caller_interpreter"

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
    installer_written = ("RECORD", "INSTALLER", "REQUESTED", "direct_url.json",
                         "RECORD.jws", "RECORD.p7s")
    rows = []
    for line in record.splitlines():
        parts = line.rsplit(",", 2)
        if len(parts) != 3 or not parts[1]:
            continue
        path = parts[0].replace("\\", "/")
        if path.rsplit("/", 1)[-1] in installer_written and ".dist-info/" in path + "/":
            continue
        rows.append(path + "," + parts[1] + "," + parts[2])
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
    "DistillationReceipt",
)

# Also runs inside the *target* interpreter. It exports the pinned release's
# own pydantic models as JSON Schema so Cursor validates against the contract
# the bound package actually ships, across the interpreter boundary that makes
# an in-process import impossible in pinned mode.
_SCHEMA_PROBE = r"""
import json, sys
# argv[1] is "CursorName=Alias1|Alias2,CursorName2=...": the release names its
# own models, and a name this side guessed is not one it owes.
requests = []
for item in sys.argv[1].split(","):
    if not item:
        continue
    head, _, tail = item.partition("=")
    requests.append((head, [head] + [a for a in tail.split("|") if a]))
names = [head for head, _ in requests]
roots = [m for m in (sys.argv[2].split(",") if len(sys.argv) > 2 else []) if m]
if not roots:
    roots = ["l9_graphite_memory.contracts"]
out = {
    "schemas": {},
    "module": None,
    "error": None,
    "missing": [],
    "available": [],
    "unimportable": [],
}
try:
    import importlib, pkgutil
    sources = []
    for root in roots:
        try:
            module = importlib.import_module(root)
        except Exception as exc:
            # Report it even if a later root supplies every model: a manifest
            # that names a module the release does not have has drifted from
            # the release, and completeness elsewhere must not hide that.
            out["unimportable"].append(f"{root}: {type(exc).__name__}: {exc}")
            out["error"] = out["error"] or f"{root}: {type(exc).__name__}: {exc}"
            continue
        if out["module"] is None:
            out["module"] = getattr(module, "__file__", None)
        sources.append(module)
        # A package's __init__ re-exports only some models; the rest live in
        # submodules (receipts, capabilities, generated_data, ...).
        for info in pkgutil.iter_modules(getattr(module, "__path__", []) or []):
            try:
                sources.append(importlib.import_module(root + "." + info.name))
            except Exception:
                continue
    if not sources:
        raise ImportError("no canonical contract module was importable: " + ", ".join(roots))
    seen = set()
    for source in sources:
        for attr in dir(source):
            if attr.startswith("_"):
                continue
            candidate = getattr(source, attr, None)
            if callable(getattr(candidate, "model_json_schema", None)) and attr not in seen:
                seen.add(attr)
                out["available"].append(attr)
    out["available"].sort()
    out["available"] = out["available"][:400]
    for name, candidates in requests:
        exporter = None
        for candidate_name in candidates:
            for source in sources:
                model = getattr(source, candidate_name, None)
                exporter = (
                    getattr(model, "model_json_schema", None) if model is not None else None
                )
                if exporter is not None:
                    break
            if exporter is not None:
                break
        if exporter is None:
            out["missing"].append(name)
            continue
        try:
            out["schemas"][name] = exporter()
        except Exception as exc:
            out["missing"].append(name)
            out["error"] = out["error"] or f"{name}: {type(exc).__name__}: {exc}"
except Exception as exc:
    # Keep the first, more specific failure (which module and why) rather than
    # the generic "nothing importable" that follows from it.
    out["error"] = out["error"] or f"{type(exc).__name__}: {exc}"
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
    #: Cursor view name -> model names the bound release actually exports.
    contract_model_aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    #: Modules the schema probe searches. Named by the manifest because not
    #: every canonical model lives under the contracts package.
    contract_model_modules: tuple[str, ...] = ()

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
            contract_model_aliases={
                str(key): tuple(str(v) for v in value)
                for key, value in (raw.get("contract_model_aliases") or {}).items()
                if not str(key).startswith("_") and isinstance(value, list)
            },
            contract_model_modules=tuple(str(m) for m in (raw.get("contract_model_modules") or [])),
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
    #: The governance checkout whose ``.venv`` was bound (``None`` for an
    #: explicit interpreter, a development checkout, or the caller fallback).
    governance_root: str | None = None
    #: What the one-shot environment heal did, if drift was met:
    #: ``healed`` / ``failed`` / ``skipped:<why>`` / ``None`` (not needed).
    environment_heal: str | None = None
    #: Every interpreter probed, in order, so an unbound verdict names what
    #: was tried rather than only the last one.
    candidates_tried: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status in {STATUS_EXACT, STATUS_COMPATIBLE, STATUS_DEVELOPMENT}

    @property
    def environment_fault(self) -> bool:
        """The runtime could not be bound for an *environment* reason.

        An unbound binding is never canonical memory degradation: no memory
        operation ran, so nothing canonical was observed. It is a bootstrap /
        environment fault — a missing or drifted governance ``.venv``, a caller
        interpreter with no governance environment at all, a contract the
        installed package predates. Consumers report it as
        ``ENVIRONMENT_FAULT`` and name the heal outcome, not as ``DEGRADED``.
        A bound caller-interpreter runtime is *not* a fault — it is a reported
        bootstrap gap (``runtime_mode``), and the memory it binds is real.
        """

        return self.status == STATUS_UNBOUND

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
            "ok": self.ok,
            "artifact_provenance": self.artifact_provenance,
            "installed_artifact_digest": self.installed_artifact_digest,
            "expected_artifact_digest": self.expected_artifact_digest,
            "release_tag": self.release_tag,
            "path_shadow": self.path_shadow,
            "governance_root": self.governance_root,
            "environment_heal": self.environment_heal,
            "environment_fault": self.environment_fault,
            "candidates_tried": list(self.candidates_tried),
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
    governance_root: str | None = None,
    environment_heal: str | None = None,
    candidates_tried: Sequence[str] = (),
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
        governance_root=governance_root,
        environment_heal=environment_heal,
        candidates_tried=tuple(candidates_tried),
    )


@dataclass(frozen=True)
class InterpreterCandidate:
    """One interpreter the binding may probe, and where it came from."""

    interpreter: str
    mode: str
    #: The governance checkout owning the ``.venv`` — the only thing the heal
    #: may act on. ``None`` for explicit, configured, dev and caller choices.
    governance_root: Path | None = None


def _venv_python(root: Path) -> Path | None:
    for name in ("python", "python3"):
        candidate = root / ".venv" / "bin" / name
        if candidate.is_file():
            return candidate
    return None


def governance_roots(env: Mapping[str, str]) -> list[Path]:
    """Governance checkouts in resolution order, de-duplicated by real path."""

    ordered: list[Path] = []
    configured = (env.get(ENV_GOVERNANCE_DIR) or "").strip()
    if configured:
        ordered.append(Path(configured).expanduser())
    home = (env.get("HOME") or "").strip()
    ordered.append((Path(home) if home else Path.home()) / GOVERNANCE_HOME_DIRNAME)
    ordered.append(_REPO_ROOT)
    roots: list[Path] = []
    seen: set[Path] = set()
    for root in ordered:
        try:
            real = root.resolve()
        except (OSError, RuntimeError):
            continue
        if real in seen or not (real / _GOVERNANCE_MARKER).is_file():
            continue
        seen.add(real)
        roots.append(real)
    return roots


def interpreter_candidates(
    explicit: str | None, env: Mapping[str, str]
) -> tuple[list[InterpreterCandidate], list[str]]:
    """Interpreters to probe, in the order the module docstring declares.

    Explicit, development and ``L9_MEMORY_INTERPRETER`` choices are single
    candidates with no fallback — the caller named one runtime and gets a
    verdict about that one. Otherwise every governance ``.venv`` is a
    candidate, and ``sys.executable`` is appended only when there is none,
    tagged ``caller_interpreter`` so the report says a governance environment
    was never found.
    """

    reasons: list[str] = []
    if explicit:
        return [InterpreterCandidate(explicit, MODE_PINNED)], reasons
    checkout = (env.get(ENV_DEV_CHECKOUT) or "").strip()
    if checkout:
        root = Path(checkout).expanduser()
        package_dir = root / "src" / "l9_graphite_memory" / "__init__.py"
        interpreter = root / ".venv" / "bin" / "python"
        if not package_dir.is_file():
            reasons.append(f"{ENV_DEV_CHECKOUT} does not contain src/l9_graphite_memory: {root}")
            return [], reasons
        if not interpreter.is_file():
            reasons.append(f"{ENV_DEV_CHECKOUT} has no .venv/bin/python: {root}")
            return [], reasons
        return [InterpreterCandidate(str(interpreter), MODE_DEVELOPMENT)], reasons
    configured = (env.get(ENV_INTERPRETER) or "").strip()
    if configured:
        return [InterpreterCandidate(configured, MODE_PINNED)], reasons
    candidates: list[InterpreterCandidate] = []
    for root in governance_roots(env):
        interpreter_path = _venv_python(root)
        if interpreter_path is None:
            reasons.append(f"governance checkout {root} has no .venv/bin/python")
            continue
        candidates.append(InterpreterCandidate(str(interpreter_path), MODE_PINNED, root))
    if candidates:
        return candidates, reasons
    reasons.append(
        "no governance .venv was found "
        f"({ENV_GOVERNANCE_DIR}, $HOME/{GOVERNANCE_HOME_DIRNAME}, {_REPO_ROOT}); "
        f"probing the caller's interpreter {sys.executable} as a reported last resort"
    )
    return [InterpreterCandidate(sys.executable, MODE_CALLER)], reasons


def _probe_interpreter(
    candidate: InterpreterCandidate,
    manifest: BindingManifest,
    run: Runner,
    environment: Mapping[str, str],
    timeout: float,
) -> tuple[dict[str, Any] | None, list[str], bool]:
    """Probe one interpreter for the pinned package.

    Returns ``(payload, reasons, drift)``. ``payload`` is ``None`` on any
    failure; ``drift`` is True only for the one failure a locked sync can
    repair — the package is absent or at another version inside a governance
    ``.venv`` — so the caller heals exactly that and nothing else.
    """

    interpreter_path = Path(candidate.interpreter)
    if not interpreter_path.is_file():
        return None, [f"interpreter is not a file: {candidate.interpreter}"], False
    try:
        probe = run(
            [str(interpreter_path), "-c", _PROBE, manifest.distribution, manifest.import_package],
            timeout=timeout,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, [f"interpreter probe failed: {type(exc).__name__}: {exc}"], False
    try:
        payload = json.loads((probe.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None, ["interpreter probe emitted no JSON", (probe.stderr or "")[:300]], False
    version = payload.get("version")
    module_path = payload.get("module")
    healable = candidate.governance_root is not None and candidate.mode == MODE_PINNED
    if not version or not module_path:
        return (
            None,
            [
                f"{manifest.distribution} is not importable in {interpreter_path}: "
                f"{payload.get('error') or 'unknown'}"
            ],
            healable,
        )
    if str(version) != manifest.expected_package_version:
        return (
            None,
            [
                f"package version {version} does not match expected "
                f"{manifest.expected_package_version} in {interpreter_path}"
            ],
            healable,
        )
    return payload, [], False


def resolve_runtime_binding(
    *,
    interpreter: str | None = None,
    manifest_path: Path | None = None,
    env: Mapping[str, str] | None = None,
    runner: Runner | None = None,
    timeout: float = 30.0,
    heal: Callable[..., tuple[str, list[str]]] | None = None,
) -> RuntimeBinding:
    """Resolve and verify the memory runtime this process is allowed to use."""

    manifest = BindingManifest.load(manifest_path)
    environment = dict(os.environ if env is None else env)
    run = runner or default_runner
    heal_environment = heal or environment_heal.heal_environment

    candidates, reasons = interpreter_candidates(interpreter, environment)
    if not candidates:
        return _unbound(manifest, mode=MODE_DEVELOPMENT, reasons=reasons)

    # 1. Package present in a governance interpreter, at the expected version.
    #    Every candidate is probed in order; the first that carries the pinned
    #    package wins. Drift in a governance .venv is healed once and re-probed
    #    before the binding gives up, and what happened is carried on the
    #    binding rather than swallowed.
    tried: list[str] = []
    probe_payload: dict[str, Any] | None = None
    chosen: InterpreterCandidate | None = None
    heal_outcome: str | None = None
    drifted: list[tuple[InterpreterCandidate, list[str]]] = []
    for candidate in candidates:
        tried.append(candidate.interpreter)
        payload, probe_reasons, drift = _probe_interpreter(
            candidate, manifest, run, environment, timeout
        )
        if payload is not None:
            probe_payload, chosen = payload, candidate
            break
        reasons.extend(probe_reasons)
        if drift:
            drifted.append((candidate, probe_reasons))
    if probe_payload is None:
        for candidate, _ in drifted:
            root = candidate.governance_root
            assert root is not None  # noqa: S101 - guaranteed by drift=True
            heal_outcome, heal_reasons = heal_environment(root, env=environment, timeout=timeout)
            reasons.append(f"environment heal on {root}: {heal_outcome}")
            reasons.extend(heal_reasons)
            if heal_outcome != environment_heal.HEAL_HEALED:
                continue
            payload, probe_reasons, _ = _probe_interpreter(
                candidate, manifest, run, environment, timeout
            )
            if payload is not None:
                probe_payload, chosen = payload, candidate
                break
            reasons.extend(f"after heal: {reason}" for reason in probe_reasons)
    if probe_payload is None or chosen is None:
        last = candidates[-1]
        return _unbound(
            manifest,
            mode=last.mode,
            reasons=reasons,
            interpreter=last.interpreter,
            governance_root=str(last.governance_root) if last.governance_root else None,
            environment_heal=heal_outcome,
            candidates_tried=tried,
        )

    mode = chosen.mode
    interpreter_path = Path(chosen.interpreter)
    governance_root = str(chosen.governance_root) if chosen.governance_root else None

    def fail(**kwargs: Any) -> RuntimeBinding:
        return _unbound(
            manifest,
            mode=mode,
            governance_root=governance_root,
            environment_heal=heal_outcome,
            candidates_tried=tried,
            **kwargs,
        )

    version = probe_payload["version"]
    module_path = probe_payload["module"]
    prefix = str(probe_payload.get("prefix") or "")
    served_from_prefix = _path_contains(prefix, str(module_path))
    if mode != MODE_DEVELOPMENT and not served_from_prefix:
        # An editable install or a .pth pointing at a checkout: the package
        # would come from somewhere the environment does not own. That is
        # only acceptable with the explicit development opt-in.
        return fail(
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
        return fail(
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
        return fail(
            reasons=[*reasons, f"capabilities probe failed: {type(exc).__name__}: {exc}"],
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
        )
    if result.returncode != 0:
        return fail(
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
        return fail(
            reasons=[*reasons, f"capabilities receipt invalid: {exc}"],
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
        )
    if capabilities.contract_version != manifest.expected_contract_version:
        return fail(
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
        return fail(
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
        return fail(
            reasons=[*reasons, f"CLI lacks required operations: {', '.join(missing)}"],
            interpreter=str(interpreter_path),
            memory_cli=str(memory_cli),
            memory_version=str(version),
            module_path=str(module_path),
            path_shadow=path_shadow,
            contract_version=capabilities.contract_version,
        )

    schemas, schema_digest, schema_source, schema_reasons = _export_contract_schemas(
        interpreter_path,
        run,
        environment,
        timeout,
        manifest.contract_model_aliases,
        manifest.contract_model_modules,
    )
    reasons.extend(schema_reasons)
    try:
        schemas, merged_source = merge_receipt_schemas(schemas)
        encoded = json.dumps(schemas, sort_keys=True, separators=(",", ":"), default=str)
        schema_digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        schema_source = (
            merged_source if schema_source is None else f"{schema_source}+{merged_source}"
        )
    except ReceiptContractError as exc:
        reasons.append(f"canonical receipt contract unavailable: {exc}")

    proven, provenance, installed_digest, provenance_reasons = _verify_artifact_provenance(
        manifest, probe_payload
    )
    reasons.extend(provenance_reasons)
    # Same release version, different wheel bytes is compatible, not unbound:
    # generated-data ingest and governed writes still run. Exactness is a
    # proof, not a write latch. L9_MEMORY_REQUIRE_EXACT_ARTIFACT fail-closes.

    if mode == MODE_DEVELOPMENT:
        status = STATUS_DEVELOPMENT
    elif proven:
        status = STATUS_EXACT
    else:
        status = STATUS_COMPATIBLE
    if status is STATUS_COMPATIBLE and _require_exact_artifact(environment):
        return fail(
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
        governance_root=governance_root,
        environment_heal=heal_outcome,
        candidates_tried=tuple(tried),
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

    A digest that is present and *disagrees* is not exactness: it is a
    different build of the same version. The caller reports STATUS_COMPATIBLE
    so generated-data ingest and governed writes still run. Exactness is a
    proof, not a write latch. ``L9_MEMORY_REQUIRE_EXACT_ARTIFACT`` fail-closes.
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
    elif manifest.artifact_sha256 and not installed_wheel_sha:
        reasons.append(
            "the install recorded no PEP 610 archive hash, so the wheel digest "
            f"{manifest.artifact_sha256} cannot be verified in place"
            + (
                f"; the installed RECORD digest is {record_digest} — pin it as "
                "release_evidence.installed_record_digest to make this binding exact"
                if record_digest
                else " and the installed RECORD is unreadable"
            )
        )
    else:
        reasons.append(
            "the installed distribution carries no artifact provenance, so the audited "
            "artifact cannot be confirmed"
        )
    return False, PROVENANCE_UNPROVEN, record_digest, reasons


def _export_contract_schemas(
    interpreter_path: Path,
    run: Runner,
    environment: Mapping[str, str],
    timeout: float,
    aliases: Mapping[str, Sequence[str]] | None = None,
    modules: Sequence[str] = (),
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
            [
                str(interpreter_path),
                "-c",
                _SCHEMA_PROBE,
                ",".join(
                    name + "=" + "|".join((aliases or {}).get(name, ()))
                    for name in CANONICAL_RECEIPT_MODELS
                ),
                ",".join(modules),
            ],
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
    if payload.get("unimportable"):
        reasons.append(
            "binding manifest names a contract module the bound release does not have: "
            + "; ".join(str(item) for item in payload["unimportable"])
        )
    if payload.get("missing"):
        available = payload.get("available") or []
        reasons.append(
            "bound release exports no schema for: "
            + ", ".join(sorted(payload["missing"]))
            + "; it exports: "
            + (", ".join(available[:40]) if available else "(none)")
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
