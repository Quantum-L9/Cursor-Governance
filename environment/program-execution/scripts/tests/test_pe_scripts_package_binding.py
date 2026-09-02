"""Regression: Program Execution must resolve its OWN `scripts/` package.

The repository root ships a `scripts/` package, and the root pytest suite runs
with PYTHONPATH=${REPO_ROOT} (ops/config/python-contract.json, suite
`repo-root`), so both providers of the top-level name `scripts` are importable
in one interpreter.

Python binds a top-level package name once per process. Before this suite
existed, five Program Execution modules did `from scripts.provider_loader
import ...`; whichever provider reached `sys.modules["scripts"]` first owned the
name for the rest of the process, and `sys.path.insert(0, PE_ROOT)` could not
take it back -- the name already resolved, so no finder ran again.

These tests pin the repaired contract: resolution is by file location under a
PE-exclusive name, so it does not depend on collection order, on which suite
ran first, or on whether some unrelated module already bound `scripts`.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import ModuleType

PE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PE_ROOT.parents[1]

# APPEND, never insert(0). This file is collected by BOTH suites: the root
# pytest suite (PYTHONPATH=${REPO_ROOT}, where `peer_execution` is not
# importable without this) and `make program-execution-conformance`
# (PYTHONPATH=PE_ROOT, where it already is). Prepending would make Program
# Execution's `scripts/` win the shared top-level name for the rest of the
# session -- the very defect this file exists to pin.
if str(PE_ROOT) not in sys.path:
    sys.path.append(str(PE_ROOT))

from peer_execution.imports import (  # noqa: E402
    PE_SCRIPTS_PACKAGE,
    bind_pe_scripts,
    load_package,
    pe_script,
)

PE_SCRIPTS_DIR = PE_ROOT / "scripts"
ROOT_SCRIPTS_DIR = REPO_ROOT / "scripts"

#: Every Program Execution module that reaches into its own `scripts/` package.
CALL_SITES = (
    "run_peer_task_pipeline",
    "probe_executable_peers",
    "probe_execution_adapters",
    "peer_execution_cli",
    "adapter_cli",
)


def _run_probe(body: str) -> subprocess.CompletedProcess[str]:
    """Run `body` in a fresh interpreter with BOTH `scripts` providers reachable.

    PYTHONPATH is the repository root, exactly as the `repo-root` pytest suite
    sets it, so repo-root `scripts` is importable; PE_ROOT is added by the
    snippet itself, mirroring what the Program Execution CLIs do.
    """
    return subprocess.run(
        [sys.executable, "-B", "-c", textwrap.dedent(body)],
        cwd=REPO_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": str(REPO_ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": str(Path.home()),
        },
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


class TwoScriptsProvidersExistTests(unittest.TestCase):
    """The collision this suite defends against must still be real."""

    def test_both_providers_are_importable_packages(self) -> None:
        self.assertTrue((ROOT_SCRIPTS_DIR / "__init__.py").is_file())
        self.assertTrue((PE_SCRIPTS_DIR / "__init__.py").is_file())
        self.assertNotEqual(ROOT_SCRIPTS_DIR, PE_SCRIPTS_DIR)

    def test_bare_scripts_import_is_still_ambiguous(self) -> None:
        """Sanity check on the mechanism, not on our code.

        If this ever fails, the two providers stopped colliding and the rest of
        this suite is guarding nothing -- which is worth knowing loudly.
        """
        probe = f"""
            import sys
            sys.path.insert(0, {str(REPO_ROOT)!r})
            import scripts
            sys.path.insert(0, {str(PE_ROOT)!r})
            try:
                import scripts.provider_loader  # noqa: F401
            except ModuleNotFoundError:
                print("AMBIGUOUS")
            else:
                print("RESOLVED")
        """
        result = _run_probe(probe)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "AMBIGUOUS")


class BinderIdentityTests(unittest.TestCase):
    def test_binds_program_execution_scripts_directory(self) -> None:
        package = bind_pe_scripts()
        bound = [Path(entry).resolve() for entry in package.__path__]
        self.assertEqual(bound, [PE_SCRIPTS_DIR.resolve()])

    def test_binding_is_idempotent(self) -> None:
        self.assertIs(bind_pe_scripts(), bind_pe_scripts())

    def test_repeated_module_access_returns_one_instance(self) -> None:
        first = pe_script("provider_loader")
        second = pe_script("provider_loader")
        self.assertIs(first, second)

    def test_module_origin_is_program_execution(self) -> None:
        module = pe_script("provider_loader")
        self.assertEqual(
            Path(module.__file__ or "").resolve(),
            (PE_SCRIPTS_DIR / "provider_loader.py").resolve(),
        )

    def test_rejects_a_non_sibling_name(self) -> None:
        for bad in ("", ".provider_loader", "sub/provider_loader"):
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    pe_script(bad)

    def test_pe_scripts_name_is_not_the_colliding_name(self) -> None:
        self.assertNotEqual(PE_SCRIPTS_PACKAGE, "scripts")


class LoadPackageTests(unittest.TestCase):
    """The generic primitive, including the paths only failure reaches.

    `load_package` became public API when the PE accessor was split off it, so
    its refusals are contract, not incidental behaviour.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _package(self, name: str, body: str = "VALUE = 1\n") -> Path:
        directory = self.root / name
        directory.mkdir()
        (directory / "__init__.py").write_text(body, encoding="utf-8")
        return directory

    def _bind(self, directory: Path, name: str) -> ModuleType:
        module = load_package(directory, name)
        self.addCleanup(sys.modules.pop, name, None)
        return module

    def test_binds_the_directory_it_was_given(self) -> None:
        directory = self._package("alpha")
        module = self._bind(directory, "l9_test_alpha")
        self.assertEqual(module.VALUE, 1)
        self.assertEqual([Path(p) for p in module.__path__], [directory])

    def test_rebinding_the_same_directory_returns_one_instance(self) -> None:
        directory = self._package("beta")
        first = self._bind(directory, "l9_test_beta")
        first.MARKER = object()  # module-level state must survive
        second = load_package(directory, "l9_test_beta")
        self.assertIs(first, second)
        self.assertIs(second.MARKER, first.MARKER)

    def test_refuses_to_steal_a_name_bound_elsewhere(self) -> None:
        self._bind(self._package("gamma"), "l9_test_clash")
        other = self._package("delta")
        with self.assertRaises(ImportError) as ctx:
            load_package(other, "l9_test_clash")
        self.assertIn("already bound", str(ctx.exception))
        # The incumbent binding must survive the refusal untouched.
        self.assertEqual(
            [Path(p) for p in sys.modules["l9_test_clash"].__path__],
            [self.root / "gamma"],
        )

    def test_refuses_a_directory_that_is_not_a_package(self) -> None:
        bare = self.root / "not_a_package"
        bare.mkdir()
        with self.assertRaises(ImportError) as ctx:
            load_package(bare, "l9_test_bare")
        self.assertIn("not a package", str(ctx.exception))
        self.assertNotIn("l9_test_bare", sys.modules)

    def test_refuses_a_symlinked_package_directory(self) -> None:
        """The control `load_module` applies to a file, applied to a package."""
        real = self._package("real_pkg")
        link = self.root / "linked_pkg"
        link.symlink_to(real, target_is_directory=True)
        with self.assertRaises(ImportError) as ctx:
            load_package(link, "l9_test_symlink_dir")
        self.assertIn("refusing symlinked package source", str(ctx.exception))
        self.assertNotIn("l9_test_symlink_dir", sys.modules)

    def test_refuses_a_symlinked_package_init(self) -> None:
        real = self._package("init_donor")
        directory = self.root / "linked_init"
        directory.mkdir()
        (directory / "__init__.py").symlink_to(real / "__init__.py")
        with self.assertRaises(ImportError) as ctx:
            load_package(directory, "l9_test_symlink_init")
        self.assertIn("refusing symlinked package source", str(ctx.exception))
        self.assertNotIn("l9_test_symlink_init", sys.modules)

    def test_a_failing_package_body_leaves_no_half_bound_module(self) -> None:
        directory = self._package("explodes", body="raise RuntimeError('boom')\n")
        with self.assertRaises(RuntimeError):
            load_package(directory, "l9_test_explodes")
        self.assertNotIn("l9_test_explodes", sys.modules)


