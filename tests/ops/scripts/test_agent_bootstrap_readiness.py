"""Full-script bootstrap proofs, not extracted or sliced reproductions.

All execution occurs in synthetic source/governance/workspace/HOME trees. No
installed environment is modified and no service is contacted. Every network or
mutation executable is absent or guarded; apply collaborators are explicit
fixture stubs. Check snapshots include every file, directory, symlink, mode,
mtime and byte, including Git, HOME, bytecode, UV locks and cached receipts.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import venv
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
BOOTSTRAP = "ops/scripts/bootstrap_agent_environment.sh"
ENSURE = "ops/scripts/ensure_uv_environment.sh"
WRITER = "ops/scripts/write_runtime_readiness_receipt.py"
INSTALLER = "environment/agents/adapters/manus/install.sh"
REAL_GIT = shutil.which("git")
REAL_PYTHON = sys.executable


def put(path: Path, content: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def snapshot(root: Path) -> dict[str, tuple[int, int, bytes | str]]:
    """No ignored-path exclusions and no symlink traversal outside the fixture."""
    result = {}
    for path in [root, *sorted(root.rglob("*"))]:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            content: bytes | str = os.readlink(path)
        elif stat.S_ISREG(info.st_mode):
            content = path.read_bytes()
        else:
            content = "DIRECTORY"
        result[str(path.relative_to(root))] = (info.st_mode, info.st_mtime_ns, content)
    return result


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        # Auto-maintenance off: git detaches `maintenance run --auto` after a
        # commit, and its objects/maintenance.lock appearing and vanishing
        # mid-copytree raced the fixture clone (shutil.Error in CI).
        [str(REAL_GIT), "-c", "maintenance.auto=false", "-c", "gc.auto=0", "-C", str(root), *args],
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(root),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_AUTHOR_NAME": "Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        },
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class BootstrapTree:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.source = root / "source"
        self.gov = root / "governance"
        self.ws = root / "workspace"
        self.home = root / "home"
        self.bin = root / "bin"
        for directory in (self.source, self.ws, self.home, self.bin):
            directory.mkdir()
        for name in (BOOTSTRAP, ENSURE, WRITER, INSTALLER):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, target)
            assert target.read_bytes() == (REPO / name).read_bytes()
        for name in (
            "ops/scripts/uv_environment_lock.py",
            "ops/scripts/lib/session_git_excludes.sh",
            "ops/scripts/lib/git_remote_head.sh",
            "environment/agents/runtime_paths.py",
        ):
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / name, target)
        # Real path-rule and L4 status owners, with their local imports. Nothing
        # calls the full event gate in check, even with L4 breakglass enabled.
        for path in (REPO / "ops/autonomy").glob("*.py"):
            target = self.source / "ops/autonomy" / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        for name in ("surface_profile.yaml", "l4-local-autonomy.contract.json"):
            original = REPO / "ops/autonomy" / name
            if original.is_file():
                shutil.copy2(original, self.source / "ops/autonomy" / name)
        put(self.source / "CANONICAL_LAW.md", "Synthetic authority\n")
        put(self.source / ".python-version", f"{sys.version_info.major}.{sys.version_info.minor}\n")
        put(self.source / "pyproject.toml", '[project]\nname="fixture"\nversion="1.0"\n')
        put(self.source / "uv.lock", "version = 1\n")
        put(self.source / ".pre-commit-config.yaml", "repos: []\n")
        for kernel in ("Recursive Alignment.md", "Validate & Repair.md"):
            put(self.source / "kernels" / kernel, "Synthetic kernel\n")
        put(
            self.source / "ops/memory/namespace_context.py",
            "import os\nfrom types import SimpleNamespace\n"
            "def resolve_namespace_context(root):\n"
            "    assert os.environ['L9_GOVERNANCE_SURFACE'] == 'manus'\n"
            "    assert os.environ['PYTHONDONTWRITEBYTECODE'] == '1'\n"
            "    return SimpleNamespace(write_namespace_hint='fixture', method='fixture')\n",
        )
        self.auth_stub(self.source, fail_on_call=True)
        put(
            self.source / "ops/scripts/scratch_hold.py", "raise RuntimeError('FORBIDDEN scratch')\n"
        )
        put(
            self.source / "environment/agents/adapters/manus/validate_manus_adapter.py",
            "import os, sys\n"
            "print('VALIDATOR ' + sys.executable)\n"
            "assert os.environ['PYTHONDONTWRITEBYTECODE'] == '1'\n"
            "raise SystemExit(int(os.environ.get('VALIDATOR_EXIT', '0')))\n",
        )
        git(self.source, "init", "-q")
        git(self.source, "add", ".")
        git(self.source, "commit", "-qm", "Synthetic source fixture")
        # An independent clone has the same starting revision without a remote.
        shutil.copytree(self.source, self.gov, symlinks=True)
        git(self.ws, "init", "-q")
        put(self.ws / "consumer.txt", "Unrelated consumer\n")
        git(self.ws, "add", ".")
        git(self.ws, "commit", "-qm", "Unrelated consumer fixture")
        self.make_venv()
        put(self.ws / ".l9/session/secrets-plane.json", '{"ok":true,"state":"ready"}\n')
        put(self.home / ".infisical/l9-machine.json", '{"fixture":"cached operator shape"}\n')
        put(
            self.home / ".l9/agents/readiness/runtime/manus/cached.json",
            '{"overall_status":"READY"}\n',
        )
        self.install_tools()
        self.env = {
            "PATH": str(self.bin),
            "HOME": str(self.home),
            "L9_RUNTIME_ROOT": str(self.home / ".l9"),
            "LANG": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "L9_GOVERNANCE_SURFACE": "wrong-inherited-surface",
            "L9_LOCAL_PUSH_AUTHORIZED": "fixture human breakglass",
            "L9_L4_LOCAL_AUTONOMY": "0",
            "PYTHONDONTWRITEBYTECODE": "0",
        }
        self.cache_fingerprint()

    def make_venv(self, alias: str = "both") -> None:
        target = self.gov / ".venv"
        if target.exists():
            shutil.rmtree(target)
        venv.EnvBuilder(with_pip=False, symlinks=True).create(target)
        site = next((target / "lib").glob("python*/site-packages"))
        put(site / "pydantic.py", "# Synthetic required dependency\n")
        put(site / "jsonschema.py", "# Synthetic optional dependency\n")
        shutil.copytree(Path(yaml.__file__).parent, site / "yaml")
        if alias == "python3":
            (target / "bin/python").unlink(missing_ok=True)
        elif alias == "python":
            (target / "bin/python3").unlink(missing_ok=True)

    def install_tools(self) -> None:
        for name in (
            "bash",
            "dirname",
            "basename",
            "sed",
            "tr",
            "head",
            "tail",
            "awk",
            "grep",
            "uname",
            "cat",
            "date",
        ):
            (self.bin / name).symlink_to(shutil.which(name))
        # Explicit denial, not reliance on a successful network call failing.
        for name in (
            "curl",
            "wget",
            "pip",
            "pip3",
            "npm",
            "uvx",
            "mkdir",
            "rm",
            "mv",
            "cp",
            "install",
            "chmod",
            "tar",
            "mktemp",
            "touch",
            "sleep",
            "gh",
            "aws",
            "infisical",
        ):
            put(
                self.bin / name,
                f"#!/bin/bash\necho 'FORBIDDEN {name}' >&2\nexit 97\n",
                executable=True,
            )
        put(
            self.bin / "python3",
            "#!/bin/bash\n"
            'if [ "${ALLOW_METADATA_PY:-}" = 1 ]; then\n'
            f'  exec {shlex.quote(REAL_PYTHON)} -B "$@"\n'
            "fi\necho 'FORBIDDEN system Python' >&2\nexit 97\n",
            executable=True,
        )
        put(
            self.bin / "git",
            "#!/bin/bash\n"
            'case " $* " in\n'
            "  *' rev-parse '*|*' diff '*|*' status '*|*' ls-files '*|"
            f"*' branch --show-current '*) exec {shlex.quote(str(REAL_GIT))} \"$@\";;\n"
            "  *' remote get-url '*) exit 1;;\n"
            '  *) echo "FORBIDDEN git $*" >&2; exit 97;;\nesac\n',
            executable=True,
        )
        put(self.bin / "gitleaks", "#!/bin/bash\necho 'gitleaks version 8.24.3'\n", executable=True)
        put(
            self.bin / "pre-commit", "#!/bin/bash\necho 'pre-commit 9.9-fixture'\n", executable=True
        )
        self.uv_stub()
        put(
            self.bin / "flock",
            "#!/bin/bash\n"
            "[ \"$*\" = '-n -s 9' ] || { echo 'FORBIDDEN filename/writer flock' >&2; exit 97; }\n"
            "echo 'READONLY_FLOCK_FD9' >&2\n"
            f'exec {shlex.quote(shutil.which("flock") or "/usr/bin/flock")} "$@"\n',
            executable=True,
        )

    def uv_stub(self) -> None:
        put(
            self.bin / "uv",
            "#!/bin/bash\n"
            "if [ \"$*\" = '--version' ]; then echo 'uv 9.9-fixture'; exit 0; fi\n"
            'echo "FORBIDDEN uv $*" >&2\nexit 97\n',
            executable=True,
        )

    def auth_stub(self, owner: Path, *, fail_on_call: bool) -> None:
        put(
            owner / "ops/secrets/session_start_secrets.py",
            "import json, os, sys\nfrom pathlib import Path\n"
            "assert os.environ['L9_GOVERNANCE_SURFACE'] == 'manus'\n"
            + (
                "raise RuntimeError('FORBIDDEN auth/login/bind')\n"
                if fail_on_call
                else "print('FIXTURE_AUTH_NOT_LIVE')\n"
                "dest = Path(sys.argv[sys.argv.index('--receipt-out')+1])\n"
                "dest.write_text(json.dumps({'ok': True}))\n"
            ),
        )

    def cache_fingerprint(self, *, machine: str | None = None) -> None:
        # Reproduce the fingerprint definition in Python, without invoking an
        # apply path or writing any installer/lock marker to compute it.
        interpreter = self.gov / ".venv/bin/python3"
        if not interpreter.exists():
            interpreter = self.gov / ".venv/bin/python"
        info = json.loads(
            subprocess.run(
                [
                    str(interpreter),
                    "-B",
                    "-I",
                    "-c",
                    "import platform,json; print(json.dumps([platform.python_version(),"
                    "platform.python_implementation(),platform.system(),platform.machine()]))",
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        )
        host = info[-1]
        if machine is not None:
            info[-1] = machine
        h = hashlib.sha256()
        for name in ("pyproject.toml", "uv.lock"):
            h.update(name.encode() + b"\0" + (self.gov / name).read_bytes() + b"\0")
        for value in (*info, host, "uv 9.9-fixture"):
            h.update(value.encode() + b"\0")
        put(self.gov / ".venv/.l9-uv-fingerprint", h.hexdigest() + "\n")

    def run(
        self, script: str = BOOTSTRAP, *, check: bool = True, owner: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        args = ["/bin/bash", str((owner or self.source) / script)]
        if script == ENSURE:
            args.extend([str(self.gov), "check" if check else "apply"])
        else:
            if script == BOOTSTRAP:
                args.extend(["--surface", "manus"])
            args.extend(["--governance", str(self.gov), "--workspace", str(self.ws)])
            if check:
                args.append("--check")
        return subprocess.run(
            args, cwd=self.ws, env=self.env, capture_output=True, text=True, timeout=45
        )

    def unchanged_check(
        self, script: str = BOOTSTRAP, *, code: int = 6
    ) -> subprocess.CompletedProcess[str]:
        before = snapshot(self.root)
        result = self.run(script)
        assert snapshot(self.root) == before, result.stderr
        assert result.returncode == code, result.stderr
        assert result.stdout == "", result.stdout
        assert "Agent environment ready" not in result.stderr
        assert "FORBIDDEN" not in result.stderr, result.stderr
        return result

    def stub_apply(self, *, ensure_exit: int = 0) -> None:
        put(self.gov / ENSURE, f"#!/bin/bash\necho 'FIXTURE_ENSURE_APPLY'\nexit {ensure_exit}\n")
        self.auth_stub(self.gov, fail_on_call=False)
        put(
            self.gov / "ops/autonomy/local_execution_gate.py",
            "import json, os, sys\nfrom pathlib import Path\n"
            "event = json.load(sys.stdin)\n"
            "if os.environ.get('FIXTURE_EVENT'):\n"
            "    Path(os.environ['FIXTURE_EVENT']).write_text(json.dumps(event))\n"
            "print('FULL_GATE_APPLY', file=sys.stderr)\n"
            "if event['tool_input']['command'] == 'make push':\n"
            "    print(json.dumps({'permissionDecision':'deny',"
            "'permissionDecisionReason':'Publish path: fixture deny'}))\n",
        )
        put(self.gov / "ops/autonomy/l4_local.py", "print('FIXTURE_L4_STATUS')\n")
        put(self.gov / "ops/scripts/scratch_hold.py", "print('FIXTURE_SCRATCH_RESTORE')\n")
        put(
            self.source / "ops/scripts/lib/session_git_excludes.sh",
            "apply_session_git_excludes() { echo 'FIXTURE_EXCLUDES' >&2; }\n"
            "session_exclude_file() { printf '%s/.git/info/exclude' \"$1\"; }\n",
        )
        for name in ("mkdir", "rm"):
            put(
                self.bin / name,
                f'#!/bin/bash\ncase " $* " in *" {self.ws}/.l9/session"*) '
                f'exec /bin/{name} "$@";; esac\n'
                f"echo 'FORBIDDEN unbounded {name}' >&2\nexit 97\n",
                executable=True,
            )


@pytest.fixture
def tree(tmp_path: Path) -> BootstrapTree:
    return BootstrapTree(tmp_path)


@pytest.mark.parametrize("local_autonomy", ["0", "1"])
def test_full_check_preserves_every_byte_directory_mode_and_mtime(
    tree: BootstrapTree, local_autonomy: str
) -> None:
    tree.env["L9_L4_LOCAL_AUTONOMY"] = local_autonomy
    result = tree.unchanged_check()
    assert "path-rule-only diagnostic; NOT host enforcement" in result.stderr
    assert "publish_path_gate=ENFORCED" in result.stderr
    assert "observed auth UNKNOWN" in result.stderr
    assert "gates importable" in result.stderr
    assert '"remote_allowed": true' in result.stderr  # real read-only L4 breakglass status
    assert "machine identity configuration absent/incomplete" in result.stderr


def test_cached_ready_auth_never_proves_live_auth_even_with_configured_shape(
    tree: BootstrapTree,
) -> None:
    tree.env.update(
        L9_INFISICAL_CLIENT_ID="fixture-id", L9_INFISICAL_CLIENT_SECRET="fixture-secret-never-log"
    )
    result = tree.unchanged_check()
    assert "machine identity configuration present (shape only)" in result.stderr
    assert "observed auth UNKNOWN" in result.stderr
    assert "fixture-secret-never-log" not in result.stderr + result.stdout


def test_complete_manus_installer_check_chain_is_read_only_and_degraded(
    tree: BootstrapTree,
) -> None:
    result = tree.unchanged_check(INSTALLER)
    assert f"VALIDATOR {tree.gov}/.venv/bin/python3" in result.stderr
    assert "manus-install: DEGRADED" in result.stderr
    assert "observed auth UNKNOWN" in result.stderr


@pytest.mark.parametrize("verdict", ["crash", "allow", "deny-both"])
def test_check_path_rule_probes_have_honest_error_and_disabled_states(
    tree: BootstrapTree, verdict: str
) -> None:
    body = {
        "crash": "raise RuntimeError('fixture probe failure')",
        "allow": "return None",
        "deny-both": "return 'Publish path: fixture deny everything'",
    }[verdict]
    put(
        tree.gov / "ops/autonomy/local_execution_gate.py",
        f"def publish_path_workflow_deny(command):\n    {body}\n",
    )
    result = tree.unchanged_check()
    expected = "PROBE_ERROR" if verdict == "crash" else "NOT_ENFORCED"
    assert f"publish_path_gate={expected}" in result.stderr
    assert "2 degraded component(s)" in result.stderr


def test_missing_uv_with_valid_locked_python_is_degraded_without_pip(tree: BootstrapTree) -> None:
    (tree.bin / "uv").unlink()
    result = tree.unchanged_check()
    assert "uv unavailable" in result.stderr
    assert "pip install" not in result.stderr


@pytest.mark.parametrize("uv_present", [False, True])
def test_missing_locked_python_blocks_before_consumers(
    tree: BootstrapTree, uv_present: bool
) -> None:
    shutil.rmtree(tree.gov / ".venv")
    tree.env["ALLOW_METADATA_PY"] = "1"
    if not uv_present:
        (tree.bin / "uv").unlink()
    result = tree.unchanged_check(code=1)
    assert "locked interpreter ABSENT" in result.stderr
    assert "Publish-path" not in result.stderr
    assert "SessionStart secrets" not in result.stderr
    assert "Repository-scoped identity" not in result.stderr


@pytest.mark.parametrize(
    "failure", ["wrong-prefix", "wrong-version", "missing-pin", "pydantic", "yaml"]
)
def test_locked_python_preflight_failure_precedes_all_consumers(
    tree: BootstrapTree, failure: str
) -> None:
    (tree.bin / "uv").unlink()  # no sync probe can mask or repair the preflight
    if failure == "wrong-prefix":
        (tree.gov / ".venv/bin/python3").unlink()
        put(
            tree.gov / ".venv/bin/python3",
            f'#!/bin/bash\nexec {shlex.quote(REAL_PYTHON)} "$@"\n',
            executable=True,
        )
    elif failure == "wrong-version":
        put(tree.gov / ".python-version", "9.99\n")
    elif failure == "missing-pin":
        (tree.gov / ".python-version").unlink()
    else:
        site = next((tree.gov / ".venv/lib").glob("python*/site-packages"))
        if failure == "yaml":
            shutil.rmtree(site / "yaml")
        else:
            (site / "pydantic.py").unlink()
        # An ambient PYTHONPATH must not lend a dependency to this interpreter.
        ambient = tree.root / "ambient"
        put(ambient / f"{failure}.py", "# Ambient dependency must not be borrowed\n")
        tree.env["PYTHONPATH"] = str(ambient)
    result = tree.unchanged_check(code=1)
    assert "fail-closed before consumers" in result.stderr
    for consumer in (
        "Canonical checker",
        "Publish-path",
        "SessionStart secrets",
        "Repository-scoped identity",
        "Readiness preflight",
    ):
        assert consumer not in result.stderr


def test_missing_jsonschema_is_optional_degraded(tree: BootstrapTree) -> None:
    site = next((tree.gov / ".venv/lib").glob("python*/site-packages"))
    (site / "jsonschema.py").unlink()
    result = tree.unchanged_check()
    assert "jsonschema import FAILING" in result.stderr
    assert "Repository-scoped identity" in result.stderr


def test_failed_ensure_check_is_counted_not_ready(tree: BootstrapTree) -> None:
    put(tree.gov / "uv.lock", "version = 2\n")
    result = tree.unchanged_check()
    assert "locked environment out of sync" in result.stderr
    assert "2 degraded component(s)" in result.stderr  # lock drift + auth UNKNOWN


@pytest.mark.parametrize("alias", ["python3", "python"])
def test_each_locked_interpreter_alias_works_in_full_check(tree: BootstrapTree, alias: str) -> None:
    tree.make_venv(alias)
    tree.cache_fingerprint()
    result = tree.unchanged_check()
    assert f"locked interpreter: {tree.gov}/.venv/bin/{alias} " in result.stderr


def test_uv_bad_arch_does_not_delete_matching_cached_fingerprint(tree: BootstrapTree) -> None:
    machine = "fixture-foreign-architecture"
    interpreter = tree.gov / ".venv/bin/python3"
    interpreter.unlink()
    put(
        interpreter,
        "#!/bin/bash\n"
        '[ "${3:-}" != \'-\' ] || { echo "$FAKE_FINGERPRINT"; exit 0; }\n'
        "case \" $* \" in *'import platform; print(platform.machine())'*) "
        f"echo '{machine}'; exit 0;; esac\n"
        f'exec {shlex.quote(REAL_PYTHON)} "$@"\n',
        executable=True,
    )
    tree.cache_fingerprint(machine=machine)
    tree.env["FAKE_FINGERPRINT"] = (tree.gov / ".venv/.l9-uv-fingerprint").read_text().strip()
    result = tree.unchanged_check(ENSURE, code=1)
    assert "re-synchronizing" in result.stderr
    assert "cached locked environment" not in result.stderr
    assert (tree.gov / ".venv/.l9-uv-fingerprint").exists()


@pytest.mark.parametrize("held", [False, True])
def test_uv_marker_uses_existing_input_lock_fd_without_writes(
    tree: BootstrapTree, held: bool
) -> None:
    lock = tree.gov / ".l9/uv-environment.lock"
    put(lock, "existing lock bytes\n")
    put(tree.gov / ".l9/uv-environment.installing", "fixture install marker\n")
    fd = os.open(lock, os.O_RDONLY)
    try:
        if held:
            fcntl.flock(fd, fcntl.LOCK_EX)
        # No shell filename-form flock is accepted by the guarded stub.
        result = tree.unchanged_check(ENSURE, code=1)
        assert (
            "install in progress" if held else "previous install did not complete"
        ) in result.stderr
    finally:
        os.close(fd)


def test_uv_marker_without_lock_does_not_create_lock(tree: BootstrapTree) -> None:
    put(tree.gov / ".l9/uv-environment.installing", "fixture abandoned marker\n")
    tree.unchanged_check(ENSURE, code=1)
    assert not (tree.gov / ".l9/uv-environment.lock").exists()


def test_known_mixed_bootstrap_revision_blocks_before_apply_mutations(tree: BootstrapTree) -> None:
    put(tree.gov / "different.txt", "different governance revision\n")
    git(tree.gov, "add", "different.txt")
    git(tree.gov, "commit", "-qm", "Synthetic independent revision")
    before = snapshot(tree.root)
    result = tree.run(check=False)
    assert result.returncode == 1, result.stderr
    assert "REVISION_MISMATCH" in result.stderr
    assert "Locked governance toolchain" not in result.stderr
    assert snapshot(tree.root) == before
    assert result.stdout == ""
    assert "FORBIDDEN" not in result.stderr


def test_unknown_bootstrap_source_is_degraded_in_check(tree: BootstrapTree) -> None:
    shutil.rmtree(tree.source / ".git")
    result = tree.unchanged_check()
    assert "revision UNKNOWN" in result.stderr
    assert "2 degraded component(s)" in result.stderr


@pytest.mark.parametrize("source_kind", ["nested-copy", "untracked", "renamed"])
def test_bootstrap_requires_exact_root_and_tracked_executing_script(
    tree: BootstrapTree, source_kind: str
) -> None:
    owner = tree.source
    script = BOOTSTRAP
    if source_kind == "nested-copy":
        # The enclosing repository has the SAME HEAD as governance. The old
        # unrestricted rev-parse accepted that HEAD for this unversioned copy.
        owner = tree.gov / "nested-copy"
        shutil.copytree(tree.source, owner, ignore=shutil.ignore_patterns(".git"), symlinks=True)
        assert git(owner, "rev-parse", "HEAD") == git(tree.gov, "rev-parse", "HEAD")
        assert Path(git(owner, "rev-parse", "--show-toplevel")) == tree.gov
    elif source_kind == "untracked":
        git(owner, "rm", "--cached", BOOTSTRAP)
    else:
        script = "ops/scripts/copied_bootstrap.sh"
        shutil.copy2(owner / BOOTSTRAP, owner / script)
    before = snapshot(tree.root)
    result = tree.run(script, owner=owner)
    assert snapshot(tree.root) == before, result.stderr
    assert result.returncode == 6, result.stderr
    assert result.stdout == ""
    assert "revision UNKNOWN" in result.stderr
    assert "2 degraded component(s)" in result.stderr
    assert "Agent environment ready" not in result.stderr
    assert "FORBIDDEN" not in result.stderr


def test_nested_governance_cannot_borrow_enclosing_git_head(tree: BootstrapTree) -> None:
    nested = tree.gov / "nested-governance"
    shutil.copytree(tree.gov, nested, ignore=shutil.ignore_patterns(".git"), symlinks=True)
    tree.gov = nested
    tree.cache_fingerprint()
    assert git(nested, "rev-parse", "HEAD") == git(tree.source, "rev-parse", "HEAD")
    result = tree.unchanged_check()
    assert "revision UNKNOWN" in result.stderr
    assert "2 degraded component(s)" in result.stderr


@pytest.mark.parametrize("ensure_exit", [0, 1])
def test_stubbed_apply_propagates_surface_and_source_provenance(
    tree: BootstrapTree, ensure_exit: int
) -> None:
    tree.stub_apply(ensure_exit=ensure_exit)
    tree.env["FIXTURE_EVENT"] = str(tree.root / "apply-gate-event.json")
    result = tree.run(check=False)
    assert result.returncode == (6 if ensure_exit else 0), result.stderr
    assert result.stdout == "", result.stdout
    assert "FORBIDDEN" not in result.stderr
    event = json.loads((tree.root / "apply-gate-event.json").read_text())
    assert event["cwd"] == str(tree.ws)
    assert event["tool_name"] == "Bash"
    assert event["tool_input"]["command"] == "make pr"
    receipts = list((tree.home / ".l9/agents/readiness/runtime/manus").glob("*.json"))
    receipt = json.loads(next(p for p in receipts if p.name != "cached.json").read_text())
    assert receipt["surface"] == "manus"
    assert receipt["governance_revision"] == git(tree.gov, "rev-parse", "HEAD")
    assert receipt["runtime_script_revision"] == git(tree.source, "rev-parse", "HEAD")
    assert receipt["bound_workspace_sha"] == "UNKNOWN"  # unrelated consumer HEAD isn't authority
    assert receipt["overall_status"] == ("DEGRADED" if ensure_exit else "READY")
    if ensure_exit:
        assert "1 degraded component(s)" in result.stderr
        assert "Agent environment ready" not in result.stderr
    else:
        assert "Agent environment ready" in result.stderr  # fixture only, not live auth


@pytest.mark.parametrize("canonical_present", [False, True])
def test_apply_never_invokes_older_workspace_secrets_owner(
    tree: BootstrapTree, canonical_present: bool
) -> None:
    tree.stub_apply()
    evil_marker = tree.ws / "evil-auth-invoked"
    put(
        tree.ws / "ops/secrets/session_start_secrets.py",
        "from pathlib import Path\n"
        f"Path({str(evil_marker)!r}).write_text('workspace owner invoked')\n"
        "raise RuntimeError('FORBIDDEN older workspace auth')\n",
    )
    git(tree.ws, "add", "ops/secrets/session_start_secrets.py")
    git(tree.ws, "commit", "-qm", "Synthetic older workspace owner")
    # The workspace owner is a real tracked old checkout, never an apply override.
    assert git(tree.ws, "rev-parse", "HEAD") != git(tree.gov, "rev-parse", "HEAD")
    assert git(tree.source, "rev-parse", "HEAD") == git(tree.gov, "rev-parse", "HEAD")
    if not canonical_present:
        (tree.gov / "ops/secrets/session_start_secrets.py").unlink()
    before_ws = snapshot(tree.ws)
    result = tree.run(check=False)
    assert result.returncode == (0 if canonical_present else 6), result.stderr
    assert result.stdout == ""
    assert not evil_marker.exists()
    assert "FORBIDDEN" not in result.stderr
    if canonical_present:
        assert "FIXTURE_AUTH_NOT_LIVE" in result.stderr
        receipt = json.loads((tree.ws / ".l9/session/secrets-plane.json").read_text())
        assert receipt == {"ok": True}
    else:
        assert "missing ops/secrets/session_start_secrets.py" in result.stderr
        assert "FIXTURE_AUTH_NOT_LIVE" not in result.stderr
    # Only the canonical secrets receipt can differ in this synthetic apply.
    after_ws = snapshot(tree.ws)
    for name, state in before_ws.items():
        if name not in {".", ".l9/session", ".l9/session/secrets-plane.json"}:
            assert after_ws[name] == state, name


def test_nested_copied_bootstrap_cannot_claim_ready_from_same_outer_head(
    tree: BootstrapTree,
) -> None:
    nested = tree.gov / "nested-source"
    shutil.copytree(tree.source, nested, ignore=shutil.ignore_patterns(".git"), symlinks=True)
    tree.source = nested
    tree.stub_apply()
    assert git(nested, "rev-parse", "HEAD") == git(tree.gov, "rev-parse", "HEAD")
    before_source = snapshot(nested)
    before_gov = snapshot(tree.gov)
    result = tree.run(check=False)
    assert result.returncode == 6, result.stderr
    assert result.stdout == ""
    assert "FORBIDDEN" not in result.stderr
    assert "Agent environment ready" not in result.stderr
    assert "FIXTURE_AUTH_NOT_LIVE" in result.stderr
    receipts = (tree.home / ".l9/agents/readiness/runtime/manus").glob("*.json")
    receipt = json.loads(next(p for p in receipts if p.name != "cached.json").read_text())
    assert receipt["runtime_script_revision"] == "UNKNOWN"
    assert receipt["governance_revision"] == git(tree.gov, "rev-parse", "HEAD")
    assert receipt["overall_status"] == "DEGRADED"
    assert snapshot(nested) == before_source
    assert snapshot(tree.gov) == before_gov


def test_unknown_source_override_cannot_be_borrowed_from_apply_writer_owner(
    tree: BootstrapTree,
) -> None:
    tree.stub_apply()
    shutil.rmtree(tree.source / ".git")
    result = tree.run(check=False)
    assert result.returncode == 6, result.stderr
    assert "Agent environment ready" not in result.stderr
    receipts = (tree.home / ".l9/agents/readiness/runtime/manus").glob("*.json")
    receipt = json.loads(next(p for p in receipts if p.name != "cached.json").read_text())
    assert receipt["runtime_script_revision"] == "UNKNOWN"
    assert receipt["governance_revision"] != "UNKNOWN"
    assert receipt["overall_status"] == "DEGRADED"


@pytest.mark.parametrize("source_known", [False, True])
def test_full_writer_uses_independent_clone_or_unknown_source(
    tree: BootstrapTree, source_known: bool
) -> None:
    put(tree.gov / "different.txt", "new governance revision\n")
    git(tree.gov, "add", "different.txt")
    git(tree.gov, "commit", "-qm", "Synthetic second-clone revision")
    source_sha = git(tree.source, "rev-parse", "HEAD")
    if not source_known:
        shutil.rmtree(tree.source / ".git")
    before_source = snapshot(tree.source)
    before_gov = snapshot(tree.gov)
    result = subprocess.run(
        [
            REAL_PYTHON,
            "-B",
            str(tree.source / WRITER),
            "--surface",
            "manus",
            "--governance",
            str(tree.gov),
            "--workspace",
            str(tree.ws),
        ],
        env=tree.env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    receipt = json.loads(Path(data["path"]).read_text())
    assert receipt["governance_revision"] == git(tree.gov, "rev-parse", "HEAD")
    assert receipt["runtime_script_revision"] == (source_sha if source_known else "UNKNOWN")
    assert receipt["overall_status"] == ("NOT_READY" if source_known else "DEGRADED")
    assert receipt["failure_code"] == ("REVISION_MISMATCH" if source_known else "")
    assert snapshot(tree.source) == before_source
    assert snapshot(tree.gov) == before_gov


@pytest.mark.parametrize("source_kind", ["nested-copy", "untracked", "renamed"])
@pytest.mark.parametrize("override", ["", "explicit", "unknown", "omit"])
def test_writer_copied_script_provenance_and_explicit_overrides(
    tree: BootstrapTree, source_kind: str, override: str
) -> None:
    owner = tree.source
    script = WRITER
    if source_kind == "nested-copy":
        owner = tree.gov / "nested-writer"
        shutil.copytree(tree.source, owner, ignore=shutil.ignore_patterns(".git"), symlinks=True)
        assert Path(git(owner, "rev-parse", "--show-toplevel")) == tree.gov
    elif source_kind == "untracked":
        git(owner, "rm", "--cached", WRITER)
    else:
        script = "ops/scripts/copied_writer.py"
        shutil.copy2(owner / WRITER, owner / script)
    gov_sha = git(tree.gov, "rev-parse", "HEAD")
    assert git(owner, "rev-parse", "HEAD") == gov_sha
    extra = {
        "": [],
        "explicit": ["--runtime-script-revision", gov_sha],
        "unknown": ["--runtime-script-revision", "UNKNOWN"],
        "omit": ["--runtime-script-revision", gov_sha, "--omit-runtime-script-revision"],
    }[override]
    before_source = snapshot(owner)
    before_gov = snapshot(tree.gov)
    result = subprocess.run(
        [
            REAL_PYTHON,
            "-B",
            str(owner / script),
            "--surface",
            "manus",
            "--governance",
            str(tree.gov),
            "--workspace",
            str(tree.ws),
            *extra,
        ],
        env={**tree.env, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(Path(json.loads(result.stdout)["path"]).read_text())
    assert receipt["governance_revision"] == gov_sha
    assert receipt["runtime_script_revision"] == (gov_sha if override == "explicit" else "UNKNOWN")
    assert receipt["overall_status"] == ("READY" if override == "explicit" else "DEGRADED")
    assert receipt["failure_code"] == ""
    assert snapshot(owner) == before_source
    assert snapshot(tree.gov) == before_gov


def test_writer_nested_governance_requires_exact_root(tree: BootstrapTree) -> None:
    nested = tree.gov / "nested-governance"
    put(nested / "CANONICAL_LAW.md", "Synthetic copied governance\n")
    before_source = snapshot(tree.source)
    before_gov = snapshot(tree.gov)
    result = subprocess.run(
        [
            REAL_PYTHON,
            "-B",
            str(tree.source / WRITER),
            "--surface",
            "manus",
            "--governance",
            str(nested),
            "--workspace",
            str(tree.ws),
        ],
        env={**tree.env, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads(Path(json.loads(result.stdout)["path"]).read_text())
    assert receipt["governance_revision"] == "UNKNOWN"
    assert receipt["runtime_script_revision"] == git(tree.source, "rev-parse", "HEAD")
    assert receipt["overall_status"] == "DEGRADED"
    assert snapshot(tree.source) == before_source
    assert snapshot(tree.gov) == before_gov


@pytest.mark.parametrize("bootstrap_exit", [1, 2, 75])
def test_installer_preserves_blocked_code_and_never_runs_validator(
    tree: BootstrapTree, bootstrap_exit: int
) -> None:
    put(tree.gov / BOOTSTRAP, f"#!/bin/bash\nexit {bootstrap_exit}\n")
    (tree.gov / "environment/agents/adapters/manus/validate_manus_adapter.py").unlink()
    before = snapshot(tree.root)
    result = tree.run(INSTALLER)
    assert result.returncode == bootstrap_exit, result.stderr
    assert "VALIDATOR" not in result.stdout + result.stderr
    assert snapshot(tree.root) == before
    assert result.stdout == ""


@pytest.mark.parametrize("alias", ["python3", "python"])
@pytest.mark.parametrize("bootstrap_exit", [0, 6])
def test_installer_selects_alias_created_by_bootstrap_not_eager_system_python(
    tree: BootstrapTree, alias: str, bootstrap_exit: int
) -> None:
    # Prepare a genuine fixture interpreter, then let the stub bootstrap reveal
    # its alias. This mutates only the synthetic tree, with no uv/package action.
    tree.make_venv(alias)
    interpreter = tree.gov / ".venv/bin" / alias
    hidden = interpreter.with_name(alias + ".hidden")
    interpreter.rename(hidden)
    put(
        tree.gov / BOOTSTRAP,
        f"#!/bin/bash\n/bin/mv {shlex.quote(str(hidden))} {shlex.quote(str(interpreter))}\n"
        f"exit {bootstrap_exit}\n",
    )
    result = tree.run(INSTALLER, check=False)
    assert result.returncode == bootstrap_exit, result.stderr
    assert f"VALIDATOR {interpreter}" in result.stderr
    assert result.stdout == ""
    assert "FORBIDDEN" not in result.stderr


@pytest.mark.parametrize("failure", ["absent", "wrong-prefix", "yaml", "validator"])
def test_installer_fail_closed_after_usable_bootstrap(tree: BootstrapTree, failure: str) -> None:
    put(tree.gov / BOOTSTRAP, "#!/bin/bash\nexit 6\n")
    if failure == "absent":
        shutil.rmtree(tree.gov / ".venv")
    elif failure == "wrong-prefix":
        interpreter = tree.gov / ".venv/bin/python3"
        interpreter.unlink()
        put(interpreter, f'#!/bin/bash\nexec {shlex.quote(REAL_PYTHON)} "$@"\n', executable=True)
    elif failure == "yaml":
        site = next((tree.gov / ".venv/lib").glob("python*/site-packages"))
        shutil.rmtree(site / "yaml")
    else:
        tree.env["VALIDATOR_EXIT"] = "1"
    before = snapshot(tree.root)
    result = tree.run(INSTALLER)
    assert result.returncode == 1, result.stderr
    assert result.stdout == ""
    assert "READY (shared bootstrap)" not in result.stderr
    assert snapshot(tree.root) == before
    if failure != "validator":
        assert "VALIDATOR" not in result.stderr
