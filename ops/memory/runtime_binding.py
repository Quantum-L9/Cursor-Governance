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
STATUS_DEVELOPMENT = "development_checkout"
STATUS_UNBOUND = "unbound"

Runner = Callable[..., "subprocess.CompletedProcess[str]"]

# Runs inside the *target* interpreter: it must not assume this repository's
# environment, only the standard library.
_PROBE = r"""
import json, sys
dist, pkg = sys.argv[1], sys.argv[2]
out = {"interpreter": sys.executable, "prefix": sys.prefix, "version": None, "module": None}
out["error"] = None
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

    @classmethod
    def load(cls, path: Path | None = None) -> BindingManifest:
        manifest_path = Path(path or DEFAULT_MANIFEST_PATH)
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        source = raw.get("source") or {}
        return cls(
            distribution=str(raw["distribution"]),
            import_package=str(raw["import_package"]),
            console_script=str(raw["console_script"]),
            expected_package_version=str(raw["expected_package_version"]),
            expected_contract_version=str(raw["expected_contract_version"]),
            required_cli_operations=tuple(str(item) for item in raw["required_cli_operations"]),
            source_ref=str(source["ref"]) if source.get("ref") else None,
            path=str(manifest_path),
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

    @property
    def ok(self) -> bool:
        return self.status in {STATUS_EXACT, STATUS_DEVELOPMENT}

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
) -> RuntimeBinding:
    return RuntimeBinding(
        status=STATUS_UNBOUND,
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
    served_from_prefix = prefix and str(module_path).startswith(prefix)
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
        if not Path(str(module_path)).resolve().is_relative_to(checkout):
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

    return RuntimeBinding(
        status=STATUS_DEVELOPMENT if mode == MODE_DEVELOPMENT else STATUS_EXACT,
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
    )


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