class ForeignBindingTests(unittest.TestCase):
    """The repair must hold whatever already owns `sys.modules['scripts']`."""

    def test_resolves_after_repo_root_scripts_is_bound_first(self) -> None:
        probe = f"""
            import sys
            from pathlib import Path

            import scripts  # repo-root provider wins the bare name
            root = Path({str(ROOT_SCRIPTS_DIR)!r}).resolve()
            assert Path(scripts.__file__).resolve().parent == root

            sys.path.insert(0, {str(PE_ROOT)!r})
            from peer_execution.imports import pe_script

            loader = pe_script("provider_loader")
            print(Path(loader.__file__).resolve())
            # The foreign binding must be left exactly as it was found.
            print(Path(sys.modules["scripts"].__file__).resolve().parent)
        """
        result = _run_probe(probe)
        self.assertEqual(result.returncode, 0, result.stderr)
        resolved, foreign = result.stdout.split()
        self.assertEqual(Path(resolved), (PE_SCRIPTS_DIR / "provider_loader.py").resolve())
        self.assertEqual(Path(foreign), ROOT_SCRIPTS_DIR.resolve())

    def test_resolves_when_program_execution_is_imported_first(self) -> None:
        probe = f"""
            import sys
            from pathlib import Path

            sys.path.append({str(PE_ROOT)!r})
            from peer_execution.imports import pe_script

            loader = pe_script("provider_loader")

            import scripts  # repo-root provider, imported afterwards
            from scripts.generate_subsystem_readmes import main  # noqa: F401

            print(Path(loader.__file__).resolve())
            print(Path(scripts.__file__).resolve().parent)
        """
        result = _run_probe(probe)
        self.assertEqual(result.returncode, 0, result.stderr)
        resolved, foreign = result.stdout.split()
        self.assertEqual(Path(resolved), (PE_SCRIPTS_DIR / "provider_loader.py").resolve())
        self.assertEqual(Path(foreign), ROOT_SCRIPTS_DIR.resolve())

    def test_pipeline_cli_does_not_shadow_the_repository_root_package(self) -> None:
        """`run_peer_task_pipeline` adds PE_ROOT to sys.path for its own packages.

        It must not do so at position 0: that would make Program Execution's
        `scripts/` win the ambiguous name for everything else in the process --
        the exact bug, pointed the other way.
        """
        probe = f"""
            import sys
            from pathlib import Path

            sys.path.append({str(PE_ROOT)!r})
            from peer_execution.imports import load_module

            load_module(
                Path({str(PE_SCRIPTS_DIR)!r}) / "run_peer_task_pipeline.py",
                "pe_pipeline_under_test",
            )

            import scripts
            from scripts.generate_subsystem_readmes import main  # noqa: F401
            print(Path(scripts.__file__).resolve().parent)
        """
        result = _run_probe(probe)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()), ROOT_SCRIPTS_DIR.resolve())


