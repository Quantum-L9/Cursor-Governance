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
import textwrap
import unittest
from pathlib import Path

from peer_execution.imports import (
    PE_SCRIPTS_PACKAGE,
    bind_pe_scripts,
    pe_script,
)

PE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PE_ROOT.parents[1]
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


if __name__ == "__main__":
    unittest.main()