class CallSiteTests(unittest.TestCase):
    """Every implicated module, under a hostile pre-existing `scripts` binding."""

    def test_no_module_imports_the_ambiguous_name(self) -> None:
        """No Program Execution module may import the top-level name `scripts`.

        Parsed, not grepped: this file embeds `import scripts` inside probe
        source strings on purpose, and a substring scan would flag itself.
        """
        offenders: list[str] = []
        for path in sorted(PE_ROOT.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover - fixture corpora
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level == 0:
                    root = (node.module or "").split(".")[0]
                elif isinstance(node, ast.Import):
                    root = next(
                        (
                            alias.name.split(".")[0]
                            for alias in node.names
                            if alias.name.split(".")[0] == "scripts"
                        ),
                        "",
                    )
                else:
                    continue
                if root == "scripts":
                    offenders.append(f"{path.relative_to(PE_ROOT)}:{node.lineno}")
        self.assertEqual(offenders, [], f"ambiguous `scripts` imports: {offenders}")

    def test_every_call_site_imports_with_repo_root_scripts_bound(self) -> None:
        for name in CALL_SITES:
            with self.subTest(module=name):
                probe = f"""
                    import sys
                    from pathlib import Path

                    import scripts  # bind the foreign provider first
                    sys.path.insert(0, {str(PE_ROOT)!r})

                    from peer_execution.imports import load_module

                    module = load_module(
                        Path({str(PE_SCRIPTS_DIR)!r}) / "{name}.py",
                        "pe_call_site_under_test",
                    )
                    print(module.__name__)
                """
                result = _run_probe(probe)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "pe_call_site_under_test")


class SysPathHygieneTests(unittest.TestCase):
    """No Program Execution module may PREPEND the subsystem root to sys.path.

    `scripts` is the only top-level name Program Execution and the repository
    root both define, so a prepend hands PE's `scripts/` that name for the whole
    process -- the mirror of the bug this file pins. Appending still resolves
    every PE-exclusive package (`peer_execution`, `compiler`, `adapters`,
    `integrations`), which is all any of these call sites actually needs.
    """

    def test_no_module_prepends_the_subsystem_root(self) -> None:
        offenders: list[str] = []
        for path in sorted(PE_ROOT.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover - fixture corpora
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute) or func.attr != "insert":
                    continue
                value = func.value
                if not (
                    isinstance(value, ast.Attribute)
                    and value.attr == "path"
                    and isinstance(value.value, ast.Name)
                    and value.value.id == "sys"
                ):
                    continue
                if not node.args or not isinstance(node.args[0], ast.Constant):
                    continue
                if node.args[0].value != 0:
                    continue
                if _is_subsystem_root(node.args[1] if len(node.args) > 1 else None):
                    offenders.append(f"{path.relative_to(PE_ROOT)}:{node.lineno}")
        self.assertEqual(offenders, [], f"sys.path.insert(0, PE_ROOT): {offenders}")


def _is_subsystem_root(node: ast.AST | None) -> bool:
    """True when `node` is a ROOT variable itself, not a directory under one.

    `sys.path.insert(0, str(PE_ROOT / "scripts"))` is a different thing: it
    exposes bare module names, never the `scripts` PACKAGE, so it cannot win
    the shared top-level name. A path join is therefore what separates the safe
    form from the unsafe one.

    Any name containing "root" counts, case-insensitively. The first cut
    matched an allow-list of spellings and missed `root` (lowercase) and then
    `_PE_ROOT_FOR_IMPORT` -- a live prepend of the subsystem root that ran
    inside every `make campaign` -- because the spelling was not on the list.
    The import system does not care how the variable is spelled.
    """
    if node is None:
        return False
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id != "str" or not node.args:
            return False
        node = node.args[0]
    return isinstance(node, ast.Name) and "root" in node.id.lower()


class BareNameBindingTests(unittest.TestCase):
    """Two different modules must never compete for one bare name inside PE.

    `instantiate.py` exists in BOTH template `scripts/` directories with
    different contracts. Whichever directory was prepended last decided which
    one a bare `import instantiate` bound -- so the Blueprint synthesizer could
    receive the controller renderer, which has no `render_tree`.
    """

    BLUEPRINT_RENDERER = (
        PE_ROOT / "core/program-execution-blueprint-template/scripts/instantiate.py"
    )
    CONTROLLER_SCRIPTS = PE_ROOT / "core/program-execution-controller-template/scripts"

    def test_no_program_execution_module_binds_the_renderer_by_bare_name(self) -> None:
        offenders: list[str] = []
        for path in sorted(PE_ROOT.rglob("*.py")):
            if "/campaigns/" in path.as_posix():
                continue  # frozen campaign snapshots are not live code
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:  # pragma: no cover - fixture corpora
                continue
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                if any(name.split(".")[0] == "instantiate" for name in names):
                    offenders.append(f"{path.relative_to(PE_ROOT)}:{node.lineno}")
        self.assertEqual(offenders, [], f"bare `instantiate` imports: {offenders}")

    def test_synthesizer_binds_the_blueprint_renderer_under_hostile_order(self) -> None:
        probe = f"""
            import sys
            from pathlib import Path
            sys.path.insert(0, {str(self.CONTROLLER_SCRIPTS)!r})
            sys.path.append({str(PE_ROOT)!r})
            import instantiate  # the CONTROLLER renderer wins the bare name
            import compiler.synthesizer as synthesizer
            print(Path(instantiate.__file__).resolve())
            print(Path(synthesizer.instantiate.__file__).resolve())
            print(hasattr(synthesizer.instantiate, "render_tree"))
        """
        result = _run_probe(probe)
        self.assertEqual(result.returncode, 0, result.stderr)
        bare, bound, renders = result.stdout.split()
        self.assertEqual(Path(bare), self.CONTROLLER_SCRIPTS / "instantiate.py")
        self.assertEqual(Path(bound), self.BLUEPRINT_RENDERER.resolve())
        self.assertEqual(renders, "True")

    def test_campaign_runner_binds_pec_by_location_without_touching_sys_path(self) -> None:
        probe = f"""
            import sys
            from pathlib import Path
            sys.path.append({str(PE_ROOT)!r})
            from peer_execution.imports import load_module
            runner = load_module(
                Path({str(PE_SCRIPTS_DIR)!r}) / "run_campaign.py", "pe_runner_probe"
            )
            before = list(sys.path)
            package = runner._bind_pec_package()
            print(Path(package.__path__[0]).resolve())
            print({str(self.CONTROLLER_SCRIPTS)!r} in sys.path)
            print(sys.path == before)
            from pec.controller import ensure_campaign_active  # noqa: F401
            print("import-ok")
        """
        result = _run_probe(probe)
        self.assertEqual(result.returncode, 0, result.stderr)
        bound, exposed, unchanged, ok = result.stdout.split()
        self.assertEqual(Path(bound), (self.CONTROLLER_SCRIPTS / "pec").resolve())
        self.assertEqual(exposed, "False")
        self.assertEqual(unchanged, "True")
        self.assertEqual(ok, "import-ok")

    def test_mission_consumers_refuse_a_namespace_binding(self) -> None:
        """`mission/` is importable as an empty namespace package from PE_ROOT."""
        probe = f"""
            import sys
            sys.path.append({str(PE_ROOT)!r})
            import mission  # binds the DIRECTORY, not mission.py
            assert not getattr(mission, "__file__", None), mission
            try:
                import compiler.mission_admission  # noqa: F401
            except ImportError as exc:
                print("REFUSED" if "namespace" in str(exc) else f"WRONG: {{exc}}")
            else:
                print("SILENT")
        """
        result = _run_probe(probe)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "REFUSED")


class RuntimeRootAuthorityTests(unittest.TestCase):
    """Runtime paths come from `environment/agents/runtime_paths.py`, by location."""

    def test_peer_probe_resolves_the_canonical_readiness_root(self) -> None:
        probe = f"""
            import os, sys
            from pathlib import Path
            os.environ["L9_RUNTIME_ROOT"] = {str(REPO_ROOT / ".l9-probe-root")!r}
            sys.path.append({str(PE_ROOT)!r})
            from peer_execution.imports import load_module, pe_script
            before = list(sys.path)
            resolved = pe_script("probe_executable_peers")._resolve_runtime_root()
            canonical = load_module(
                Path({str(REPO_ROOT)!r}) / "environment/agents/runtime_paths.py",
                "probe_runtime_paths",
            ).peer_readiness_root()
            print(resolved == canonical)
            print(sys.path == before)
            print(str(resolved).endswith("agents/readiness"))
        """
        result = _run_probe(probe)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["True", "True", "True"])

    def test_no_legacy_readiness_literal_remains(self) -> None:
        for name in ("probe_executable_peers.py", "probe_execution_adapters.py"):
            text = (PE_SCRIPTS_DIR / name).read_text(encoding="utf-8")
            # Quoted literals are code; the prose in docstrings may name the
            # legacy layout to explain why it is gone.
            self.assertNotIn('"_peer-readiness"', text, name)
            self.assertNotIn('Path.home() / ".l9"', text, name)
            self.assertNotIn('"~/.l9', text, name)
